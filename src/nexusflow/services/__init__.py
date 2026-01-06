"""
NexusFlow Services

Business logic services for embeddings, classification, and batch processing.
"""

from nexusflow.services.embeddings import EmbeddingService, get_embedding_service

# These are imported lazily to avoid circular imports
# Use: from nexusflow.services.classification import ClassificationService
# Use: from nexusflow.services.batch import BatchProcessor

__all__ = [
    "EmbeddingService",
    "get_embedding_service",
]
