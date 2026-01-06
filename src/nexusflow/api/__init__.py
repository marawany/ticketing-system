"""
NexusFlow API

FastAPI-based REST API for ticket classification and management.
"""

from nexusflow.api.main import app, create_app

__all__ = ["app", "create_app"]
