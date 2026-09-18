"""
AnatoVision API — application entrypoint.

Phase 1 scope only: app wiring, CORS, and two routes (/health, /api/status).
No anatomy, DICOM, or auth routes belong here yet.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, status
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for AnatoVision, a free educational anatomy and "
    "radiology imaging platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(status.router)
