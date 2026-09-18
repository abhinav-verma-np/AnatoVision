"""
Application status endpoint — this is what the frontend's
ConnectionStatus feature calls to prove the frontend <-> backend wiring
works end to end (Phase 1 requirement #4).
"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.status import StatusResponse

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    settings = get_settings()
    return StatusResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
    )
