"""
Classification Routes

Endpoints for ticket classification operations.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nexusflow.models.ticket import TicketCreate, TicketPriority
from nexusflow.services.classification import ClassificationService

router = APIRouter()

# Classification service instance
_service: ClassificationService | None = None


def get_service() -> ClassificationService:
    """Get or create classification service."""
    global _service
    if _service is None:
        _service = ClassificationService()
    return _service


class ClassifyRequest(BaseModel):
    """Request model for classification."""

    title: str = Field(..., min_length=1, description="Ticket title")
    description: str = Field(..., min_length=1, description="Ticket description")
    priority: str = Field(default="medium", description="Priority level")
    source: str | None = None
    customer_id: str | None = None
    metadata: dict[str, Any] | None = None


class ClassifyResponse(BaseModel):
    """Response model for classification."""

    ticket_id: str
    classification: dict[str, Any]
    confidence: dict[str, Any]
    routing: dict[str, Any]
    processing: dict[str, Any]


class SuggestionsResponse(BaseModel):
    """Response model for category suggestions."""

    suggestions: list[dict[str, Any]]
    count: int


class HierarchyResponse(BaseModel):
    """Response model for category hierarchy."""

    hierarchy: dict[str, Any]
    statistics: dict[str, Any]  # Can include int and float values


@router.post("/classify", response_model=ClassifyResponse)
async def classify_ticket(request: ClassifyRequest):
    """
    Classify a single ticket.

    Runs the full classification pipeline:
    1. Graph-based category matching
    2. Vector similarity search
    3. LLM judgment
    4. Ensemble confidence calculation
    5. Routing decision
    """
    service = get_service()

    try:
        priority = TicketPriority(request.priority.lower())
    except ValueError:
        priority = TicketPriority.MEDIUM

    ticket = TicketCreate(
        title=request.title,
        description=request.description,
        priority=priority,
        source=request.source,
        customer_id=request.customer_id,
        metadata=request.metadata or {},
    )

    result = await service.classify_ticket(ticket)

    return ClassifyResponse(
        ticket_id=result["ticket_id"],
        classification=result["classification"],
        confidence=result["confidence"],
        routing=result["routing"],
        processing=result["processing"],
    )


@router.post("/suggest", response_model=SuggestionsResponse)
async def get_suggestions(request: ClassifyRequest):
    """
    Get category suggestions without full classification.

    Faster than full classification, useful for autocomplete.
    """
    service = get_service()

    suggestions = await service.get_category_suggestions(
        title=request.title,
        description=request.description,
    )

    return SuggestionsResponse(
        suggestions=suggestions,
        count=len(suggestions),
    )


@router.post("/similar")
async def find_similar(
    title: str,
    description: str,
    limit: int = 5,
):
    """
    Find similar historical tickets.

    Returns tickets with similar content and their classifications.
    """
    service = get_service()

    matches = await service.get_similar_tickets(
        title=title,
        description=description,
        limit=limit,
    )

    return {
        "matches": matches,
        "count": len(matches),
    }


@router.get("/hierarchy", response_model=HierarchyResponse)
async def get_hierarchy():
    """
    Get the complete classification hierarchy.

    Returns the 3-level category structure with statistics.
    """
    from nexusflow.db.neo4j_client import get_neo4j_client

    neo4j = await get_neo4j_client()

    stats = await neo4j.get_graph_statistics()
    paths = await neo4j.get_all_paths()

    # Organize into hierarchy
    hierarchy = {}
    for path in paths:
        l1, l2, l3 = path["level1"], path["level2"], path["level3"]

        if l1 not in hierarchy:
            hierarchy[l1] = {"subcategories": {}, "ticket_count": 0}
        if l2 not in hierarchy[l1]["subcategories"]:
            hierarchy[l1]["subcategories"][l2] = {"issues": [], "ticket_count": 0}

        hierarchy[l1]["subcategories"][l2]["issues"].append(
            {
                "name": l3,
                "ticket_count": path.get("ticket_count", 0),
                "accuracy": path.get("accuracy", 1.0),
            }
        )
        hierarchy[l1]["subcategories"][l2]["ticket_count"] += path.get("ticket_count", 0)
        hierarchy[l1]["ticket_count"] += path.get("ticket_count", 0)

    return HierarchyResponse(
        hierarchy=hierarchy,
        statistics=stats,
    )


@router.get("/categories")
async def list_categories():
    """
    Get a flat list of all category paths.
    """
    from nexusflow.db.neo4j_client import get_neo4j_client

    neo4j = await get_neo4j_client()
    paths = await neo4j.get_all_paths()

    categories = [
        {
            "path": f"{p['level1']} > {p['level2']} > {p['level3']}",
            "level1": p["level1"],
            "level2": p["level2"],
            "level3": p["level3"],
            "ticket_count": p.get("ticket_count", 0),
        }
        for p in paths
    ]

    return {"categories": categories, "count": len(categories)}


@router.get("/categories/{level1}")
async def get_subcategories(level1: str):
    """
    Get subcategories for a Level 1 category.
    """
    from nexusflow.db.neo4j_client import get_neo4j_client

    neo4j = await get_neo4j_client()
    paths = await neo4j.traverse_from_level1(level1)

    if not paths:
        raise HTTPException(status_code=404, detail=f"Category '{level1}' not found")

    # Group by level2
    subcategories = {}
    for path in paths:
        l2 = path["level2"]
        if l2 not in subcategories:
            subcategories[l2] = {"issues": [], "ticket_count": 0}
        subcategories[l2]["issues"].append(path["level3"])
        subcategories[l2]["ticket_count"] += path.get("ticket_count", 0)

    return {
        "level1": level1,
        "subcategories": subcategories,
    }
