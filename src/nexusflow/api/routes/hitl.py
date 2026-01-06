"""
Human-in-the-Loop (HITL) Routes

Endpoints for managing HITL review tasks and corrections.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from nexusflow.api.routes.users import get_current_user
from nexusflow.db import get_milvus_client, get_neo4j_client
from nexusflow.db.repository import (
    HITLCorrectionRepository,
    HITLTaskRepository,
    TicketRepository,
    UserRepository,
)
from nexusflow.models.hitl import (
    HITLCorrection,
    HITLCorrectionCreate,
    HITLPriority,
    HITLStats,
    HITLStatus,
    HITLTask,
    HITLTaskCreate,
)
from nexusflow.models.user import User

router = APIRouter()


class TaskListResponse(BaseModel):
    """Response for task list."""

    tasks: list[HITLTask]
    total: int
    page: int
    page_size: int


class CorrectionListResponse(BaseModel):
    """Response for correction list."""

    corrections: list[HITLCorrection]
    total: int


def db_to_task(db_task) -> HITLTask:
    """Convert database task to Pydantic model."""
    return HITLTask(
        id=UUID(db_task.id),
        ticket_id=UUID(db_task.ticket_id),
        ticket_title=db_task.ticket_title,
        ticket_description=db_task.ticket_description,
        ticket_source=db_task.ticket_source,
        ai_level1=db_task.ai_level1,
        ai_level2=db_task.ai_level2,
        ai_level3=db_task.ai_level3,
        ai_confidence=db_task.ai_confidence,
        routing_reason=db_task.routing_reason,
        confidence_details=db_task.confidence_details or {},
        status=HITLStatus(db_task.status) if db_task.status else HITLStatus.PENDING,
        priority=HITLPriority(db_task.priority) if db_task.priority else HITLPriority.NORMAL,
        created_at=db_task.created_at,
        assigned_to=UUID(db_task.assigned_to) if db_task.assigned_to else None,
        assigned_at=db_task.assigned_at,
        completed_by=UUID(db_task.completed_by) if db_task.completed_by else None,
        completed_at=db_task.completed_at,
        review_time_seconds=db_task.review_time_seconds,
        similar_tickets=db_task.similar_tickets or [],
    )


def db_to_correction(db_correction) -> HITLCorrection:
    """Convert database correction to Pydantic model."""
    return HITLCorrection(
        id=UUID(db_correction.id),
        task_id=UUID(db_correction.task_id),
        ticket_id=UUID(db_correction.ticket_id),
        reviewer_id=UUID(db_correction.reviewer_id),
        original_level1=db_correction.original_level1,
        original_level2=db_correction.original_level2,
        original_level3=db_correction.original_level3,
        original_confidence=db_correction.original_confidence,
        corrected_level1=db_correction.corrected_level1,
        corrected_level2=db_correction.corrected_level2,
        corrected_level3=db_correction.corrected_level3,
        is_correct=db_correction.is_correct,
        correction_notes=db_correction.correction_notes,
        confidence_feedback=db_correction.confidence_feedback,
        submitted_at=db_correction.submitted_at,
        review_time_seconds=db_correction.review_time_seconds,
    )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: HITLStatus | None = None,
    priority: HITLPriority | None = None,
    assigned_to: UUID | None = None,
    unassigned_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    List HITL tasks with optional filtering.
    """
    status_str = status.value if status else None
    priority_str = priority.value if priority else None
    assigned_to_str = str(assigned_to) if assigned_to else None

    db_tasks, total = await HITLTaskRepository.list(
        status=status_str,
        priority=priority_str,
        assigned_to=assigned_to_str,
        unassigned_only=unassigned_only,
        page=page,
        page_size=page_size,
    )

    tasks = [db_to_task(t) for t in db_tasks]

    return TaskListResponse(
        tasks=tasks,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks/{task_id}", response_model=HITLTask)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific HITL task.
    """
    db_task = await HITLTaskRepository.get(str(task_id))
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    return db_to_task(db_task)


@router.post("/tasks/{task_id}/assign")
async def assign_task(
    task_id: UUID,
    user_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
):
    """
    Assign a task to a user.

    If no user_id provided, assigns to current user.
    """
    db_task = await HITLTaskRepository.get(str(task_id))
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.status == "completed":
        raise HTTPException(status_code=400, detail="Task already completed")

    assignee_id = str(user_id) if user_id else str(current_user.id)

    db_task = await HITLTaskRepository.assign(str(task_id), assignee_id)

    return {
        "message": "Task assigned",
        "task_id": str(task_id),
        "assigned_to": assignee_id,
    }


@router.post("/tasks/{task_id}/unassign")
async def unassign_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Unassign a task.
    """
    db_task = await HITLTaskRepository.get(str(task_id))
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot unassign completed task")

    await HITLTaskRepository.update(
        str(task_id),
        assigned_to=None,
        assigned_at=None,
        status="pending",
    )

    return {"message": "Task unassigned", "task_id": str(task_id)}


@router.post("/tasks/{task_id}/skip")
async def skip_task(
    task_id: UUID,
    reason: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """
    Skip a task and return it to the queue.
    """
    db_task = await HITLTaskRepository.get(str(task_id))
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    await HITLTaskRepository.update(
        str(task_id),
        assigned_to=None,
        assigned_at=None,
        status="pending",
    )

    return {
        "message": "Task skipped",
        "task_id": str(task_id),
        "reason": reason,
    }


@router.post("/corrections", response_model=HITLCorrection)
async def submit_correction(
    correction: HITLCorrectionCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Submit a correction for a HITL task.

    This will:
    1. Record the correction
    2. Update the ticket with corrected classification
    3. Update the Neo4j graph with the correction
    4. Mark the task as completed
    """
    # Get the task
    db_task = await HITLTaskRepository.get(str(correction.task_id))
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.status == "completed":
        raise HTTPException(status_code=400, detail="Task already completed")

    # Determine if classification was correct
    is_correct = (
        correction.corrected_level1 == db_task.ai_level1
        and correction.corrected_level2 == db_task.ai_level2
        and correction.corrected_level3 == db_task.ai_level3
    )

    # Create the correction
    db_correction = await HITLCorrectionRepository.create(
        task_id=str(correction.task_id),
        ticket_id=db_task.ticket_id,
        reviewer_id=str(current_user.id),
        original_level1=db_task.ai_level1,
        original_level2=db_task.ai_level2,
        original_level3=db_task.ai_level3,
        original_confidence=db_task.ai_confidence,
        corrected_level1=correction.corrected_level1,
        corrected_level2=correction.corrected_level2,
        corrected_level3=correction.corrected_level3,
        is_correct=is_correct,
        correction_notes=correction.correction_notes,
        confidence_feedback=correction.confidence_feedback,
        review_time_seconds=correction.review_time_seconds,
    )

    # Update the ticket with corrected classification
    await TicketRepository.update(
        db_task.ticket_id,
        level1_category=correction.corrected_level1,
        level2_category=correction.corrected_level2,
        level3_category=correction.corrected_level3,
        status="resolved",
        resolved_at=datetime.utcnow(),
    )

    # Mark task as completed
    await HITLTaskRepository.complete(
        str(correction.task_id),
        completed_by=str(current_user.id),
        review_time_seconds=correction.review_time_seconds,
    )

    # Update user stats
    await UserRepository.increment_reviews(str(current_user.id))

    # Update the Neo4j graph with the correction
    if not is_correct:
        try:
            neo4j = get_neo4j_client()
            await neo4j.record_classification(
                ticket_id=db_task.ticket_id,
                level1=correction.corrected_level1,
                level2=correction.corrected_level2,
                level3=correction.corrected_level3,
                was_corrected=True,
            )
        except Exception as e:
            # Log but don't fail the request
            import structlog

            logger = structlog.get_logger(__name__)
            logger.warning("Failed to update Neo4j graph", error=str(e))

    return db_to_correction(db_correction)


@router.get("/corrections", response_model=CorrectionListResponse)
async def list_corrections(
    reviewer_id: UUID | None = None,
    is_correct: bool | None = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    List corrections with optional filtering.
    """
    reviewer_str = str(reviewer_id) if reviewer_id else None

    db_corrections = await HITLCorrectionRepository.list(
        reviewer_id=reviewer_str,
        is_correct=is_correct,
        limit=limit,
    )

    corrections = [db_to_correction(c) for c in db_corrections]

    return CorrectionListResponse(
        corrections=corrections,
        total=len(corrections),
    )


@router.get("/stats", response_model=HITLStats)
async def get_hitl_stats(
    current_user: User = Depends(get_current_user),
):
    """
    Get HITL system statistics.
    """
    # Get task counts
    task_counts = await HITLTaskRepository.count_by_status()
    pending = task_counts.get("pending", 0)
    in_progress = task_counts.get("in_progress", 0)
    completed = task_counts.get("completed", 0)

    # Get correction stats
    accuracy_rate = await HITLCorrectionRepository.get_accuracy_rate()
    avg_time = await HITLCorrectionRepository.get_avg_review_time()

    return HITLStats(
        total_pending=pending,
        total_in_progress=in_progress,
        total_completed_today=completed,  # Simplified - would need date filtering
        total_completed_week=completed,  # Simplified - would need date filtering
        avg_review_time_seconds=avg_time,
        ai_accuracy_rate=accuracy_rate,
        correction_rate=1.0 - accuracy_rate if accuracy_rate > 0 else 0.0,
        tasks_by_priority={},
        tasks_by_routing_reason={},
        top_correction_categories=[],
        reviewer_leaderboard=[],
    )


@router.post("/tasks", response_model=HITLTask)
async def create_task(
    task_data: HITLTaskCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new HITL task (usually done automatically by the system).
    """
    # Fetch similar tickets from Milvus for reference
    similar_tickets = []
    try:
        milvus = get_milvus_client()
        # Get embeddings for the ticket
        from nexusflow.services.embeddings import EmbeddingService

        embedding_service = EmbeddingService()
        text = f"{task_data.ticket_title} {task_data.ticket_description}"
        embedding = await embedding_service.get_embedding(text)

        results = milvus.search(embedding, limit=5)
        similar_tickets = [
            {
                "ticket_id": r["ticket_id"],
                "category": r.get("metadata", {}).get("category", ""),
                "similarity": r["score"],
            }
            for r in results
        ]
    except Exception:
        pass  # Continue without similar tickets

    db_task = await HITLTaskRepository.create(
        ticket_id=str(task_data.ticket_id),
        ticket_title=task_data.ticket_title,
        ticket_description=task_data.ticket_description,
        ticket_source=task_data.ticket_source,
        ai_level1=task_data.ai_level1,
        ai_level2=task_data.ai_level2,
        ai_level3=task_data.ai_level3,
        ai_confidence=task_data.ai_confidence,
        routing_reason=task_data.routing_reason,
        confidence_details=task_data.confidence_details,
        priority=task_data.priority.value if task_data.priority else "normal",
        similar_tickets=similar_tickets,
    )

    return db_to_task(db_task)
