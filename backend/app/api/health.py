"""
Liveness endpoint.

Intentionally the simplest possible route: no DB check, no dependencies.
Used by container orchestrators / uptime checks to answer "is the process
alive", as distinct from /api/status which answers "is the app configured
correctly and reachable from the frontend".
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])



@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
