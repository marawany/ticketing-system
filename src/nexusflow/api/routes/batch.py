"""
Batch Processing Routes

Endpoints for batch ticket processing with WebSocket streaming.
"""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from nexusflow.models.ticket import TicketCreate, TicketPriority
from nexusflow.services.batch import (
    BatchStatus, 
    get_batch_processor, 
    subscribe_to_batch, 
    unsubscribe_from_batch
)

router = APIRouter()


class BatchTicket(BaseModel):
    """Model for a ticket in a batch."""

    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    priority: str = Field(default="medium")
    source: str | None = None
    customer_id: str | None = None
    metadata: dict[str, Any] | None = None


class BatchSubmitRequest(BaseModel):
    """Request model for batch submission."""

    tickets: list[BatchTicket] = Field(..., min_length=1, max_length=1000)
    batch_id: str | None = None
    callback_url: str | None = None


class BatchSubmitResponse(BaseModel):
    """Response model for batch submission."""

    batch_id: str
    ticket_count: int
    status: str
    message: str


class BatchStatusResponse(BaseModel):
    """Response model for batch status."""

    batch_id: str
    status: str
    ticket_count: int
    progress: int
    created_at: str | None
    started_at: str | None
    completed_at: str | None
    error: str | None


class BatchListResponse(BaseModel):
    """Response model for batch list."""

    batches: list[dict[str, Any]]
    count: int


@router.post("/submit", response_model=BatchSubmitResponse)
async def submit_batch(
    request: BatchSubmitRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit a batch of tickets for classification.

    The batch will be processed asynchronously.
    Use the batch_id to track progress and retrieve results.
    """
    processor = get_batch_processor()

    # Convert to TicketCreate objects
    ticket_creates = []
    for t in request.tickets:
        try:
            priority = TicketPriority(t.priority.lower())
        except ValueError:
            priority = TicketPriority.MEDIUM

        ticket_creates.append(
            TicketCreate(
                title=t.title,
                description=t.description,
                priority=priority,
                source=t.source,
                customer_id=t.customer_id,
                metadata=t.metadata or {},
            )
        )

    batch_id = await processor.submit_batch(
        tickets=ticket_creates,
        batch_id=request.batch_id,
        callback_url=request.callback_url,
    )

    return BatchSubmitResponse(
        batch_id=batch_id,
        ticket_count=len(request.tickets),
        status="pending",
        message="Batch submitted for processing",
    )


@router.get("/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """
    Get the status of a batch job.
    """
    processor = get_batch_processor()

    status = processor.get_batch_status(batch_id)
    if not status:
        raise HTTPException(status_code=404, detail="Batch not found")

    return BatchStatusResponse(**status)


@router.get("/{batch_id}/result")
async def get_batch_result(batch_id: str):
    """
    Get the results of a completed batch job.

    Only available after batch status is 'completed'.
    """
    processor = get_batch_processor()

    status = processor.get_batch_status(batch_id)
    if not status:
        raise HTTPException(status_code=404, detail="Batch not found")

    if status["status"] != "completed":
        raise HTTPException(
            status_code=400, detail=f"Batch not completed. Current status: {status['status']}"
        )

    result = processor.get_batch_result(batch_id)
    return result


@router.get("", response_model=BatchListResponse)
async def list_batches(
    status: str | None = None,
    limit: int = 50,
):
    """
    List batch jobs with optional status filter.
    """
    processor = get_batch_processor()

    status_enum = None
    if status:
        try:
            status_enum = BatchStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid values: {[s.value for s in BatchStatus]}",
            )

    batches = processor.list_batches(status=status_enum, limit=limit)

    return BatchListResponse(batches=batches, count=len(batches))


@router.post("/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    """
    Cancel a pending batch job.

    Only works for batches that haven't started processing yet.
    """
    processor = get_batch_processor()

    success = processor.cancel_batch(batch_id)
    if not success:
        status = processor.get_batch_status(batch_id)
        if not status:
            raise HTTPException(status_code=404, detail="Batch not found")
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel batch. Current status: {status['status']}"
        )

    return {"message": "Batch cancelled", "batch_id": batch_id}


@router.post("/{batch_id}/retry")
async def retry_batch(batch_id: str):
    """
    Retry a failed batch job.
    """
    processor = get_batch_processor()

    status = processor.get_batch_status(batch_id)
    if not status:
        raise HTTPException(status_code=404, detail="Batch not found")

    if status["status"] != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed batches. Current status: {status['status']}",
        )

    # Re-submit the batch
    # This would require storing the original tickets
    raise HTTPException(status_code=501, detail="Retry not yet implemented")


@router.websocket("/stream/{batch_id}")
async def stream_batch_events(websocket: WebSocket, batch_id: str):
    """
    WebSocket endpoint for real-time batch processing updates.
    
    Streams events as JSON:
    - batch_started: Batch processing has begun
    - ticket_processing: A ticket is being processed
    - ticket_classified: A ticket has been classified (includes full details)
    - batch_completed: Batch processing is complete
    """
    await websocket.accept()
    
    # Subscribe to batch events
    event_queue = subscribe_to_batch(batch_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "batch_id": batch_id,
            "message": "Connected to batch stream"
        })
        
        # Stream events until batch completes or client disconnects
        while True:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                await websocket.send_json(event)
                
                # Stop streaming after batch completion
                if event.get("type") in ("batch_completed", "batch_failed"):
                    break
                    
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe_from_batch(batch_id, event_queue)


@router.post("/submit-and-stream")
async def submit_batch_for_streaming(
    request: BatchSubmitRequest,
):
    """
    Submit a batch and return batch_id for WebSocket streaming.
    
    Use the returned batch_id to connect to /api/v1/batch/stream/{batch_id}
    for real-time updates.
    """
    processor = get_batch_processor()

    # Convert to TicketCreate objects
    ticket_creates = []
    for t in request.tickets:
        try:
            priority = TicketPriority(t.priority.lower())
        except ValueError:
            priority = TicketPriority.MEDIUM

        ticket_creates.append(
            TicketCreate(
                title=t.title,
                description=t.description,
                priority=priority,
                source=t.source,
                customer_id=t.customer_id,
                metadata=t.metadata or {},
            )
        )

    batch_id = await processor.submit_batch(
        tickets=ticket_creates,
        batch_id=request.batch_id,
        callback_url=request.callback_url,
    )

    return {
        "batch_id": batch_id,
        "ticket_count": len(request.tickets),
        "status": "pending",
        "stream_url": f"/api/v1/batch/stream/{batch_id}",
        "message": "Connect to stream_url via WebSocket for real-time updates"
    }
