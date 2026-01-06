"""
WebSocket endpoints for real-time updates.

Provides real-time streaming of:
- Classification pipeline progress
- HITL task updates  
- Graph learning events
- System metrics
"""

import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from nexusflow.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {
            "classification": [],
            "hitl": [],
            "graph": [],
            "metrics": [],
        }
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str):
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            if channel in self.active_connections:
                self.active_connections[channel].append(websocket)
        logger.info("WebSocket connected", channel=channel)

    async def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a disconnected WebSocket."""
        async with self._lock:
            if channel in self.active_connections:
                try:
                    self.active_connections[channel].remove(websocket)
                except ValueError:
                    pass
        logger.info("WebSocket disconnected", channel=channel)

    async def broadcast(self, channel: str, message: dict[str, Any]):
        """Broadcast a message to all connections in a channel."""
        if channel not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected sockets
        for conn in disconnected:
            await self.disconnect(conn, channel)


manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return manager


@router.websocket("/ws/classification/{ticket_id}")
async def classification_stream(websocket: WebSocket, ticket_id: str):
    """
    Stream classification pipeline progress for a specific ticket.
    
    Sends events:
    - stage_start: When a pipeline stage begins
    - stage_complete: When a stage completes with results
    - classification_complete: Final classification result
    - error: If an error occurs
    """
    await manager.connect(websocket, "classification")
    
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                # Handle ping/pong for keepalive
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({"type": "keepalive", "timestamp": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "classification")


@router.websocket("/ws/hitl")
async def hitl_stream(websocket: WebSocket):
    """
    Stream HITL queue updates in real-time.
    
    Sends events:
    - task_created: New task added to queue
    - task_assigned: Task assigned to reviewer
    - task_completed: Task completed with correction
    - stats_update: Updated queue statistics
    """
    await manager.connect(websocket, "hitl")
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "keepalive", "timestamp": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "hitl")


@router.websocket("/ws/graph")
async def graph_stream(websocket: WebSocket):
    """
    Stream graph learning and evolution events.
    
    Sends events:
    - node_updated: Node weights/accuracy updated
    - edge_updated: Edge strength changed
    - learning_event: New learning from HITL correction
    - graph_stats: Periodic graph statistics
    """
    await manager.connect(websocket, "graph")
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send periodic graph stats
                await websocket.send_json({
                    "type": "keepalive",
                    "timestamp": datetime.utcnow().isoformat()
                })
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "graph")


@router.websocket("/ws/metrics")
async def metrics_stream(websocket: WebSocket):
    """
    Stream real-time system metrics.
    
    Sends events:
    - metrics_update: Periodic metrics snapshot
    - classification_event: Each classification completed
    - throughput_update: Processing throughput stats
    """
    await manager.connect(websocket, "metrics")
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=5.0
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send metrics update
                await websocket.send_json({
                    "type": "metrics_update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "active_connections": sum(
                            len(conns) for conns in manager.active_connections.values()
                        ),
                    }
                })
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "metrics")


# Event broadcasting functions for use by other modules

async def broadcast_classification_stage(
    ticket_id: str,
    stage: str,
    status: str,
    result: dict[str, Any] | None = None,
    duration_ms: int | None = None,
):
    """Broadcast a classification pipeline stage update."""
    await manager.broadcast("classification", {
        "type": f"stage_{status}",
        "ticket_id": ticket_id,
        "stage": stage,
        "result": result,
        "duration_ms": duration_ms,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_classification_complete(
    ticket_id: str,
    classification: dict[str, str],
    confidence: dict[str, float],
    routing: dict[str, Any],
    processing_time_ms: int,
):
    """Broadcast a completed classification."""
    await manager.broadcast("classification", {
        "type": "classification_complete",
        "ticket_id": ticket_id,
        "classification": classification,
        "confidence": confidence,
        "routing": routing,
        "processing_time_ms": processing_time_ms,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Also send to metrics channel
    await manager.broadcast("metrics", {
        "type": "classification_event",
        "ticket_id": ticket_id,
        "confidence": confidence.get("calibrated_score", 0),
        "auto_resolved": routing.get("auto_resolved", False),
        "processing_time_ms": processing_time_ms,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_hitl_update(
    event_type: str,
    task_id: str,
    data: dict[str, Any] | None = None,
):
    """Broadcast an HITL queue update."""
    await manager.broadcast("hitl", {
        "type": event_type,
        "task_id": task_id,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_graph_learning(
    event_type: str,
    node_id: str | None = None,
    data: dict[str, Any] | None = None,
):
    """Broadcast a graph learning event."""
    await manager.broadcast("graph", {
        "type": event_type,
        "node_id": node_id,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    })

