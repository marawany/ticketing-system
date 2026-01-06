"""
NexusFlow MCP Server

FastMCP 2.0-based server for ticket classification tools and resources.
Exposes all tools needed by the classification agent.
"""

import json
from datetime import datetime
from typing import Any

import structlog
from fastmcp import FastMCP

from nexusflow.config import settings
from nexusflow.models.ticket import TicketCreate, TicketPriority

logger = structlog.get_logger(__name__)

# Create MCP server instance with FastMCP 2.0
mcp = FastMCP(
    name="nexusflow",
    instructions="""
    NexusFlow is an intelligent ticket classification and resolution system.

    Use these tools to:
    - Classify support tickets using AI
    - Query the graph database for category information
    - Search vector database for similar tickets
    - Manage HITL tasks
    - Get system statistics and reports

    The classification workflow:
    1. Query graph for category hierarchy
    2. Search vectors for similar tickets
    3. Combine insights with confidence scoring
    4. Route based on confidence threshold
    """,
)


# =============================================================================
# Graph Database Tools (Neo4j)
# =============================================================================


@mcp.tool()
async def query_graph_categories(
    ticket_text: str,
    max_results: int = 5,
) -> dict[str, Any]:
    """
    Query the Neo4j graph database to find matching categories.

    Traverses the 3-level classification hierarchy to find the best
    category path based on the ticket text content.

    Args:
        ticket_text: Combined title and description of the ticket
        max_results: Maximum number of category paths to return

    Returns:
        List of matching category paths with confidence scores
    """
    from nexusflow.db import get_neo4j_client

    try:
        neo4j = await get_neo4j_client()

        # Get candidate categories based on text similarity
        paths = await neo4j.find_matching_categories(ticket_text, limit=max_results)

        return {
            "matches": paths,
            "count": len(paths),
            "source": "graph_database",
        }
    except Exception as e:
        logger.error("Graph query failed", error=str(e))
        return {"matches": [], "count": 0, "error": str(e)}


@mcp.tool()
async def get_graph_statistics() -> dict[str, Any]:
    """
    Get statistics about the classification graph database.

    Returns counts of categories at each level and total tickets.

    Returns:
        Statistics including category counts and ticket totals
    """
    from nexusflow.db import get_neo4j_client

    try:
        neo4j = await get_neo4j_client()
        stats = await neo4j.get_graph_statistics()
        return stats
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_category_hierarchy() -> dict[str, Any]:
    """
    Get the complete 3-level classification category hierarchy.

    Returns all Level1 -> Level2 -> Level3 category paths
    with ticket counts and accuracy statistics.

    Returns:
        Nested hierarchy structure with statistics
    """
    from nexusflow.db import get_neo4j_client

    try:
        neo4j = await get_neo4j_client()
        paths = await neo4j.get_all_paths()

        # Organize into hierarchy
        hierarchy = {}
        for path in paths:
            l1, l2, l3 = path["level1"], path["level2"], path["level3"]

            if l1 not in hierarchy:
                hierarchy[l1] = {}
            if l2 not in hierarchy[l1]:
                hierarchy[l1][l2] = []

            hierarchy[l1][l2].append(
                {
                    "name": l3,
                    "ticket_count": path.get("ticket_count", 0),
                    "accuracy": path.get("accuracy", 1.0),
                }
            )

        return {
            "hierarchy": hierarchy,
            "total_paths": len(paths),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def update_graph_classification(
    ticket_id: str,
    level1: str,
    level2: str,
    level3: str,
    was_corrected: bool = False,
) -> dict[str, Any]:
    """
    Update the graph database with a classification result.

    Records the classification and updates category statistics.
    Used for learning from both auto-resolved and HITL-corrected tickets.

    Args:
        ticket_id: The ticket identifier
        level1: Level 1 category
        level2: Level 2 category
        level3: Level 3 category (most specific)
        was_corrected: Whether this was a human correction

    Returns:
        Confirmation of the update
    """
    from nexusflow.db import get_neo4j_client

    try:
        neo4j = await get_neo4j_client()
        await neo4j.record_classification(
            ticket_id=ticket_id,
            level1=level1,
            level2=level2,
            level3=level3,
            was_corrected=was_corrected,
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "classification": {"level1": level1, "level2": level2, "level3": level3},
            "was_corrected": was_corrected,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Vector Database Tools (Milvus)
# =============================================================================


@mcp.tool()
async def search_similar_tickets(
    title: str,
    description: str,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Search the vector database for similar historical tickets.

    Uses semantic similarity to find tickets with similar content
    and their resolved classifications.

    Args:
        title: Ticket title
        description: Ticket description
        limit: Maximum number of results

    Returns:
        List of similar tickets with classifications and similarity scores
    """
    from nexusflow.db import get_milvus_client
    from nexusflow.services.embeddings import EmbeddingService

    try:
        milvus = get_milvus_client()
        embedding_service = EmbeddingService()

        # Create embedding for search
        text = f"{title}\n{description}"
        embedding = await embedding_service.get_embedding(text)

        # Search
        results = milvus.search(embedding, limit=limit)

        return {
            "matches": results,
            "count": len(results),
            "source": "vector_database",
        }
    except Exception as e:
        logger.error("Vector search failed", error=str(e))
        return {"matches": [], "count": 0, "error": str(e)}


@mcp.tool()
async def get_vector_statistics() -> dict[str, Any]:
    """
    Get statistics about the vector database collection.

    Returns count of indexed tickets and collection info.

    Returns:
        Vector collection statistics
    """
    from nexusflow.db import get_milvus_client

    try:
        milvus = get_milvus_client()
        stats = milvus.get_collection_stats()
        return stats
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def index_ticket_vector(
    ticket_id: str,
    title: str,
    description: str,
    level1: str,
    level2: str,
    level3: str,
    metadata: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Index a classified ticket in the vector database.

    Creates an embedding and stores it for future similarity searches.

    Args:
        ticket_id: The ticket identifier
        title: Ticket title
        description: Ticket description
        level1: Level 1 category
        level2: Level 2 category
        level3: Level 3 category
        metadata: Additional metadata to store

    Returns:
        Confirmation of indexing
    """
    from nexusflow.db import get_milvus_client
    from nexusflow.services.embeddings import EmbeddingService

    try:
        milvus = get_milvus_client()
        embedding_service = EmbeddingService()

        # Create embedding
        text = f"{title}\n{description}"
        embedding = await embedding_service.get_embedding(text)

        # Prepare metadata
        full_metadata = {
            "title": title[:500],
            "level1": level1,
            "level2": level2,
            "level3": level3,
            "category": f"{level1} > {level2} > {level3}",
            **(metadata or {}),
        }

        # Index
        milvus.insert(
            ticket_id=ticket_id,
            embedding=embedding,
            metadata=full_metadata,
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "indexed": True,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Classification Tools
# =============================================================================


@mcp.tool()
async def classify_ticket(
    title: str,
    description: str,
    priority: str = "medium",
    source: str = "mcp",
    customer_id: str = None,
    metadata: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Perform full ticket classification using the classification agent.

    This combines graph queries, vector search, and LLM judgment to
    produce a final classification with confidence scores.

    Args:
        title: The ticket title/subject
        description: Detailed description of the issue
        priority: Priority level (low, medium, high, critical)
        source: Source system of the ticket
        customer_id: Optional customer identifier
        metadata: Additional metadata

    Returns:
        Complete classification result with confidence and routing
    """
    from nexusflow.services.classification import ClassificationService

    try:
        service = ClassificationService()

        try:
            priority_enum = TicketPriority(priority.lower())
        except ValueError:
            priority_enum = TicketPriority.MEDIUM

        ticket = TicketCreate(
            title=title,
            description=description,
            priority=priority_enum,
            source=source,
            customer_id=customer_id,
            metadata=metadata or {},
        )

        result = await service.classify_ticket(ticket)

        return {
            "ticket_id": result["ticket_id"],
            "classification": {
                "level1": result["classification"]["level1"],
                "level2": result["classification"]["level2"],
                "level3": result["classification"]["level3"],
            },
            "confidence": {
                "score": result["confidence"]["calibrated_score"],
                "graph_confidence": result["confidence"]["graph"],
                "vector_confidence": result["confidence"]["vector"],
                "llm_confidence": result["confidence"]["llm"],
                "component_agreement": result["confidence"]["component_agreement"],
            },
            "routing": {
                "auto_resolved": result["routing"]["auto_resolved"],
                "requires_hitl": result["routing"]["requires_hitl"],
                "reason": result["routing"]["hitl_reason"],
            },
            "processing_time_ms": result["processing"]["time_ms"],
        }
    except Exception as e:
        logger.error("Classification failed", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def calculate_confidence(
    graph_score: float,
    vector_score: float,
    llm_score: float,
    graph_classification: dict[str, str],
    vector_classification: dict[str, str],
    llm_classification: dict[str, str],
) -> dict[str, Any]:
    """
    Calculate combined confidence score from multiple sources.

    Uses weighted ensemble and calibration to produce a final
    confidence score that indicates classification reliability.

    Args:
        graph_score: Confidence from graph-based classification
        vector_score: Confidence from vector similarity
        llm_score: Confidence from LLM judgment
        graph_classification: Category from graph
        vector_classification: Category from vectors
        llm_classification: Category from LLM

    Returns:
        Combined confidence with breakdown and agreement score
    """
    from nexusflow.agents.confidence import calculate_combined_confidence

    confidence = calculate_combined_confidence(
        graph_score=graph_score,
        vector_score=vector_score,
        llm_score=llm_score,
        graph_classification=graph_classification,
        vector_classification=vector_classification,
        llm_classification=llm_classification,
    )

    # Determine routing
    threshold = settings.classification_confidence_threshold
    hitl_threshold = settings.hitl_threshold

    return {
        "calibrated_score": confidence["calibrated_score"],
        "raw_score": confidence["raw_score"],
        "component_agreement": confidence["component_agreement"],
        "components": {
            "graph": graph_score,
            "vector": vector_score,
            "llm": llm_score,
        },
        "weights": confidence["weights"],
        "routing": {
            "auto_resolved": confidence["calibrated_score"] >= threshold,
            "requires_hitl": confidence["calibrated_score"] < threshold
            and confidence["calibrated_score"] >= hitl_threshold,
            "needs_escalation": confidence["calibrated_score"] < hitl_threshold,
        },
    }


@mcp.tool()
async def get_llm_classification(
    title: str,
    description: str,
    available_categories: list[str],
    similar_tickets: list[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Get classification from LLM as final judge.

    The LLM reviews the ticket and suggested categories to make
    a final classification decision with reasoning.

    Args:
        title: Ticket title
        description: Ticket description
        available_categories: List of valid category paths
        similar_tickets: Optional similar tickets for context

    Returns:
        LLM classification with reasoning and confidence
    """
    from nexusflow.agents.classification_agent import ClassificationAgent

    try:
        agent = ClassificationAgent()

        result = await agent.get_llm_judgment(
            title=title,
            description=description,
            available_categories=available_categories,
            similar_tickets=similar_tickets or [],
        )

        return result
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# HITL Tools
# =============================================================================


@mcp.tool()
async def create_hitl_task(
    ticket_id: str,
    ticket_title: str,
    ticket_description: str,
    ai_level1: str,
    ai_level2: str,
    ai_level3: str,
    ai_confidence: float,
    routing_reason: str,
    confidence_details: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Create a Human-in-the-Loop review task for a ticket.

    Called when confidence is below threshold and human review is needed.

    Args:
        ticket_id: The ticket identifier
        ticket_title: Ticket title
        ticket_description: Ticket description
        ai_level1: AI suggested Level 1 category
        ai_level2: AI suggested Level 2 category
        ai_level3: AI suggested Level 3 category
        ai_confidence: AI confidence score
        routing_reason: Reason for HITL routing
        confidence_details: Detailed confidence breakdown

    Returns:
        Created HITL task details
    """
    from nexusflow.db.repository import HITLTaskRepository

    try:
        task = await HITLTaskRepository.create(
            ticket_id=ticket_id,
            ticket_title=ticket_title,
            ticket_description=ticket_description,
            ai_level1=ai_level1,
            ai_level2=ai_level2,
            ai_level3=ai_level3,
            ai_confidence=ai_confidence,
            routing_reason=routing_reason,
            confidence_details=confidence_details or {},
        )

        return {
            "success": True,
            "task_id": task.id,
            "ticket_id": ticket_id,
            "status": task.status,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_hitl_queue_stats() -> dict[str, Any]:
    """
    Get statistics about the HITL review queue.

    Returns counts of pending, in-progress, and completed tasks.

    Returns:
        HITL queue statistics
    """
    from nexusflow.db.repository import HITLCorrectionRepository, HITLTaskRepository

    task_counts = await HITLTaskRepository.count_by_status()
    accuracy = await HITLCorrectionRepository.get_accuracy_rate()
    avg_time = await HITLCorrectionRepository.get_avg_review_time()

    return {
        "queue": task_counts,
        "pending": task_counts.get("pending", 0) + task_counts.get("in_progress", 0),
        "completed": task_counts.get("completed", 0),
        "ai_accuracy": accuracy,
        "avg_review_time_seconds": avg_time,
    }


# =============================================================================
# Batch Processing Tools
# =============================================================================


@mcp.tool()
async def submit_batch(
    tickets: list[dict[str, Any]],
    batch_id: str = None,
    callback_url: str = None,
) -> dict[str, Any]:
    """
    Submit a batch of tickets for classification.

    Processes multiple tickets with parallel processing for efficiency.

    Args:
        tickets: List of ticket dicts with title, description, priority
        batch_id: Optional custom batch identifier
        callback_url: Optional webhook for completion notification

    Returns:
        Batch submission confirmation with tracking ID
    """
    from nexusflow.services.batch import get_batch_processor

    try:
        batch_processor = get_batch_processor()

        ticket_creates = []
        for t in tickets:
            try:
                priority = TicketPriority(t.get("priority", "medium").lower())
            except ValueError:
                priority = TicketPriority.MEDIUM

            ticket_creates.append(
                TicketCreate(
                    title=t["title"],
                    description=t["description"],
                    priority=priority,
                    source=t.get("source", "mcp"),
                    customer_id=t.get("customer_id"),
                    metadata=t.get("metadata", {}),
                )
            )

        submitted_id = await batch_processor.submit_batch(
            tickets=ticket_creates,
            batch_id=batch_id,
            callback_url=callback_url,
        )

        return {
            "batch_id": submitted_id,
            "ticket_count": len(tickets),
            "status": "pending",
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_batch_status(batch_id: str) -> dict[str, Any]:
    """
    Get the current status of a batch classification job.

    Args:
        batch_id: The batch identifier

    Returns:
        Batch status with progress information
    """
    from nexusflow.services.batch import get_batch_processor

    batch_processor = get_batch_processor()
    status = batch_processor.get_batch_status(batch_id)

    if not status:
        return {"error": "Batch not found", "batch_id": batch_id}

    return status


# =============================================================================
# System Tools
# =============================================================================


@mcp.tool()
async def get_system_health() -> dict[str, Any]:
    """
    Check health of all system components.

    Returns status of API, Neo4j, Milvus, and other services.

    Returns:
        Health status of all components
    """
    health = {
        "api": "healthy",
        "neo4j": "unknown",
        "milvus": "unknown",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Check Neo4j
    try:
        from nexusflow.db import get_neo4j_client

        neo4j = await get_neo4j_client()
        await neo4j.get_graph_statistics()
        health["neo4j"] = "healthy"
    except Exception as e:
        health["neo4j"] = f"unhealthy: {str(e)}"

    # Check Milvus
    try:
        from nexusflow.db import get_milvus_client

        milvus = get_milvus_client()
        milvus.get_collection_stats()
        health["milvus"] = "healthy"
    except Exception as e:
        health["milvus"] = f"unhealthy: {str(e)}"

    return health


@mcp.tool()
async def get_configuration() -> dict[str, Any]:
    """
    Get current system configuration (non-sensitive).

    Returns thresholds and settings for classification.

    Returns:
        System configuration values
    """
    return {
        "confidence_threshold": settings.classification_confidence_threshold,
        "hitl_threshold": settings.hitl_threshold,
        "batch_size": settings.batch_size,
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "default_model": settings.nexusflow_default_model,
    }


# =============================================================================
# Resources
# =============================================================================


@mcp.resource("nexusflow://stats")
async def stats_resource() -> str:
    """Get system statistics as a resource."""
    from nexusflow.db import get_milvus_client, get_neo4j_client

    try:
        neo4j = await get_neo4j_client()
        graph_stats = await neo4j.get_graph_statistics()
    except Exception:
        graph_stats = {}

    try:
        milvus = get_milvus_client()
        vector_stats = milvus.get_collection_stats()
    except Exception:
        vector_stats = {}

    return json.dumps(
        {
            "graph": graph_stats,
            "vectors": vector_stats,
            "config": {
                "confidence_threshold": settings.classification_confidence_threshold,
                "hitl_threshold": settings.hitl_threshold,
            },
        },
        indent=2,
    )


@mcp.resource("nexusflow://categories")
async def categories_resource() -> str:
    """Get all classification categories as a resource."""
    from nexusflow.db import get_neo4j_client

    try:
        neo4j = await get_neo4j_client()
        paths = await neo4j.get_all_paths()

        categories = [f"{p['level1']} > {p['level2']} > {p['level3']}" for p in paths]
        return "\n".join(sorted(set(categories)))
    except Exception as e:
        return f"Error: {e}"


@mcp.resource("nexusflow://readme")
async def readme_resource() -> str:
    """Get system documentation."""
    return """
# NexusFlow MCP Tools

## Classification Workflow

1. **query_graph_categories** - Find matching categories from graph DB
2. **search_similar_tickets** - Find similar historical tickets
3. **calculate_confidence** - Combine scores from multiple sources
4. **get_llm_classification** - Get LLM final judgment
5. **classify_ticket** - Full classification pipeline

## Database Tools

- **get_graph_statistics** - Graph DB stats
- **get_vector_statistics** - Vector DB stats
- **update_graph_classification** - Record classification in graph
- **index_ticket_vector** - Index ticket in vector DB

## HITL Tools

- **create_hitl_task** - Create review task
- **get_hitl_queue_stats** - Queue statistics

## Batch Tools

- **submit_batch** - Submit batch for processing
- **get_batch_status** - Check batch status
"""


# =============================================================================
# Server Entry Points
# =============================================================================


def create_mcp_server() -> FastMCP:
    """Create and return the MCP server instance."""
    return mcp


async def run_mcp_server(
    host: str = "0.0.0.0",
    port: int = None,
):
    """Run the MCP server."""
    if port is None:
        port = settings.nexusflow_mcp_port

    logger.info("Starting NexusFlow MCP server", host=host, port=port)

    # Initialize database
    from nexusflow.db.session import init_db

    await init_db()

    # Run the server
    await mcp.run_async(host=host, port=port)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_mcp_server())
