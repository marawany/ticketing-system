"""
Batch Processing Service

Handles batch ticket processing with queue management and callbacks.
Supports real-time streaming of processing events.
"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

from nexusflow.models.ticket import TicketCreate
from nexusflow.services.classification import ClassificationService

logger = structlog.get_logger(__name__)

# Global event subscribers for streaming
_event_subscribers: dict[str, list[asyncio.Queue]] = {}


class BatchStatus(str, Enum):
    """Status of a batch processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchJob:
    """Represents a batch processing job."""

    def __init__(
        self,
        batch_id: str,
        tickets: list[TicketCreate],
        callback_url: str | None = None,
    ):
        self.batch_id = batch_id
        self.tickets = tickets
        self.callback_url = callback_url
        self.status = BatchStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.progress: int = 0  # 0-100


class BatchProcessor:
    """
    Batch processor for handling large volumes of tickets.

    Features:
    - Queue management
    - Progress tracking
    - Async processing
    - Webhook callbacks
    """

    def __init__(self, max_concurrent_batches: int = 3):
        self._classification_service = ClassificationService()
        self._jobs: dict[str, BatchJob] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._max_concurrent = max_concurrent_batches
        self._workers_running = False
        self._callback_handler: Callable | None = None

    def set_callback_handler(self, handler: Callable):
        """Set custom callback handler for batch completion."""
        self._callback_handler = handler

    async def start_workers(self):
        """Start background workers for processing batches."""
        if self._workers_running:
            return

        self._workers_running = True
        for i in range(self._max_concurrent):
            asyncio.create_task(self._worker(f"worker-{i}"))

        logger.info("Batch workers started", count=self._max_concurrent)

    async def stop_workers(self):
        """Stop background workers."""
        self._workers_running = False
        logger.info("Batch workers stopped")

    async def submit_batch(
        self,
        tickets: list[TicketCreate],
        batch_id: str | None = None,
        callback_url: str | None = None,
    ) -> str:
        """
        Submit a batch for processing.

        Args:
            tickets: List of tickets to process
            batch_id: Optional custom batch ID
            callback_url: URL to call when batch completes

        Returns:
            The batch ID
        """
        if batch_id is None:
            batch_id = f"batch_{uuid4().hex[:12]}"

        job = BatchJob(
            batch_id=batch_id,
            tickets=tickets,
            callback_url=callback_url,
        )

        self._jobs[batch_id] = job
        await self._queue.put(batch_id)

        logger.info(
            "Batch submitted",
            batch_id=batch_id,
            ticket_count=len(tickets),
            callback=callback_url,
        )

        # Ensure workers are running
        await self.start_workers()

        return batch_id

    def get_batch_status(self, batch_id: str) -> dict[str, Any] | None:
        """Get the status of a batch job."""
        job = self._jobs.get(batch_id)
        if not job:
            return None

        return {
            "batch_id": job.batch_id,
            "status": job.status.value,
            "ticket_count": len(job.tickets),
            "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
        }

    def get_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        """Get the result of a completed batch job."""
        job = self._jobs.get(batch_id)
        if not job or job.status != BatchStatus.COMPLETED:
            return None
        return job.result

    def list_batches(
        self,
        status: BatchStatus | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List batch jobs with optional status filter."""
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return [self.get_batch_status(j.batch_id) for j in jobs[:limit]]

    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a pending batch job."""
        job = self._jobs.get(batch_id)
        if not job:
            return False

        if job.status == BatchStatus.PENDING:
            job.status = BatchStatus.CANCELLED
            logger.info("Batch cancelled", batch_id=batch_id)
            return True

        return False

    async def _worker(self, worker_id: str):
        """Background worker for processing batches."""
        logger.info("Worker started", worker_id=worker_id)

        while self._workers_running:
            try:
                # Wait for a job with timeout
                try:
                    batch_id = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=5.0,
                    )
                except TimeoutError:
                    continue

                job = self._jobs.get(batch_id)
                if not job or job.status == BatchStatus.CANCELLED:
                    continue

                # Process the batch
                await self._process_batch(job, worker_id)

            except Exception as e:
                logger.error("Worker error", worker_id=worker_id, error=str(e))

        logger.info("Worker stopped", worker_id=worker_id)

    async def _process_batch(self, job: BatchJob, worker_id: str):
        """Process a single batch job."""
        job.status = BatchStatus.PROCESSING
        job.started_at = datetime.utcnow()

        logger.info(
            "Processing batch",
            batch_id=job.batch_id,
            worker_id=worker_id,
            ticket_count=len(job.tickets),
        )

        try:
            # Emit start event
            await emit_batch_event(job.batch_id, {
                "type": "batch_started",
                "batch_id": job.batch_id,
                "total_tickets": len(job.tickets),
                "timestamp": datetime.utcnow().isoformat(),
                "worker_id": worker_id,
            })
            
            # Process with progress updates
            total = len(job.tickets)
            results = []
            auto_resolved_count = 0
            hitl_count = 0

            for i, ticket in enumerate(job.tickets):
                ticket_start = datetime.utcnow()
                
                # Emit processing event
                await emit_batch_event(job.batch_id, {
                    "type": "ticket_processing",
                    "batch_id": job.batch_id,
                    "ticket_index": i + 1,
                    "total": total,
                    "title": ticket.title[:60],
                    "timestamp": ticket_start.isoformat(),
                })
                
                result = await self._classification_service.classify_ticket(ticket)
                results.append(result)
                job.progress = int((i + 1) / total * 100)
                
                # Track stats
                is_auto = result["routing"]["auto_resolved"]
                if is_auto:
                    auto_resolved_count += 1
                else:
                    hitl_count += 1
                
                processing_ms = int((datetime.utcnow() - ticket_start).total_seconds() * 1000)
                
                # Emit completion event with details
                await emit_batch_event(job.batch_id, {
                    "type": "ticket_classified",
                    "batch_id": job.batch_id,
                    "ticket_index": i + 1,
                    "total": total,
                    "progress": job.progress,
                    "title": ticket.title[:60],
                    "classification": result["classification"],
                    "confidence": {
                        "graph": result["confidence"].get("graph_confidence", 0),
                        "vector": result["confidence"].get("vector_confidence", 0),
                        "llm": result["confidence"].get("llm_confidence", 0),
                        "final": result["confidence"].get("calibrated_score", 0),
                    },
                    "routing": result["routing"],
                    "processing_ms": processing_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                    "auto_resolved_so_far": auto_resolved_count,
                    "hitl_so_far": hitl_count,
                })

            # Calculate summary
            auto_resolved = sum(1 for r in results if r["routing"]["auto_resolved"])
            requires_hitl = sum(1 for r in results if r["routing"]["requires_hitl"])

            job.result = {
                "batch_id": job.batch_id,
                "total_tickets": total,
                "successful": total,
                "failed": 0,
                "auto_resolved": auto_resolved,
                "requires_hitl": requires_hitl,
                "results": results,
                "processing_time_ms": int(
                    (datetime.utcnow() - job.started_at).total_seconds() * 1000
                ),
            }

            job.status = BatchStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress = 100

            logger.info(
                "Batch completed",
                batch_id=job.batch_id,
                total=total,
                auto_resolved=auto_resolved,
                requires_hitl=requires_hitl,
            )
            
            # Emit completion event
            await emit_batch_event(job.batch_id, {
                "type": "batch_completed",
                "batch_id": job.batch_id,
                "total_tickets": total,
                "auto_resolved": auto_resolved,
                "requires_hitl": requires_hitl,
                "processing_time_ms": job.result["processing_time_ms"],
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Trigger callback
            await self._trigger_callback(job)

        except Exception as e:
            job.status = BatchStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()

            logger.error(
                "Batch failed",
                batch_id=job.batch_id,
                error=str(e),
            )

    async def _trigger_callback(self, job: BatchJob):
        """Trigger webhook callback for completed batch."""
        if not job.callback_url:
            return

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    job.callback_url,
                    json={
                        "batch_id": job.batch_id,
                        "status": job.status.value,
                        "result": job.result,
                    },
                    timeout=30.0,
                )

                logger.info(
                    "Callback sent",
                    batch_id=job.batch_id,
                    url=job.callback_url,
                    status_code=response.status_code,
                )
        except Exception as e:
            logger.error(
                "Callback failed",
                batch_id=job.batch_id,
                url=job.callback_url,
                error=str(e),
            )

        # Also trigger custom handler if set
        if self._callback_handler:
            try:
                await self._callback_handler(job)
            except Exception as e:
                logger.error("Custom callback handler failed", error=str(e))


# Streaming event functions
def subscribe_to_batch(batch_id: str) -> asyncio.Queue:
    """Subscribe to real-time events for a batch."""
    if batch_id not in _event_subscribers:
        _event_subscribers[batch_id] = []
    queue = asyncio.Queue()
    _event_subscribers[batch_id].append(queue)
    return queue


def unsubscribe_from_batch(batch_id: str, queue: asyncio.Queue):
    """Unsubscribe from batch events."""
    if batch_id in _event_subscribers:
        try:
            _event_subscribers[batch_id].remove(queue)
            if not _event_subscribers[batch_id]:
                del _event_subscribers[batch_id]
        except ValueError:
            pass


async def emit_batch_event(batch_id: str, event: dict[str, Any]):
    """Emit an event to all subscribers of a batch."""
    if batch_id not in _event_subscribers:
        return
    
    for queue in _event_subscribers[batch_id]:
        try:
            await queue.put(event)
        except Exception:
            pass


# Singleton instance
_batch_processor: BatchProcessor | None = None


def get_batch_processor() -> BatchProcessor:
    """Get or create the batch processor singleton."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor
