"""
Settings API Routes

CRUD operations for application settings with persistence.
"""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nexusflow.config import settings as app_settings

logger = structlog.get_logger(__name__)

router = APIRouter()


# In-memory settings store (will be persisted to database in production)
# For now, we initialize with values from config
_settings_store: dict[str, Any] = {
    "confidence_threshold": app_settings.classification_confidence_threshold,
    "hitl_threshold": app_settings.hitl_threshold,
    "batch_size": 50,
    "enable_notifications": True,
    "enable_auto_classify": True,
    "default_model": app_settings.nexusflow_default_model,
}


class ClassificationSettings(BaseModel):
    """Classification-related settings."""
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence for auto-resolution")
    hitl_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Route to HITL if confidence below this")
    batch_size: int = Field(50, ge=10, le=500, description="Maximum tickets per batch")


class GeneralSettings(BaseModel):
    """General application settings."""
    enable_notifications: bool = Field(True, description="Enable HITL task notifications")
    enable_auto_classify: bool = Field(True, description="Automatically classify new tickets")
    default_model: str = Field("gpt-4o", description="Default LLM model")


class AllSettings(BaseModel):
    """All application settings."""
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0)
    hitl_threshold: float = Field(0.5, ge=0.0, le=1.0)
    batch_size: int = Field(50, ge=10, le=500)
    enable_notifications: bool = Field(True)
    enable_auto_classify: bool = Field(True)
    default_model: str = Field("gpt-4o")


class SettingsResponse(BaseModel):
    """Response for settings operations."""
    success: bool
    message: str
    settings: AllSettings


@router.get("", response_model=AllSettings)
async def get_all_settings():
    """
    Get all application settings.
    """
    return AllSettings(**_settings_store)


@router.put("", response_model=SettingsResponse)
async def update_all_settings(new_settings: AllSettings):
    """
    Update all application settings.
    """
    global _settings_store
    
    # Update in-memory store
    _settings_store.update(new_settings.model_dump())
    
    # Also update the app config (runtime only - won't persist to file)
    app_settings.classification_confidence_threshold = new_settings.confidence_threshold
    app_settings.hitl_threshold = new_settings.hitl_threshold
    app_settings.nexusflow_default_model = new_settings.default_model
    
    logger.info(
        "Settings updated",
        confidence_threshold=new_settings.confidence_threshold,
        hitl_threshold=new_settings.hitl_threshold,
        batch_size=new_settings.batch_size,
        default_model=new_settings.default_model,
    )
    
    return SettingsResponse(
        success=True,
        message="Settings saved successfully",
        settings=new_settings,
    )


@router.get("/classification", response_model=ClassificationSettings)
async def get_classification_settings():
    """
    Get classification-specific settings.
    """
    return ClassificationSettings(
        confidence_threshold=_settings_store["confidence_threshold"],
        hitl_threshold=_settings_store["hitl_threshold"],
        batch_size=_settings_store["batch_size"],
    )


@router.put("/classification", response_model=SettingsResponse)
async def update_classification_settings(new_settings: ClassificationSettings):
    """
    Update classification settings.
    """
    _settings_store["confidence_threshold"] = new_settings.confidence_threshold
    _settings_store["hitl_threshold"] = new_settings.hitl_threshold
    _settings_store["batch_size"] = new_settings.batch_size
    
    # Update runtime config
    app_settings.classification_confidence_threshold = new_settings.confidence_threshold
    app_settings.hitl_threshold = new_settings.hitl_threshold
    
    logger.info(
        "Classification settings updated",
        confidence_threshold=new_settings.confidence_threshold,
        hitl_threshold=new_settings.hitl_threshold,
        batch_size=new_settings.batch_size,
    )
    
    return SettingsResponse(
        success=True,
        message="Classification settings saved successfully",
        settings=AllSettings(**_settings_store),
    )


@router.get("/general", response_model=GeneralSettings)
async def get_general_settings():
    """
    Get general application settings.
    """
    return GeneralSettings(
        enable_notifications=_settings_store["enable_notifications"],
        enable_auto_classify=_settings_store["enable_auto_classify"],
        default_model=_settings_store["default_model"],
    )


@router.put("/general", response_model=SettingsResponse)
async def update_general_settings(new_settings: GeneralSettings):
    """
    Update general application settings.
    """
    _settings_store["enable_notifications"] = new_settings.enable_notifications
    _settings_store["enable_auto_classify"] = new_settings.enable_auto_classify
    _settings_store["default_model"] = new_settings.default_model
    
    # Update runtime config
    app_settings.nexusflow_default_model = new_settings.default_model
    
    logger.info(
        "General settings updated",
        enable_notifications=new_settings.enable_notifications,
        enable_auto_classify=new_settings.enable_auto_classify,
        default_model=new_settings.default_model,
    )
    
    return SettingsResponse(
        success=True,
        message="General settings saved successfully",
        settings=AllSettings(**_settings_store),
    )


@router.post("/reset")
async def reset_settings():
    """
    Reset all settings to defaults.
    """
    global _settings_store
    
    _settings_store = {
        "confidence_threshold": 0.7,
        "hitl_threshold": 0.5,
        "batch_size": 50,
        "enable_notifications": True,
        "enable_auto_classify": True,
        "default_model": "gpt-4o",
    }
    
    # Reset runtime config
    app_settings.classification_confidence_threshold = 0.7
    app_settings.hitl_threshold = 0.5
    app_settings.nexusflow_default_model = "gpt-4o"
    
    logger.info("Settings reset to defaults")
    
    return {
        "success": True,
        "message": "Settings reset to defaults",
        "settings": _settings_store,
    }

