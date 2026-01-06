"""
Turing NexusFlow FastAPI Application

Main entry point for the Turing NexusFlow REST API.
"""

from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nexusflow.api.routes import (
    analytics,
    batch,
    classification,
    health,
    hitl,
    tickets,
    users,
)
from nexusflow.api.websocket import router as websocket_router
from nexusflow.config import settings
from nexusflow.db.milvus_client import close_milvus_client, get_milvus_client
from nexusflow.db.neo4j_client import close_neo4j_client, get_neo4j_client
from nexusflow.db.session import close_db, init_db
from nexusflow.observability.phoenix import setup_phoenix
from nexusflow.services.batch import get_batch_processor

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting NexusFlow API", environment=settings.environment)

    # Setup observability
    if settings.phoenix_enabled:
        setup_phoenix()

    # Initialize SQLite database for persistence
    try:
        await init_db()
        logger.info("SQLite database initialized")
    except Exception as e:
        logger.error("Failed to initialize SQLite database", error=str(e))

    # Initialize database connections
    try:
        neo4j = await get_neo4j_client()
        await neo4j.create_schema()
        logger.info("Neo4j connected and schema verified")
    except Exception as e:
        logger.error("Failed to connect to Neo4j", error=str(e))

    try:
        milvus = get_milvus_client()
        milvus.create_collection()
        logger.info("Milvus connected and collection verified")
    except Exception as e:
        logger.error("Failed to connect to Milvus", error=str(e))

    # Start batch processor
    batch_processor = get_batch_processor()
    await batch_processor.start_workers()

    logger.info("NexusFlow API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down NexusFlow API")

    await batch_processor.stop_workers()
    await close_neo4j_client()
    close_milvus_client()
    await close_db()

    logger.info("NexusFlow API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Turing NexusFlow API",
        description="""
## Turing NexusFlow - Intelligent Ticket Classification System

Turing NexusFlow is an AI-powered ticket classification and resolution system that combines:

- **Graph-based classification** using Neo4j for hierarchical category matching
- **Vector similarity search** using Milvus for finding similar historical tickets
- **LLM judgment** for final classification decisions
- **Ensemble confidence scoring** with calibration
- **Human-in-the-Loop (HITL)** for low-confidence cases

### Key Features

- 🎯 **3-Level Classification**: Hierarchical categorization (L1 > L2 > L3)
- 📊 **Confidence Scoring**: Calibrated ensemble confidence with component agreement
- 🔄 **Batch Processing**: Efficient handling of large ticket volumes
- 👥 **HITL System**: Human review for uncertain classifications
- 📈 **Auto-learning**: Graph weights update based on feedback
- 🔍 **Observability**: Integrated with Arize Phoenix for monitoring

### API Sections

- `/tickets` - Ticket management
- `/classification` - Classification operations
- `/batch` - Batch processing
- `/hitl` - Human-in-the-loop tasks
- `/users` - User management
- `/analytics` - Dashboard and reports
        """,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = datetime.utcnow()

        response = await call_next(request)

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc) if settings.debug else "An unexpected error occurred",
            },
        )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["Tickets"])
    app.include_router(
        classification.router, prefix="/api/v1/classification", tags=["Classification"]
    )
    app.include_router(batch.router, prefix="/api/v1/batch", tags=["Batch Processing"])
    app.include_router(hitl.router, prefix="/api/v1/hitl", tags=["Human-in-the-Loop"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
    app.include_router(websocket_router, tags=["WebSocket"])

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "nexusflow.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
