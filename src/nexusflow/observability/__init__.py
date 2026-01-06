"""
NexusFlow Observability

Arize Phoenix integration for LLM observability and tracing.
"""

from nexusflow.observability.phoenix import get_tracer, setup_phoenix

__all__ = ["setup_phoenix", "get_tracer"]
