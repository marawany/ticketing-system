"""
Database Repository

CRUD operations for persistent storage.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import structlog
from sqlalchemy import and_, desc, func, select, update

from nexusflow.db.models import (
    ClassificationMetricsDB,
    HITLCorrectionDB,
    HITLTaskDB,
    TicketDB,
    UserDB,
)
from nexusflow.db.session import get_session

logger = structlog.get_logger(__name__)


# ============================================================================
# Ticket Repository
# ============================================================================


class TicketRepository:
    """Repository for ticket operations."""

    @staticmethod
    async def create(
        title: str,
        description: str,
        priority: str = "medium",
        source: str | None = None,
        customer_id: str | None = None,
        metadata: dict | None = None,
        ticket_id: str | None = None,
    ) -> TicketDB:
        """Create a new ticket."""
        async with get_session() as session:
            ticket = TicketDB(
                id=ticket_id or str(uuid4()),
                title=title,
                description=description,
                priority=priority,
                source=source,
                customer_id=customer_id,
                extra_data=metadata or {},
            )
            session.add(ticket)
            await session.flush()
            await session.refresh(ticket)
            return ticket

    @staticmethod
    async def get(ticket_id: str) -> TicketDB | None:
        """Get a ticket by ID."""
        async with get_session() as session:
            result = await session.execute(select(TicketDB).where(TicketDB.id == ticket_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def update(ticket_id: str, **kwargs) -> TicketDB | None:
        """Update a ticket."""
        async with get_session() as session:
            result = await session.execute(select(TicketDB).where(TicketDB.id == ticket_id))
            ticket = result.scalar_one_or_none()
            if ticket:
                for key, value in kwargs.items():
                    if hasattr(ticket, key):
                        setattr(ticket, key, value)
                ticket.updated_at = datetime.utcnow()
                await session.flush()
                await session.refresh(ticket)
            return ticket

    @staticmethod
    async def delete(ticket_id: str) -> bool:
        """Delete a ticket."""
        async with get_session() as session:
            result = await session.execute(select(TicketDB).where(TicketDB.id == ticket_id))
            ticket = result.scalar_one_or_none()
            if ticket:
                await session.delete(ticket)
                return True
            return False

    @staticmethod
    async def list(
        status: str | None = None,
        priority: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TicketDB], int]:
        """List tickets with optional filters."""
        async with get_session() as session:
            query = select(TicketDB)
            count_query = select(func.count(TicketDB.id))

            if status:
                query = query.where(TicketDB.status == status)
                count_query = count_query.where(TicketDB.status == status)
            if priority:
                query = query.where(TicketDB.priority == priority)
                count_query = count_query.where(TicketDB.priority == priority)

            # Get total count
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            # Get paginated results
            query = query.order_by(desc(TicketDB.created_at))
            query = query.offset((page - 1) * page_size).limit(page_size)

            result = await session.execute(query)
            tickets = list(result.scalars().all())

            return tickets, total

    @staticmethod
    async def update_classification(
        ticket_id: str,
        level1: str,
        level2: str,
        level3: str,
        confidence: float,
        processing_time_ms: int,
    ) -> TicketDB | None:
        """Update ticket with classification results."""
        return await TicketRepository.update(
            ticket_id,
            level1_category=level1,
            level2_category=level2,
            level3_category=level3,
            classification_confidence=confidence,
            status="classified",
            classified_at=datetime.utcnow(),
            processing_time_ms=processing_time_ms,
        )

    @staticmethod
    async def count_by_status() -> dict[str, int]:
        """Get ticket counts by status."""
        async with get_session() as session:
            result = await session.execute(
                select(TicketDB.status, func.count(TicketDB.id)).group_by(TicketDB.status)
            )
            return {row[0]: row[1] for row in result.all()}

    @staticmethod
    async def count_today() -> int:
        """Get count of tickets created today."""
        async with get_session() as session:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            result = await session.execute(
                select(func.count(TicketDB.id)).where(TicketDB.created_at >= today)
            )
            return result.scalar() or 0


# ============================================================================
# User Repository
# ============================================================================


class UserRepository:
    """Repository for user operations."""

    @staticmethod
    async def create(
        email: str,
        full_name: str,
        hashed_password: str,
        role: str = "viewer",
        department: str | None = None,
        teams: list[str] | None = None,
    ) -> UserDB:
        """Create a new user."""
        async with get_session() as session:
            user = UserDB(
                id=str(uuid4()),
                email=email,
                full_name=full_name,
                hashed_password=hashed_password,
                role=role,
                department=department,
                teams=teams or [],
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            return user

    @staticmethod
    async def get(user_id: str) -> UserDB | None:
        """Get a user by ID."""
        async with get_session() as session:
            result = await session.execute(select(UserDB).where(UserDB.id == user_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(email: str) -> UserDB | None:
        """Get a user by email."""
        async with get_session() as session:
            result = await session.execute(select(UserDB).where(UserDB.email == email))
            return result.scalar_one_or_none()

    @staticmethod
    async def update(user_id: str, **kwargs) -> UserDB | None:
        """Update a user."""
        async with get_session() as session:
            result = await session.execute(select(UserDB).where(UserDB.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                user.updated_at = datetime.utcnow()
                await session.flush()
                await session.refresh(user)
            return user

    @staticmethod
    async def delete(user_id: str) -> bool:
        """Delete a user."""
        async with get_session() as session:
            result = await session.execute(select(UserDB).where(UserDB.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                await session.delete(user)
                return True
            return False

    @staticmethod
    async def list() -> list[UserDB]:
        """List all users."""
        async with get_session() as session:
            result = await session.execute(select(UserDB).order_by(UserDB.created_at))
            return list(result.scalars().all())

    @staticmethod
    async def update_login(user_id: str) -> None:
        """Update last login timestamp."""
        await UserRepository.update(user_id, last_login=datetime.utcnow())

    @staticmethod
    async def increment_reviews(user_id: str) -> None:
        """Increment review count for user."""
        async with get_session() as session:
            await session.execute(
                update(UserDB)
                .where(UserDB.id == user_id)
                .values(tickets_reviewed=UserDB.tickets_reviewed + 1)
            )

    @staticmethod
    async def ensure_admin_exists(hashed_password: str) -> UserDB:
        """Ensure an admin user exists."""
        admin = await UserRepository.get_by_email("marawan.y@turing.com")
        if not admin:
            admin = await UserRepository.create(
                email="marawan.y@turing.com",
                full_name="Marawan Youssef",
                hashed_password=hashed_password,
                role="admin",
            )
            logger.info("Created default admin user: marawan.y@turing.com")
        return admin


# ============================================================================
# HITL Task Repository
# ============================================================================


class HITLTaskRepository:
    """Repository for HITL task operations."""

    @staticmethod
    async def create(
        ticket_id: str,
        ticket_title: str,
        ticket_description: str,
        ai_level1: str,
        ai_level2: str,
        ai_level3: str,
        ai_confidence: float,
        routing_reason: str,
        confidence_details: dict | None = None,
        ticket_source: str | None = None,
        priority: str = "normal",
        similar_tickets: list | None = None,
    ) -> HITLTaskDB:
        """Create a new HITL task."""
        async with get_session() as session:
            task = HITLTaskDB(
                id=str(uuid4()),
                ticket_id=ticket_id,
                ticket_title=ticket_title,
                ticket_description=ticket_description,
                ticket_source=ticket_source,
                ai_level1=ai_level1,
                ai_level2=ai_level2,
                ai_level3=ai_level3,
                ai_confidence=ai_confidence,
                routing_reason=routing_reason,
                confidence_details=confidence_details or {},
                priority=priority,
                similar_tickets=similar_tickets or [],
            )
            session.add(task)
            await session.flush()
            await session.refresh(task)
            return task

    @staticmethod
    async def get(task_id: str) -> HITLTaskDB | None:
        """Get a task by ID."""
        async with get_session() as session:
            result = await session.execute(select(HITLTaskDB).where(HITLTaskDB.id == task_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def update(task_id: str, **kwargs) -> HITLTaskDB | None:
        """Update a task."""
        async with get_session() as session:
            result = await session.execute(select(HITLTaskDB).where(HITLTaskDB.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                await session.flush()
                await session.refresh(task)
            return task

    @staticmethod
    async def list(
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        unassigned_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[HITLTaskDB], int]:
        """List tasks with optional filters."""
        async with get_session() as session:
            query = select(HITLTaskDB)
            count_query = select(func.count(HITLTaskDB.id))

            conditions = []
            if status:
                conditions.append(HITLTaskDB.status == status)
            if priority:
                conditions.append(HITLTaskDB.priority == priority)
            if assigned_to:
                conditions.append(HITLTaskDB.assigned_to == assigned_to)
            if unassigned_only:
                conditions.append(HITLTaskDB.assigned_to.is_(None))

            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))

            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            query = query.order_by(HITLTaskDB.priority, HITLTaskDB.created_at)
            query = query.offset((page - 1) * page_size).limit(page_size)

            result = await session.execute(query)
            tasks = list(result.scalars().all())

            return tasks, total

    @staticmethod
    async def assign(task_id: str, user_id: str) -> HITLTaskDB | None:
        """Assign a task to a user."""
        return await HITLTaskRepository.update(
            task_id,
            assigned_to=user_id,
            assigned_at=datetime.utcnow(),
            status="in_progress",
        )

    @staticmethod
    async def complete(
        task_id: str,
        completed_by: str,
        review_time_seconds: int,
    ) -> HITLTaskDB | None:
        """Mark a task as completed."""
        return await HITLTaskRepository.update(
            task_id,
            status="completed",
            completed_by=completed_by,
            completed_at=datetime.utcnow(),
            review_time_seconds=review_time_seconds,
        )

    @staticmethod
    async def count_by_status() -> dict[str, int]:
        """Get task counts by status."""
        async with get_session() as session:
            result = await session.execute(
                select(HITLTaskDB.status, func.count(HITLTaskDB.id)).group_by(HITLTaskDB.status)
            )
            return {row[0]: row[1] for row in result.all()}

    @staticmethod
    async def count_pending() -> int:
        """Get count of pending tasks."""
        async with get_session() as session:
            result = await session.execute(
                select(func.count(HITLTaskDB.id)).where(
                    HITLTaskDB.status.in_(["pending", "in_progress"])
                )
            )
            return result.scalar() or 0


# ============================================================================
# HITL Correction Repository
# ============================================================================


class HITLCorrectionRepository:
    """Repository for HITL correction operations."""

    @staticmethod
    async def create(
        task_id: str,
        ticket_id: str,
        reviewer_id: str,
        original_level1: str,
        original_level2: str,
        original_level3: str,
        original_confidence: float,
        corrected_level1: str,
        corrected_level2: str,
        corrected_level3: str,
        is_correct: bool,
        review_time_seconds: int,
        correction_notes: str | None = None,
        confidence_feedback: str | None = None,
    ) -> HITLCorrectionDB:
        """Create a new correction."""
        async with get_session() as session:
            correction = HITLCorrectionDB(
                id=str(uuid4()),
                task_id=task_id,
                ticket_id=ticket_id,
                reviewer_id=reviewer_id,
                original_level1=original_level1,
                original_level2=original_level2,
                original_level3=original_level3,
                original_confidence=original_confidence,
                corrected_level1=corrected_level1,
                corrected_level2=corrected_level2,
                corrected_level3=corrected_level3,
                is_correct=is_correct,
                correction_notes=correction_notes,
                confidence_feedback=confidence_feedback,
                review_time_seconds=review_time_seconds,
            )
            session.add(correction)
            await session.flush()
            await session.refresh(correction)
            return correction

    @staticmethod
    async def list(
        reviewer_id: str | None = None,
        is_correct: bool | None = None,
        limit: int = 50,
    ) -> list[HITLCorrectionDB]:
        """List corrections with optional filters."""
        async with get_session() as session:
            query = select(HITLCorrectionDB)

            if reviewer_id:
                query = query.where(HITLCorrectionDB.reviewer_id == reviewer_id)
            if is_correct is not None:
                query = query.where(HITLCorrectionDB.is_correct == is_correct)

            query = query.order_by(desc(HITLCorrectionDB.submitted_at)).limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def get_accuracy_rate() -> float:
        """Get the AI accuracy rate based on corrections."""
        async with get_session() as session:
            total_result = await session.execute(select(func.count(HITLCorrectionDB.id)))
            total = total_result.scalar() or 0

            if total == 0:
                return 1.0

            correct_result = await session.execute(
                select(func.count(HITLCorrectionDB.id)).where(HITLCorrectionDB.is_correct)
            )
            correct = correct_result.scalar() or 0

            return correct / total

    @staticmethod
    async def get_avg_review_time() -> float:
        """Get average review time in seconds."""
        async with get_session() as session:
            result = await session.execute(select(func.avg(HITLCorrectionDB.review_time_seconds)))
            return result.scalar() or 0.0


# ============================================================================
# Classification Metrics Repository
# ============================================================================


class MetricsRepository:
    """Repository for classification metrics."""

    @staticmethod
    async def record(
        ticket_id: str,
        level1: str,
        level2: str,
        level3: str,
        graph_confidence: float,
        vector_confidence: float,
        llm_confidence: float,
        final_confidence: float,
        component_agreement: float,
        auto_resolved: bool,
        requires_hitl: bool,
        processing_time_ms: int,
    ) -> ClassificationMetricsDB:
        """Record classification metrics."""
        async with get_session() as session:
            metric = ClassificationMetricsDB(
                ticket_id=ticket_id,
                level1=level1,
                level2=level2,
                level3=level3,
                graph_confidence=graph_confidence,
                vector_confidence=vector_confidence,
                llm_confidence=llm_confidence,
                final_confidence=final_confidence,
                component_agreement=component_agreement,
                auto_resolved=auto_resolved,
                requires_hitl=requires_hitl,
                processing_time_ms=processing_time_ms,
            )
            session.add(metric)
            await session.flush()
            await session.refresh(metric)
            return metric

    @staticmethod
    async def get_stats(days: int = 30) -> dict[str, Any]:
        """Get aggregated metrics for the last N days."""
        async with get_session() as session:
            since = datetime.utcnow() - timedelta(days=days)

            # Total count
            total_result = await session.execute(
                select(func.count(ClassificationMetricsDB.id)).where(
                    ClassificationMetricsDB.timestamp >= since
                )
            )
            total = total_result.scalar() or 0

            # Auto-resolved count
            auto_result = await session.execute(
                select(func.count(ClassificationMetricsDB.id)).where(
                    and_(
                        ClassificationMetricsDB.timestamp >= since,
                        ClassificationMetricsDB.auto_resolved,
                    )
                )
            )
            auto_resolved = auto_result.scalar() or 0

            # Average confidence
            avg_conf_result = await session.execute(
                select(func.avg(ClassificationMetricsDB.final_confidence)).where(
                    ClassificationMetricsDB.timestamp >= since
                )
            )
            avg_confidence = avg_conf_result.scalar() or 0.0

            # Average processing time
            avg_time_result = await session.execute(
                select(func.avg(ClassificationMetricsDB.processing_time_ms)).where(
                    ClassificationMetricsDB.timestamp >= since
                )
            )
            avg_time = avg_time_result.scalar() or 0

            return {
                "total": total,
                "auto_resolved": auto_resolved,
                "auto_resolved_rate": auto_resolved / total if total > 0 else 0,
                "avg_confidence": avg_confidence,
                "avg_processing_time_ms": int(avg_time),
            }

    @staticmethod
    async def get_confidence_distribution() -> list[dict[str, Any]]:
        """Get confidence score distribution."""
        async with get_session() as session:
            # Group by confidence ranges
            ranges = [
                (0.0, 0.5, "0.0-0.5"),
                (0.5, 0.6, "0.5-0.6"),
                (0.6, 0.7, "0.6-0.7"),
                (0.7, 0.8, "0.7-0.8"),
                (0.8, 0.9, "0.8-0.9"),
                (0.9, 1.01, "0.9-1.0"),
            ]

            distribution = []
            for low, high, label in ranges:
                result = await session.execute(
                    select(func.count(ClassificationMetricsDB.id)).where(
                        and_(
                            ClassificationMetricsDB.final_confidence >= low,
                            ClassificationMetricsDB.final_confidence < high,
                        )
                    )
                )
                count = result.scalar() or 0
                distribution.append({"range": label, "count": count})

            return distribution
