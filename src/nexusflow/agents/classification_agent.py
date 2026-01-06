"""
Classification Agent using LangGraph v1

A multi-step classification agent that:
1. Queries Neo4j graph for category hierarchy
2. Searches Milvus for similar historical tickets
3. Uses LLM as a judge for final classification
4. Calculates ensemble confidence
5. Routes to HITL if confidence is low
"""

import json
import time
from datetime import datetime
from typing import Annotated, Any, TypedDict

import structlog
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from nexusflow.agents.confidence import (
    ComponentPrediction,
    ConfidenceCalculator,
)
from nexusflow.config import settings
from nexusflow.db.milvus_client import MilvusClient, get_milvus_client
from nexusflow.db.neo4j_client import Neo4jClient, get_neo4j_client
from nexusflow.services.embeddings import EmbeddingService, get_embedding_service

logger = structlog.get_logger(__name__)


class ClassificationState(TypedDict):
    """State for the classification agent graph."""

    # Input
    ticket_id: str
    title: str
    description: str
    priority: str
    metadata: dict[str, Any]

    # Processing state
    messages: Annotated[list[BaseMessage], add_messages]
    current_step: str
    start_time: float

    # Graph results
    graph_paths: list[dict[str, Any]]
    graph_prediction: dict[str, Any] | None
    graph_confidence: float

    # Vector results
    vector_matches: list[dict[str, Any]]
    vector_prediction: dict[str, Any] | None
    vector_confidence: float

    # LLM results
    llm_prediction: dict[str, Any] | None
    llm_confidence: float
    llm_reasoning: str

    # Final results
    ensemble_result: dict[str, Any] | None
    final_classification: dict[str, Any] | None
    requires_hitl: bool
    hitl_reason: str | None

    # Errors
    errors: list[str]


def get_llm_client():
    """Get the appropriate LLM client based on available credentials."""
    # Try Azure OpenAI first
    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            deployment_name=settings.azure_openai_deployment_name,
            temperature=0.1,
        )

    # Try direct OpenAI
    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.nexusflow_default_model,
            temperature=0.1,
        )

    # Try Anthropic
    if settings.anthropic_api_key:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model="claude-3-5-sonnet-20241022",
            temperature=0.1,
        )

    raise ValueError(
        "No LLM API key configured. Set AZURE_OPENAI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY"
    )


class ClassificationAgent:
    """
    LangGraph-based classification agent.

    The agent flow:
    1. extract_keywords - Extract relevant keywords from ticket
    2. query_graph - Query Neo4j for matching category paths
    3. search_vectors - Search Milvus for similar tickets
    4. llm_judge - Use LLM to make final classification decision
    5. calculate_confidence - Ensemble confidence calculation
    6. route_decision - Route to auto-resolve or HITL
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient = None,
        milvus_client: MilvusClient = None,
        embedding_service: EmbeddingService = None,
    ):
        self.neo4j_client = neo4j_client
        self.milvus_client = milvus_client
        self.embedding_service = embedding_service
        self.confidence_calculator = ConfidenceCalculator()

        # Initialize LLM
        self.llm = get_llm_client()

        # Build the graph
        self.graph = self._build_graph()

    async def _ensure_clients(self):
        """Ensure all clients are initialized."""
        if self.neo4j_client is None:
            self.neo4j_client = await get_neo4j_client()
        if self.milvus_client is None:
            self.milvus_client = get_milvus_client()
        if self.embedding_service is None:
            self.embedding_service = get_embedding_service()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create the graph
        workflow = StateGraph(ClassificationState)

        # Add nodes
        workflow.add_node("extract_keywords", self.extract_keywords)
        workflow.add_node("query_graph", self.query_graph)
        workflow.add_node("search_vectors", self.search_vectors)
        workflow.add_node("llm_judge", self.llm_judge)
        workflow.add_node("calculate_confidence", self.calculate_confidence)
        workflow.add_node("route_decision", self.route_decision)

        # Set entry point
        workflow.set_entry_point("extract_keywords")

        # Add edges
        workflow.add_edge("extract_keywords", "query_graph")
        workflow.add_edge("query_graph", "search_vectors")
        workflow.add_edge("search_vectors", "llm_judge")
        workflow.add_edge("llm_judge", "calculate_confidence")
        workflow.add_edge("calculate_confidence", "route_decision")
        workflow.add_edge("route_decision", END)

        return workflow.compile()

    async def classify(
        self,
        ticket_id: str,
        title: str,
        description: str,
        priority: str = "medium",
        metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """
        Classify a ticket through the full pipeline.

        Returns:
            Classification result with confidence and routing decision
        """
        await self._ensure_clients()

        # Initialize state
        initial_state: ClassificationState = {
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "priority": priority,
            "metadata": metadata or {},
            "messages": [],
            "current_step": "start",
            "start_time": time.time(),
            "graph_paths": [],
            "graph_prediction": None,
            "graph_confidence": 0.0,
            "vector_matches": [],
            "vector_prediction": None,
            "vector_confidence": 0.0,
            "llm_prediction": None,
            "llm_confidence": 0.0,
            "llm_reasoning": "",
            "ensemble_result": None,
            "final_classification": None,
            "requires_hitl": False,
            "hitl_reason": None,
            "errors": [],
        }

        # Run the graph
        try:
            final_state = await self.graph.ainvoke(initial_state)
            return self._format_result(final_state)
        except Exception as e:
            logger.error("Classification failed", ticket_id=ticket_id, error=str(e))
            raise

    async def get_llm_judgment(
        self,
        title: str,
        description: str,
        available_categories: list[str],
        similar_tickets: list[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Get LLM classification judgment for a ticket.

        This is a standalone method that can be used via MCP tools.

        Args:
            title: Ticket title
            description: Ticket description
            available_categories: List of valid category paths (L1 > L2 > L3)
            similar_tickets: Optional list of similar tickets for context

        Returns:
            LLM classification with reasoning and confidence
        """
        # Build category context
        categories_text = "\n".join(f"- {cat}" for cat in available_categories[:50])

        # Build similar tickets context
        similar_context = ""
        if similar_tickets:
            similar_context = "\n\nSimilar historical tickets:\n"
            for i, ticket in enumerate(similar_tickets[:5], 1):
                similar_context += f'{i}. [{ticket.get("category", "Unknown")}] "{ticket.get("title", "")}" (similarity: {ticket.get("similarity", 0):.2f})\n'

        system_prompt = """You are an expert support ticket classifier. Classify the ticket into the most appropriate category from the provided list.

Respond with a JSON object:
{
    "level1": "Level 1 category",
    "level2": "Level 2 category",
    "level3": "Level 3 category",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}"""

        user_prompt = f"""Classify this ticket:

Title: {title}
Description: {description}

Available categories:
{categories_text}
{similar_context}

Classification (JSON):"""

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )

            response_text = response.content.strip()

            # Extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text)

            return {
                "level1": result.get("level1", "Unknown"),
                "level2": result.get("level2", "Unknown"),
                "level3": result.get("level3", "Unknown"),
                "confidence": result.get("confidence", 0.7),
                "reasoning": result.get("reasoning", ""),
            }
        except Exception as e:
            logger.error("LLM judgment failed", error=str(e))
            return {
                "level1": "Unknown",
                "level2": "Unknown",
                "level3": "Unknown",
                "confidence": 0.0,
                "reasoning": f"Error: {str(e)}",
                "error": str(e),
            }

    # =========================================================================
    # Graph Nodes
    # =========================================================================

    async def extract_keywords(self, state: ClassificationState) -> ClassificationState:
        """Extract keywords from ticket for graph query."""
        state["current_step"] = "extract_keywords"

        prompt = f"""Extract 5-10 relevant keywords from this support ticket that would help classify it.
Return only the keywords as a JSON array of strings.

Ticket:
Title: {state["title"]}
Description: {state["description"]}

Keywords (JSON array):"""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            keywords_text = response.content.strip()

            # Parse JSON array
            if keywords_text.startswith("["):
                keywords = json.loads(keywords_text)
            else:
                # Fallback: split by commas
                keywords = [k.strip().strip("\"'") for k in keywords_text.split(",")]

            state["metadata"]["keywords"] = keywords
            logger.debug("Extracted keywords", keywords=keywords)
        except Exception as e:
            logger.warning("Keyword extraction failed", error=str(e))
            state["metadata"]["keywords"] = []
            state["errors"].append(f"Keyword extraction: {str(e)}")

        return state

    async def query_graph(self, state: ClassificationState) -> ClassificationState:
        """Query Neo4j graph for classification paths."""
        state["current_step"] = "query_graph"

        try:
            keywords = state["metadata"].get("keywords", [])

            # Get paths from graph
            paths = await self.neo4j_client.get_classification_path(
                ticket_text=f"{state['title']} {state['description']}",
                keywords=keywords,
            )

            state["graph_paths"] = paths

            if paths:
                top_path = paths[0]
                state["graph_prediction"] = {
                    "level1": top_path["level1"],
                    "level2": top_path["level2"],
                    "level3": top_path["level3"],
                }
                state["graph_confidence"] = top_path.get("confidence", 0.7)

                logger.debug(
                    "Graph query result",
                    top_path=top_path,
                    num_paths=len(paths),
                )
            else:
                state["graph_confidence"] = 0.0
                state["errors"].append("No graph paths found")

        except Exception as e:
            logger.error("Graph query failed", error=str(e))
            state["errors"].append(f"Graph query: {str(e)}")
            state["graph_confidence"] = 0.0

        return state

    async def search_vectors(self, state: ClassificationState) -> ClassificationState:
        """Search Milvus for similar tickets."""
        state["current_step"] = "search_vectors"

        try:
            # Generate embedding
            text = f"{state['title']} {state['description']}"
            embedding = await self.embedding_service.get_embedding(text)

            # Search for similar tickets
            matches = self.milvus_client.search(
                query_embedding=embedding,
                limit=10,
            )

            state["vector_matches"] = matches

            # Calculate classification from matches
            if matches:
                # Get most common classification from top matches
                classifications = {}
                for match in matches[:5]:
                    meta = match.get("metadata", {})
                    key = (
                        meta.get("level1", ""),
                        meta.get("level2", ""),
                        meta.get("level3", ""),
                    )
                    score = match.get("score", 0)
                    if key not in classifications:
                        classifications[key] = {"count": 0, "total_score": 0}
                    classifications[key]["count"] += 1
                    classifications[key]["total_score"] += score

                if classifications:
                    # Sort by count then by score
                    best = max(
                        classifications.items(), key=lambda x: (x[1]["count"], x[1]["total_score"])
                    )
                    state["vector_prediction"] = {
                        "level1": best[0][0],
                        "level2": best[0][1],
                        "level3": best[0][2],
                    }
                    # Confidence based on agreement and similarity
                    state["vector_confidence"] = min(
                        best[1]["total_score"]
                        / best[1]["count"]
                        * (best[1]["count"] / len(matches[:5])),
                        1.0,
                    )

                logger.debug(
                    "Vector search result",
                    top_prediction=state["vector_prediction"],
                    confidence=state["vector_confidence"],
                    num_matches=len(matches),
                )
            else:
                state["vector_confidence"] = 0.0

        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            state["errors"].append(f"Vector search: {str(e)}")
            state["vector_confidence"] = 0.0

        return state

    async def llm_judge(self, state: ClassificationState) -> ClassificationState:
        """Use LLM to make final classification judgment."""
        state["current_step"] = "llm_judge"

        # Prepare context from graph and vector results
        graph_context = ""
        if state["graph_paths"]:
            graph_context = "Graph-based suggestions:\n"
            for i, path in enumerate(state["graph_paths"][:3], 1):
                conf = path.get("confidence", 0.7)
                graph_context += f"{i}. {path['level1']} > {path['level2']} > {path['level3']} (confidence: {conf:.2f})\n"

        vector_context = ""
        if state["vector_matches"]:
            vector_context = "\nSimilar historical tickets:\n"
            for i, match in enumerate(state["vector_matches"][:3], 1):
                meta = match.get("metadata", {})
                title = meta.get("title", "Unknown")[:80]
                cat = f"{meta.get('level1', '')} > {meta.get('level2', '')} > {meta.get('level3', '')}"
                score = match.get("score", 0)
                vector_context += f'{i}. [{cat}] "{title}" (similarity: {score:.2f})\n'

        # Build prompt
        system_prompt = """You are an expert support ticket classifier. Your task is to classify tickets into a 3-level hierarchy.

Classification Hierarchy Levels:
- Level 1: Main category (e.g., "Technical Support", "Billing & Payments", "Account Management")
- Level 2: Subcategory (e.g., "Authentication", "Performance", "Invoicing")
- Level 3: Specific issue type (e.g., "Password Reset Issues", "Slow Response Time", "Missing Invoice")

You will be provided with suggestions from a graph database and similar historical tickets. Use these as guidance but make your own judgment.

Respond with a JSON object containing:
{
    "level1": "Category name",
    "level2": "Subcategory name",
    "level3": "Specific issue type",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of classification decision"
}"""

        user_prompt = f"""Classify this support ticket:

Title: {state["title"]}
Description: {state["description"]}
Priority: {state["priority"]}

{graph_context}
{vector_context}

Provide your classification as JSON:"""

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )

            # Parse response
            response_text = response.content.strip()

            # Extract JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text)

            state["llm_prediction"] = {
                "level1": result["level1"],
                "level2": result["level2"],
                "level3": result["level3"],
            }
            state["llm_confidence"] = result.get("confidence", 0.8)
            state["llm_reasoning"] = result.get("reasoning", "")

            logger.debug(
                "LLM judgment",
                prediction=state["llm_prediction"],
                confidence=state["llm_confidence"],
            )

        except Exception as e:
            logger.error("LLM judgment failed", error=str(e))
            state["errors"].append(f"LLM judgment: {str(e)}")

            # Fall back to graph or vector prediction
            if state["graph_prediction"]:
                state["llm_prediction"] = state["graph_prediction"]
                state["llm_confidence"] = state["graph_confidence"] * 0.8
            elif state["vector_prediction"]:
                state["llm_prediction"] = state["vector_prediction"]
                state["llm_confidence"] = state["vector_confidence"] * 0.8
            else:
                state["llm_confidence"] = 0.0

        return state

    async def calculate_confidence(self, state: ClassificationState) -> ClassificationState:
        """Calculate ensemble confidence from all components."""
        state["current_step"] = "calculate_confidence"

        # Create component predictions
        graph_pred = ComponentPrediction(
            level1=state["graph_prediction"]["level1"] if state["graph_prediction"] else "",
            level2=state["graph_prediction"]["level2"] if state["graph_prediction"] else "",
            level3=state["graph_prediction"]["level3"] if state["graph_prediction"] else "",
            confidence=state["graph_confidence"],
            source="graph",
        )

        vector_pred = ComponentPrediction(
            level1=state["vector_prediction"]["level1"] if state["vector_prediction"] else "",
            level2=state["vector_prediction"]["level2"] if state["vector_prediction"] else "",
            level3=state["vector_prediction"]["level3"] if state["vector_prediction"] else "",
            confidence=state["vector_confidence"],
            source="vector",
        )

        llm_pred = ComponentPrediction(
            level1=state["llm_prediction"]["level1"] if state["llm_prediction"] else "",
            level2=state["llm_prediction"]["level2"] if state["llm_prediction"] else "",
            level3=state["llm_prediction"]["level3"] if state["llm_prediction"] else "",
            confidence=state["llm_confidence"],
            source="llm",
        )

        # Calculate ensemble
        ensemble = self.confidence_calculator.calculate_ensemble_confidence(
            graph_pred, vector_pred, llm_pred
        )

        state["ensemble_result"] = {
            "level1": ensemble.level1,
            "level2": ensemble.level2,
            "level3": ensemble.level3,
            "graph_confidence": ensemble.graph_confidence,
            "vector_confidence": ensemble.vector_confidence,
            "llm_confidence": ensemble.llm_confidence,
            "raw_combined_score": ensemble.raw_combined_score,
            "calibrated_score": ensemble.calibrated_score,
            "component_agreement": ensemble.component_agreement,
            "entropy": ensemble.entropy,
            "is_high_confidence": ensemble.is_high_confidence,
            "needs_review": ensemble.needs_review,
        }

        state["final_classification"] = {
            "level1": ensemble.level1,
            "level2": ensemble.level2,
            "level3": ensemble.level3,
            "confidence": ensemble.calibrated_score,
        }

        logger.info(
            "Calculated ensemble confidence",
            ticket_id=state["ticket_id"],
            classification=f"{ensemble.level1} > {ensemble.level2} > {ensemble.level3}",
            confidence=ensemble.calibrated_score,
            agreement=ensemble.component_agreement,
        )

        return state

    async def route_decision(self, state: ClassificationState) -> ClassificationState:
        """Decide whether to auto-resolve or route to HITL."""
        state["current_step"] = "route_decision"

        ensemble = state["ensemble_result"]
        calibrated_score = ensemble["calibrated_score"]
        component_agreement = ensemble["component_agreement"]
        
        # Routing logic:
        # - Auto-resolve: confidence >= threshold (0.7) AND agreement >= 0.6
        # - HITL queue: confidence between hitl_threshold (0.5) and classification_threshold (0.7)
        # - Escalation: confidence < hitl_threshold (0.5) OR agreement < 0.4
        
        needs_hitl = False
        reasons = []
        
        # Check if auto-resolve conditions are NOT met
        if calibrated_score < settings.classification_confidence_threshold:
            needs_hitl = True
            if calibrated_score < settings.hitl_threshold:
                reasons.append(f"Very low confidence ({calibrated_score:.2f}) - escalation")
            else:
                reasons.append(f"Below auto-resolve threshold ({calibrated_score:.2f})")
        
        if component_agreement < 0.4:
            needs_hitl = True
            reasons.append(f"Low component agreement ({component_agreement:.2f})")
        
        if state["errors"]:
            needs_hitl = True
            reasons.append(f"Processing errors: {len(state['errors'])}")

        if needs_hitl:
            state["requires_hitl"] = True
            state["hitl_reason"] = "; ".join(reasons) if reasons else "Manual review required"
            logger.info(
                "Routing to HITL",
                ticket_id=state["ticket_id"],
                confidence=calibrated_score,
                reason=state["hitl_reason"],
            )
        else:
            state["requires_hitl"] = False
            state["hitl_reason"] = None
            logger.info(
                "Auto-resolved",
                ticket_id=state["ticket_id"],
                confidence=calibrated_score,
            )

        return state

    def _format_result(self, state: ClassificationState) -> dict[str, Any]:
        """Format the final classification result."""
        processing_time = int((time.time() - state["start_time"]) * 1000)

        return {
            "ticket_id": state["ticket_id"],
            "classification": state["final_classification"],
            "confidence": state["ensemble_result"],
            "graph_analysis": {
                "paths": state["graph_paths"][:5],
                "prediction": state["graph_prediction"],
                "confidence": state["graph_confidence"],
            },
            "vector_analysis": {
                "matches": state["vector_matches"][:5],
                "prediction": state["vector_prediction"],
                "confidence": state["vector_confidence"],
            },
            "llm_analysis": {
                "prediction": state["llm_prediction"],
                "confidence": state["llm_confidence"],
                "reasoning": state["llm_reasoning"],
            },
            "routing": {
                "requires_hitl": state["requires_hitl"],
                "hitl_reason": state["hitl_reason"],
                "auto_resolved": not state["requires_hitl"],
            },
            "processing": {
                "time_ms": processing_time,
                "errors": state["errors"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        }


def create_classification_graph() -> StateGraph:
    """Create a new classification graph instance."""
    agent = ClassificationAgent()
    return agent.graph


# Singleton agent instance
_classification_agent: ClassificationAgent | None = None


async def get_classification_agent() -> ClassificationAgent:
    """Get or create the classification agent singleton."""
    global _classification_agent
    if _classification_agent is None:
        _classification_agent = ClassificationAgent()
    return _classification_agent
