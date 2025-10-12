from typing import Optional

from fastapi import APIRouter

from models.forecast import ConfigUpdate
from services.config_service import ConfigService

router = APIRouter()

config_service = ConfigService()


@router.get("/configs")
async def get_latest_config():
    """Return the currently effective configuration."""
    return config_service.get_latest_config()


@router.post("/configs")
async def update_config(payload: ConfigUpdate):
    """Append a new configuration update and return the recorded entry."""
    record = config_service.append_update(payload)
    return record.dict()


@router.get("/configs/history")
async def get_config_history(limit: Optional[int] = None):
    """Return the configuration change history."""
    return config_service.get_history(limit)
