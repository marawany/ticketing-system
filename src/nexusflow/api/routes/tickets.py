"""
Ticket Routes

Endpoints for ticket management and operations.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from nexusflow.db.repository import TicketRepository
from nexusflow.models.ticket import (
    Ticket,
    TicketCreate,
    TicketPriority,
    TicketStatus,
    TicketUpdate,
)

router = APIRouter()


class TicketResponse(BaseModel):
    """Response model for ticket operations."""

    ticket: Ticket
    message: str = "Success"


class TicketListResponse(BaseModel):
    """Response model for ticket list."""

    tickets: list[Ticket]
    total: int
    page: int
    page_size: int


def db_to_model(db_ticket) -> Ticket:
    """Convert database ticket to Pydantic model."""
    return Ticket(
        id=UUID(db_ticket.id),
        title=db_ticket.title,
        description=db_ticket.description,
        priority=TicketPriority(db_ticket.priority),
        status=TicketStatus(db_ticket.status),
        source=db_ticket.source,
        customer_id=db_ticket.customer_id,
        metadata=db_ticket.extra_data or {},
        level1_category=db_ticket.level1_category,
        level2_category=db_ticket.level2_category,
        level3_category=db_ticket.level3_category,
        classification_confidence=db_ticket.classification_confidence,
        created_at=db_ticket.created_at,
        updated_at=db_ticket.updated_at,
        classified_at=db_ticket.classified_at,
        resolved_at=db_ticket.resolved_at,
        processing_time_ms=db_ticket.processing_time_ms,
        assigned_to=db_ticket.assigned_to,
        resolution=db_ticket.resolution,
    )


@router.post("", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate):
    """
    Create a new ticket.

    The ticket will be stored and can be classified later.
    """
    db_ticket = await TicketRepository.create(
        title=ticket.title,
        description=ticket.description,
        priority=ticket.priority.value,
        source=ticket.source,
        customer_id=ticket.customer_id,
        metadata=ticket.metadata,
    )

    return TicketResponse(
        ticket=db_to_model(db_ticket),
        message="Ticket created successfully",
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: UUID):
    """
    Get a ticket by ID.
    """
    db_ticket = await TicketRepository.get(str(ticket_id))
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketResponse(ticket=db_to_model(db_ticket))


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: UUID, update: TicketUpdate):
    """
    Update an existing ticket.
    """
    # Check if ticket exists
    existing = await TicketRepository.get(str(ticket_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")

    update_data = update.model_dump(exclude_unset=True)

    # Convert enums to strings
    if "priority" in update_data and update_data["priority"]:
        update_data["priority"] = update_data["priority"].value
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value

    db_ticket = await TicketRepository.update(str(ticket_id), **update_data)

    return TicketResponse(
        ticket=db_to_model(db_ticket),
        message="Ticket updated successfully",
    )


@router.delete("/{ticket_id}")
async def delete_ticket(ticket_id: UUID):
    """
    Delete a ticket.
    """
    success = await TicketRepository.delete(str(ticket_id))
    if not success:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {"message": "Ticket deleted successfully", "ticket_id": str(ticket_id)}


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    List tickets with optional filtering.
    """
    status_str = status.value if status else None
    priority_str = priority.value if priority else None

    db_tickets, total = await TicketRepository.list(
        status=status_str,
        priority=priority_str,
        page=page,
        page_size=page_size,
    )

    tickets = [db_to_model(t) for t in db_tickets]

    return TicketListResponse(
        tickets=tickets,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: UUID,
    resolution: str = None,
):
    """
    Mark a ticket as resolved.
    """
    existing = await TicketRepository.get(str(ticket_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")

    db_ticket = await TicketRepository.update(
        str(ticket_id),
        status="resolved",
        resolved_at=datetime.utcnow(),
        resolution=resolution,
    )

    return {
        "message": "Ticket resolved",
        "ticket_id": str(ticket_id),
        "status": db_ticket.status,
    }


@router.post("/{ticket_id}/escalate")
async def escalate_ticket(
    ticket_id: UUID,
    reason: str = None,
):
    """
    Escalate a ticket for priority handling.
    """
    existing = await TicketRepository.get(str(ticket_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")

    db_ticket = await TicketRepository.update(
        str(ticket_id),
        status="escalated",
    )

    return {
        "message": "Ticket escalated",
        "ticket_id": str(ticket_id),
        "status": db_ticket.status,
        "reason": reason,
    }
