"""
Health Check Routes

Endpoints for health monitoring and system status.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from nexusflow.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    version: str
    environment: str
    services: dict[str, Any]


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    ready: bool
    checks: dict[str, bool]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.

    Returns the application status and version.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        environment=settings.environment,
        services={
            "api": "running",
            "phoenix_enabled": settings.phoenix_enabled,
        },
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness check endpoint.

    Verifies all required services are available.
    """
    checks = {
        "neo4j": False,
        "milvus": False,
    }

    # Check Neo4j
    try:
        from nexusflow.db.neo4j_client import get_neo4j_client

        neo4j = await get_neo4j_client()
        async with neo4j.session() as session:
            await session.run("RETURN 1")
        checks["neo4j"] = True
    except Exception:
        pass

    # Check Milvus
    try:
        from nexusflow.db.milvus_client import get_milvus_client

        milvus = get_milvus_client()
        milvus.get_collection_stats()
        checks["milvus"] = True
    except Exception:
        pass

    all_ready = all(checks.values())

    if not all_ready:
        raise HTTPException(status_code=503, detail={"ready": False, "checks": checks})

    return ReadinessResponse(ready=True, checks=checks)


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check endpoint.

    Simple check that the service is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
