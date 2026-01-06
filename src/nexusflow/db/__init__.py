"""
NexusFlow Database Connections

Manages connections to Neo4j (graph), Milvus (vector), and SQLite (persistence) databases.
"""

from nexusflow.db.milvus_client import MilvusClient, get_milvus_client
from nexusflow.db.neo4j_client import Neo4jClient, get_neo4j_client
from nexusflow.db.repository import (
    HITLCorrectionRepository,
    HITLTaskRepository,
    MetricsRepository,
    TicketRepository,
    UserRepository,
)
from nexusflow.db.session import close_db, get_db, get_session, init_db

__all__ = [
    # Graph DB
    "Neo4jClient",
    "get_neo4j_client",
    # Vector DB
    "MilvusClient",
    "get_milvus_client",
    # SQLite session
    "init_db",
    "close_db",
    "get_session",
    "get_db",
    # Repositories
    "TicketRepository",
    "UserRepository",
    "HITLTaskRepository",
    "HITLCorrectionRepository",
    "MetricsRepository",
]
