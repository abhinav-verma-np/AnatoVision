"""
Response schemas for the /api/status endpoint.

Keep this in sync with frontend/services/statusService.ts — the field
names here are the contract the frontend's connection test depends on.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class StatusResponse(BaseModel):
    status: str = Field(examples=["ok"])
    service: str = Field(examples=["AnatoVision API"])
    environment: str = Field(examples=["development"])
    version: str = Field(examples=["0.1.0"])
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC time the response was generated.",
    )
