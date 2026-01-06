"""
Graph Management API Routes

Provides CRUD operations for the classification graph and AI-powered evolution.
"""

import json
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from nexusflow.api.routes.users import get_current_user
from nexusflow.db.neo4j_client import get_neo4j_client
from nexusflow.models.user import User
from nexusflow.services.graph_evolution import GraphEvolutionService, get_graph_evolution_service

logger = structlog.get_logger(__name__)

router = APIRouter()


# =============================================================================
# Models
# =============================================================================


class CategoryBase(BaseModel):
    """Base model for category."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    keywords: list[str] = Field(default_factory=list)


class Level1Create(CategoryBase):
    """Create a Level 1 category."""
    pass


class Level2Create(CategoryBase):
    """Create a Level 2 category."""
    parent_level1: str = Field(..., description="Parent Level 1 category name")


class Level3Create(CategoryBase):
    """Create a Level 3 category."""
    parent_level1: str = Field(..., description="Parent Level 1 category name")
    parent_level2: str = Field(..., description="Parent Level 2 category name")


class CategoryUpdate(BaseModel):
    """Update a category."""
    name: str | None = None
    description: str | None = None
    keywords: list[str] | None = None


class CategoryResponse(BaseModel):
    """Category response."""
    name: str
    level: int
    description: str | None = None
    keywords: list[str] = []
    ticket_count: int = 0
    accuracy: float = 1.0
    children_count: int = 0
    parent: str | None = None


class GraphStats(BaseModel):
    """Graph statistics."""
    level1_count: int
    level2_count: int
    level3_count: int
    total_tickets: int
    total_edges: int
    avg_accuracy: float


class AIExpansionRequest(BaseModel):
    """Request for AI-powered node expansion."""
    category_name: str
    level: int = Field(..., ge=1, le=3)
    context: str | None = Field(None, description="Additional context for expansion")
    num_suggestions: int = Field(default=5, ge=1, le=20)


class AIExpansionResponse(BaseModel):
    """Response from AI expansion."""
    suggestions: list[dict[str, Any]]
    reasoning: str
    category_analyzed: str


class DatasetAnalysisRequest(BaseModel):
    """Request for dataset analysis."""
    sample_size: int = Field(default=100, ge=10, le=1000)


class DatasetAnalysisResponse(BaseModel):
    """Response from dataset analysis."""
    new_categories_suggested: list[dict[str, Any]]
    existing_categories_expanded: list[dict[str, Any]]
    coverage_analysis: dict[str, Any]
    recommendations: list[str]


class HITLFeedbackEvolution(BaseModel):
    """HITL feedback for graph evolution."""
    correction_id: str
    original_path: list[str]
    corrected_path: list[str]
    ticket_content: str
    user_notes: str | None = None


# =============================================================================
# CRUD Operations
# =============================================================================


@router.get("/stats", response_model=GraphStats)
async def get_graph_stats(
    current_user: User = Depends(get_current_user),
):
    """Get graph statistics."""
    neo4j = await get_neo4j_client()
    stats = await neo4j.get_graph_statistics()
    
    # Get edge count and avg accuracy
    async with neo4j.session() as session:
        edge_result = await session.run(
            "MATCH ()-[r:CONTAINS]->() RETURN count(r) AS edges"
        )
        edge_record = await edge_result.single()
        
        acc_result = await session.run(
            "MATCH (n) WHERE n:Level1Category OR n:Level2Category OR n:Level3Category "
            "RETURN avg(n.accuracy) AS avg_acc"
        )
        acc_record = await acc_result.single()
    
    return GraphStats(
        level1_count=stats["level1_categories"],
        level2_count=stats["level2_categories"],
        level3_count=stats["level3_categories"],
        total_tickets=stats["total_tickets"],
        total_edges=edge_record["edges"] if edge_record else 0,
        avg_accuracy=acc_record["avg_acc"] if acc_record and acc_record["avg_acc"] else 1.0,
    )


@router.get("/categories")
async def list_categories(
    level: int | None = Query(None, ge=1, le=3),
    parent: str | None = Query(None, description="Filter by parent category"),
    search: str | None = Query(None, description="Search by name"),
    current_user: User = Depends(get_current_user),
):
    """List categories with optional filtering."""
    neo4j = await get_neo4j_client()
    
    async with neo4j.session() as session:
        if level == 1:
            query = """
            MATCH (c:Level1Category)
            WHERE $search IS NULL OR toLower(c.name) CONTAINS toLower($search)
            OPTIONAL MATCH (c)-[:CONTAINS]->(child)
            RETURN c.name AS name, 'Level1Category' AS label, 
                   c.description AS description, c.ticket_count AS ticket_count,
                   c.accuracy AS accuracy, count(child) AS children_count,
                   null AS parent
            ORDER BY c.name
            """
        elif level == 2:
            query = """
            MATCH (p:Level1Category)-[:CONTAINS]->(c:Level2Category)
            WHERE ($search IS NULL OR toLower(c.name) CONTAINS toLower($search))
              AND ($parent IS NULL OR p.name = $parent)
            OPTIONAL MATCH (c)-[:CONTAINS]->(child)
            RETURN c.name AS name, 'Level2Category' AS label,
                   c.description AS description, c.ticket_count AS ticket_count,
                   c.accuracy AS accuracy, count(child) AS children_count,
                   p.name AS parent
            ORDER BY p.name, c.name
            """
        elif level == 3:
            query = """
            MATCH (gp:Level1Category)-[:CONTAINS]->(p:Level2Category)-[:CONTAINS]->(c:Level3Category)
            WHERE ($search IS NULL OR toLower(c.name) CONTAINS toLower($search))
              AND ($parent IS NULL OR p.name = $parent OR gp.name = $parent)
            RETURN c.name AS name, 'Level3Category' AS label,
                   c.description AS description, c.ticket_count AS ticket_count,
                   c.accuracy AS accuracy, 0 AS children_count,
                   p.name AS parent
            ORDER BY gp.name, p.name, c.name
            """
        else:
            # All levels
            query = """
            MATCH (c)
            WHERE (c:Level1Category OR c:Level2Category OR c:Level3Category)
              AND ($search IS NULL OR toLower(c.name) CONTAINS toLower($search))
            OPTIONAL MATCH (c)-[:CONTAINS]->(child)
            OPTIONAL MATCH (parent)-[:CONTAINS]->(c)
            RETURN c.name AS name, labels(c)[0] AS label,
                   c.description AS description, c.ticket_count AS ticket_count,
                   c.accuracy AS accuracy, count(child) AS children_count,
                   parent.name AS parent
            ORDER BY c.name
            """
        
        result = await session.run(query, search=search, parent=parent)
        categories = []
        async for record in result:
            level_num = {"Level1Category": 1, "Level2Category": 2, "Level3Category": 3}.get(
                record["label"], 0
            )
            categories.append(
                CategoryResponse(
                    name=record["name"],
                    level=level_num,
                    description=record["description"],
                    ticket_count=record["ticket_count"] or 0,
                    accuracy=record["accuracy"] or 1.0,
                    children_count=record["children_count"] or 0,
                    parent=record["parent"],
                )
            )
    
    return {"categories": categories, "total": len(categories)}


@router.post("/categories/level1", response_model=CategoryResponse)
async def create_level1_category(
    data: Level1Create,
    current_user: User = Depends(get_current_user),
):
    """Create a new Level 1 category."""
    neo4j = await get_neo4j_client()
    
    async with neo4j.session() as session:
        # Check if exists
        check = await session.run(
            "MATCH (c:Level1Category {name: $name}) RETURN c",
            name=data.name,
        )
        if await check.single():
            raise HTTPException(status_code=400, detail="Category already exists")
        
        # Create
        await session.run(
            """
            CREATE (c:Level1Category {
                name: $name,
                description: $description,
                keywords: $keywords,
                ticket_count: 0,
                accuracy: 1.0,
                created_at: datetime(),
                created_by: $user_id
            })
            """,
            name=data.name,
            description=data.description or "",
            keywords=data.keywords,
            user_id=str(current_user.id),
        )
    
    logger.info("Created Level1 category", name=data.name, user=current_user.email)
    
    return CategoryResponse(
        name=data.name,
        level=1,
        description=data.description,
        keywords=data.keywords,
        ticket_count=0,
        accuracy=1.0,
        children_count=0,
    )


@router.post("/categories/level2", response_model=CategoryResponse)
async def create_level2_category(
    data: Level2Create,
    current_user: User = Depends(get_current_user),
):
    """Create a new Level 2 category."""
    neo4j = await get_neo4j_client()
    
    async with neo4j.session() as session:
        # Check parent exists
        parent_check = await session.run(
            "MATCH (p:Level1Category {name: $parent}) RETURN p",
            parent=data.parent_level1,
        )
        if not await parent_check.single():
            raise HTTPException(status_code=404, detail=f"Parent category '{data.parent_level1}' not found")
        
        # Check if exists
        check = await session.run(
            "MATCH (c:Level2Category {name: $name}) RETURN c",
            name=data.name,
        )
        if await check.single():
            raise HTTPException(status_code=400, detail="Category already exists")
        
        # Create with relationship
        await session.run(
            """
            MATCH (p:Level1Category {name: $parent})
            CREATE (c:Level2Category {
                name: $name,
                description: $description,
                keywords: $keywords,
                ticket_count: 0,
                accuracy: 1.0,
                created_at: datetime(),
                created_by: $user_id
            })
            CREATE (p)-[:CONTAINS {weight: 1.0, traversal_count: 0}]->(c)
            """,
            parent=data.parent_level1,
            name=data.name,
            description=data.description or "",
            keywords=data.keywords,
            user_id=str(current_user.id),
        )
    
    logger.info("Created Level2 category", name=data.name, parent=data.parent_level1)
    
    return CategoryResponse(
        name=data.name,
        level=2,
        description=data.description,
        keywords=data.keywords,
        ticket_count=0,
        accuracy=1.0,
        children_count=0,
        parent=data.parent_level1,
    )


@router.post("/categories/level3", response_model=CategoryResponse)
async def create_level3_category(
    data: Level3Create,
    current_user: User = Depends(get_current_user),
):
    """Create a new Level 3 category."""
    neo4j = await get_neo4j_client()
    
    async with neo4j.session() as session:
        # Check parent path exists
        parent_check = await session.run(
            """
            MATCH (l1:Level1Category {name: $l1})-[:CONTAINS]->(l2:Level2Category {name: $l2})
            RETURN l2
            """,
            l1=data.parent_level1,
            l2=data.parent_level2,
        )
        if not await parent_check.single():
            raise HTTPException(
                status_code=404,
                detail=f"Parent path '{data.parent_level1} > {data.parent_level2}' not found",
            )
        
        # Create with relationship
        await session.run(
            """
            MATCH (p:Level2Category {name: $parent})
            CREATE (c:Level3Category {
                name: $name,
                description: $description,
                keywords: $keywords,
                ticket_count: 0,
                accuracy: 1.0,
                created_at: datetime(),
                created_by: $user_id
            })
            CREATE (p)-[:CONTAINS {weight: 1.0, traversal_count: 0}]->(c)
            """,
            parent=data.parent_level2,
            name=data.name,
            description=data.description or "",
            keywords=data.keywords,
            user_id=str(current_user.id),
        )
    
    logger.info("Created Level3 category", name=data.name, parent=data.parent_level2)
    
    return CategoryResponse(
        name=data.name,
        level=3,
        description=data.description,
        keywords=data.keywords,
        ticket_count=0,
        accuracy=1.0,
        children_count=0,
        parent=data.parent_level2,
    )


@router.put("/categories/{level}/{name}", response_model=CategoryResponse)
async def update_category(
    level: int,
    name: str,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a category."""
    level_label = {1: "Level1Category", 2: "Level2Category", 3: "Level3Category"}.get(level)
    if not level_label:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    neo4j = await get_neo4j_client()
    
    async with neo4j.session() as session:
        # Build update query
        updates = []
        params = {"name": name}
        
        if data.name is not None:
            updates.append("c.name = $new_name")
            params["new_name"] = data.name
        if data.description is not None:
            updates.append("c.description = $description")
            params["description"] = data.description
        if data.keywords is not None:
            updates.append("c.keywords = $keywords")
            params["keywords"] = data.keywords
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        updates.append("c.updated_at = datetime()")
        updates.append("c.updated_by = $user_id")
        params["user_id"] = str(current_user.id)
        
        query = f"""
        MATCH (c:{level_label} {{name: $name}})
        SET {', '.join(updates)}
        RETURN c.name AS name, c.description AS description, c.keywords AS keywords,
               c.ticket_count AS ticket_count, c.accuracy AS accuracy
        """
        
        result = await session.run(query, **params)
        record = await result.single()
        
        if not record:
            raise HTTPException(status_code=404, detail="Category not found")
    
    return CategoryResponse(
        name=record["name"],
        level=level,
        description=record["description"],
        keywords=record["keywords"] or [],
        ticket_count=record["ticket_count"] or 0,
        accuracy=record["accuracy"] or 1.0,
        children_count=0,
    )


@router.delete("/categories/{level}/{name}")
async def delete_category(
    level: int,
    name: str,
    cascade: bool = Query(False, description="Delete children too"),
    current_user: User = Depends(get_current_user),
):
    """Delete a category."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    level_label = {1: "Level1Category", 2: "Level2Category", 3: "Level3Category"}.get(level)
    if not level_label:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    neo4j = await get_neo4j_client()
    
    async with neo4j.session() as session:
        # Check for children
        if level < 3 and not cascade:
            child_check = await session.run(
                f"MATCH (c:{level_label} {{name: $name}})-[:CONTAINS]->(child) RETURN count(child) AS cnt",
                name=name,
            )
            record = await child_check.single()
            if record and record["cnt"] > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Category has {record['cnt']} children. Use cascade=true to delete.",
                )
        
        # Delete
        if cascade and level < 3:
            if level == 1:
                await session.run(
                    """
                    MATCH (c:Level1Category {name: $name})
                    OPTIONAL MATCH (c)-[:CONTAINS]->(l2)-[:CONTAINS]->(l3)
                    DETACH DELETE c, l2, l3
                    """,
                    name=name,
                )
            else:
                await session.run(
                    """
                    MATCH (c:Level2Category {name: $name})
                    OPTIONAL MATCH (c)-[:CONTAINS]->(l3)
                    DETACH DELETE c, l3
                    """,
                    name=name,
                )
        else:
            await session.run(
                f"MATCH (c:{level_label} {{name: $name}}) DETACH DELETE c",
                name=name,
            )
    
    logger.info("Deleted category", level=level, name=name, cascade=cascade, user=current_user.email)
    
    return {"status": "deleted", "name": name, "level": level}


# =============================================================================
# AI-Powered Evolution
# =============================================================================


@router.post("/ai/expand", response_model=AIExpansionResponse)
async def ai_expand_category(
    data: AIExpansionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Use AI to suggest new subcategories for expansion.
    
    The AI analyzes the category and suggests relevant subcategories
    based on common ticket patterns and industry standards.
    """
    service = await get_graph_evolution_service()
    
    result = await service.suggest_expansion(
        category_name=data.category_name,
        level=data.level,
        context=data.context,
        num_suggestions=data.num_suggestions,
    )
    
    return AIExpansionResponse(
        suggestions=result["suggestions"],
        reasoning=result["reasoning"],
        category_analyzed=data.category_name,
    )


@router.post("/ai/expand/apply")
async def apply_ai_expansion(
    category_name: str,
    level: int,
    suggestions: list[dict[str, Any]],
    current_user: User = Depends(get_current_user),
):
    """
    Apply AI-suggested expansions to the graph.
    
    Takes the suggestions from /ai/expand and creates the nodes.
    """
    if current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    service = await get_graph_evolution_service()
    
    results = await service.apply_expansion(
        category_name=category_name,
        level=level,
        suggestions=suggestions,
        user_id=str(current_user.id),
    )
    
    return {
        "applied": results["applied"],
        "skipped": results["skipped"],
        "errors": results["errors"],
    }


@router.post("/ai/analyze-dataset", response_model=DatasetAnalysisResponse)
async def analyze_dataset_for_evolution(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze an uploaded dataset to suggest graph evolution.
    
    The AI examines ticket titles/descriptions to identify:
    - New categories that should be added
    - Existing categories that need expansion
    - Coverage gaps in the current graph
    """
    if not file.filename.endswith((".json", ".csv")):
        raise HTTPException(status_code=400, detail="Only JSON and CSV files supported")
    
    content = await file.read()
    
    try:
        if file.filename.endswith(".json"):
            data = json.loads(content.decode())
        else:
            # CSV parsing
            import csv
            from io import StringIO
            reader = csv.DictReader(StringIO(content.decode()))
            data = list(reader)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
    
    service = await get_graph_evolution_service()
    
    result = await service.analyze_dataset_for_evolution(
        tickets=data,
        sample_size=min(100, len(data)),
    )
    
    return DatasetAnalysisResponse(
        new_categories_suggested=result["new_categories"],
        existing_categories_expanded=result["expanded_categories"],
        coverage_analysis=result["coverage"],
        recommendations=result["recommendations"],
    )


@router.post("/ai/evolve-from-hitl")
async def evolve_from_hitl_feedback(
    data: HITLFeedbackEvolution,
    current_user: User = Depends(get_current_user),
):
    """
    Use LLM to analyze HITL corrections and evolve the graph.
    
    When humans correct classifications, this endpoint:
    1. Analyzes why the correction was made
    2. Suggests graph modifications to prevent future errors
    3. Optionally creates new categories or adjusts relationships
    """
    service = await get_graph_evolution_service()
    
    result = await service.evolve_from_correction(
        original_path=data.original_path,
        corrected_path=data.corrected_path,
        ticket_content=data.ticket_content,
        user_notes=data.user_notes,
    )
    
    return {
        "analysis": result["analysis"],
        "suggestions": result["suggestions"],
        "applied_changes": result["applied_changes"],
        "graph_updated": result["graph_updated"],
    }


# =============================================================================
# Graph Visualization Data
# =============================================================================


@router.get("/visualization")
async def get_graph_visualization(
    current_user: User = Depends(get_current_user),
):
    """Get graph data formatted for visualization."""
    neo4j = await get_neo4j_client()
    
    nodes = []
    edges = []
    
    async with neo4j.session() as session:
        # Get all nodes
        node_query = """
        MATCH (n)
        WHERE n:Level1Category OR n:Level2Category OR n:Level3Category
        RETURN id(n) AS id, labels(n)[0] AS label, n.name AS name,
               n.ticket_count AS ticket_count, n.accuracy AS accuracy,
               n.description AS description
        """
        result = await session.run(node_query)
        async for record in result:
            level = {"Level1Category": 1, "Level2Category": 2, "Level3Category": 3}.get(
                record["label"], 0
            )
            nodes.append({
                "id": str(record["id"]),
                "name": record["name"],
                "level": level,
                "type": record["label"],
                "ticket_count": record["ticket_count"] or 0,
                "accuracy": record["accuracy"] or 1.0,
                "description": record["description"],
            })
        
        # Get all edges
        edge_query = """
        MATCH (from)-[r:CONTAINS]->(to)
        RETURN id(from) AS source, id(to) AS target,
               r.weight AS weight, r.traversal_count AS traversal_count
        """
        result = await session.run(edge_query)
        async for record in result:
            edges.append({
                "source": str(record["source"]),
                "target": str(record["target"]),
                "weight": record["weight"] or 1.0,
                "traversal_count": record["traversal_count"] or 0,
            })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }


@router.get("/hierarchy")
async def get_hierarchy(
    current_user: User = Depends(get_current_user),
):
    """Get full hierarchy as nested structure."""
    neo4j = await get_neo4j_client()
    
    hierarchy = {}
    
    async with neo4j.session() as session:
        query = """
        MATCH (l1:Level1Category)-[:CONTAINS]->(l2:Level2Category)-[:CONTAINS]->(l3:Level3Category)
        RETURN l1.name AS level1, l2.name AS level2, l3.name AS level3,
               l1.ticket_count AS l1_count, l2.ticket_count AS l2_count, l3.ticket_count AS l3_count,
               l3.accuracy AS accuracy
        ORDER BY l1.name, l2.name, l3.name
        """
        result = await session.run(query)
        
        async for record in result:
            l1 = record["level1"]
            l2 = record["level2"]
            l3 = record["level3"]
            
            if l1 not in hierarchy:
                hierarchy[l1] = {"name": l1, "ticket_count": record["l1_count"] or 0, "children": {}}
            if l2 not in hierarchy[l1]["children"]:
                hierarchy[l1]["children"][l2] = {
                    "name": l2,
                    "ticket_count": record["l2_count"] or 0,
                    "children": [],
                }
            hierarchy[l1]["children"][l2]["children"].append({
                "name": l3,
                "ticket_count": record["l3_count"] or 0,
                "accuracy": record["accuracy"] or 1.0,
            })
    
    # Convert to list format
    result = []
    for l1_data in hierarchy.values():
        l1_data["children"] = list(l1_data["children"].values())
        result.append(l1_data)
    
    return {"hierarchy": result}

