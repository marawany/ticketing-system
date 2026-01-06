"""
Classification Service

High-level service for ticket classification operations.
"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import uuid4

import structlog

from nexusflow.agents.classification_agent import ClassificationAgent, get_classification_agent
from nexusflow.db.milvus_client import MilvusClient, get_milvus_client
from nexusflow.db.neo4j_client import Neo4jClient, get_neo4j_client
from nexusflow.models.ticket import TicketCreate
from nexusflow.services.embeddings import EmbeddingService, get_embedding_service

logger = structlog.get_logger(__name__)


class ClassificationService:
    """
    Service for classifying tickets.

    Provides high-level API for:
    - Single ticket classification
    - Batch classification
    - Retrieving classification results
    - Managing classification feedback
    """

    def __init__(self):
        self._agent: ClassificationAgent | None = None
        self._neo4j: Neo4jClient | None = None
        self._milvus: MilvusClient | None = None
        self._embeddings: EmbeddingService | None = None

    async def _ensure_services(self):
        """Initialize all required services."""
        if self._agent is None:
            self._agent = await get_classification_agent()
        if self._neo4j is None:
            self._neo4j = await get_neo4j_client()
        if self._milvus is None:
            self._milvus = get_milvus_client()
        if self._embeddings is None:
            self._embeddings = get_embedding_service()

    async def classify_ticket(
        self,
        ticket: TicketCreate,
        ticket_id: str = None,
    ) -> dict[str, Any]:
        """
        Classify a single ticket.

        Args:
            ticket: The ticket to classify
            ticket_id: Optional ticket ID (generated if not provided)

        Returns:
            Classification result with confidence and routing decision
        """
        await self._ensure_services()

        if ticket_id is None:
            ticket_id = str(uuid4())

        logger.info("Classifying ticket", ticket_id=ticket_id, title=ticket.title[:50])

        # Run classification
        result = await self._agent.classify(
            ticket_id=ticket_id,
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority.value,
            metadata=ticket.metadata,
        )

        # Store ticket embedding for future similarity search
        await self._store_ticket_embedding(
            ticket_id=ticket_id,
            title=ticket.title,
            description=ticket.description,
            classification=result["classification"],
        )

        # Update graph with new ticket
        await self._update_graph(
            ticket_id=ticket_id,
            classification=result["classification"],
        )

        return result

    async def classify_batch(
        self,
        tickets: list[TicketCreate],
        batch_id: str = None,
        concurrency: int = 5,
    ) -> dict[str, Any]:
        """
        Classify a batch of tickets.

        Args:
            tickets: List of tickets to classify
            batch_id: Optional batch identifier
            concurrency: Number of concurrent classifications

        Returns:
            Batch result with individual results and summary
        """
        await self._ensure_services()

        if batch_id is None:
            batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        logger.info("Starting batch classification", batch_id=batch_id, count=len(tickets))

        start_time = datetime.utcnow()

        # Process in batches with concurrency limit
        semaphore = asyncio.Semaphore(concurrency)

        async def classify_with_limit(ticket: TicketCreate, idx: int) -> dict[str, Any]:
            async with semaphore:
                try:
                    ticket_id = str(uuid4())
                    result = await self.classify_ticket(ticket, ticket_id)
                    return {"success": True, "result": result, "index": idx}
                except Exception as e:
                    logger.error("Ticket classification failed", index=idx, error=str(e))
                    return {"success": False, "error": str(e), "index": idx}

        # Run all classifications
        tasks = [classify_with_limit(t, i) for i, t in enumerate(tickets)]
        results = await asyncio.gather(*tasks)

        # Aggregate results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        auto_resolved = sum(1 for r in successful if r["result"]["routing"]["auto_resolved"])
        requires_hitl = sum(1 for r in successful if r["result"]["routing"]["requires_hitl"])

        end_time = datetime.utcnow()
        processing_time = int((end_time - start_time).total_seconds() * 1000)

        batch_result = {
            "batch_id": batch_id,
            "total_tickets": len(tickets),
            "successful": len(successful),
            "failed": len(failed),
            "auto_resolved": auto_resolved,
            "requires_hitl": requires_hitl,
            "results": [r["result"] for r in successful],
            "errors": [{"index": r["index"], "error": r["error"]} for r in failed],
            "processing_time_ms": processing_time,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
        }

        logger.info(
            "Batch classification complete",
            batch_id=batch_id,
            successful=len(successful),
            failed=len(failed),
            time_ms=processing_time,
        )

        return batch_result

    async def _store_ticket_embedding(
        self,
        ticket_id: str,
        title: str,
        description: str,
        classification: dict[str, Any],
    ):
        """Store ticket embedding in Milvus for future similarity search."""
        try:
            embedding = await self._embeddings.embed_ticket(title, description)

            self._milvus.insert_ticket(
                ticket_id=ticket_id,
                embedding=embedding,
                title=title,
                description=description,
                level1_category=classification["level1"],
                level2_category=classification["level2"],
                level3_category=classification["level3"],
                confidence=classification.get("confidence", 1.0),
            )
        except Exception as e:
            logger.warning("Failed to store ticket embedding", ticket_id=ticket_id, error=str(e))

    async def _update_graph(
        self,
        ticket_id: str,
        classification: dict[str, Any],
    ):
        """Update graph with new ticket classification."""
        try:
            await self._neo4j.add_ticket_to_graph(
                ticket_id=ticket_id,
                level3_category=classification["level3"],
                confidence=classification.get("confidence", 1.0),
            )
        except Exception as e:
            logger.warning("Failed to update graph", ticket_id=ticket_id, error=str(e))

    async def get_classification(self, ticket_id: str) -> dict[str, Any] | None:
        """Get classification result for a ticket."""
        # This would typically query a results store
        # For now, return None (implement with proper storage later)
        return None

    async def get_similar_tickets(
        self,
        title: str,
        description: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find similar tickets based on content."""
        await self._ensure_services()

        embedding = await self._embeddings.embed_ticket(title, description)
        matches = self._milvus.search_similar(embedding, limit=limit)

        return matches

    async def get_category_suggestions(
        self,
        title: str,
        description: str,
    ) -> list[dict[str, Any]]:
        """Get category suggestions without full classification."""
        await self._ensure_services()

        # Extract keywords
        text = f"{title} {description}"
        keywords = text.lower().split()[:10]

        # Get graph suggestions
        paths = await self._neo4j.get_classification_path(text, keywords)

        # Get vector suggestions
        embedding = await self._embeddings.embed_ticket(title, description)
        vector_result = self._milvus.get_classification_confidence(embedding, limit=5)

        # Combine suggestions
        suggestions = []

        # Add graph suggestions
        for path in paths[:3]:
            suggestions.append(
                {
                    "source": "graph",
                    "level1": path["level1"],
                    "level2": path["level2"],
                    "level3": path["level3"],
                    "confidence": path["confidence"],
                }
            )

        # Add vector suggestion
        if vector_result.get("level1"):
            suggestions.append(
                {
                    "source": "vector",
                    "level1": vector_result["level1"],
                    "level2": vector_result["level2"],
                    "level3": vector_result["level3"],
                    "confidence": vector_result["confidence"],
                }
            )

        return suggestions
