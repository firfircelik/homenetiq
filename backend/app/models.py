from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class MetricIn(BaseModel):
    """Generic metric model received from agents."""

    device_id: str = Field(..., min_length=2)
    device_name: Optional[str] = None
    device_type: str = Field(..., examples=["wifi_probe", "network_probe", "browser_probe"])
    os: Optional[str] = None
    metric_type: str = Field(..., examples=["wifi", "network", "dns", "channel_scan"])
    collected_at: Optional[datetime] = None
    payload: dict[str, Any]

    def normalized_collected_at(self) -> datetime:
        return self.collected_at or datetime.now(timezone.utc)


class MetricOut(BaseModel):
    id: int
    device_id: str
    device_type: str
    metric_type: str
    collected_at: datetime
    quality: str
    issues: list[str]
    root_cause: str
    payload: dict[str, Any]
    # New optional fields (backwards compatible)
    quality_score: Optional[int] = None
    explanations: Optional[list[str]] = None
    recommendations: Optional[list[str]] = None


class DeviceOut(BaseModel):
    device_id: str
    device_name: Optional[str]
    device_type: str
    os: Optional[str]
    first_seen: datetime
    last_seen: datetime
    status: str


class StoreResponse(BaseModel):
    """Response of POST /api/v1/metrics.

    Backwards compatible: `quality`, `issues`, `root_cause` are always
    returned. New fields: `quality_score` (0-100), `explanations`,
    `recommendations`.
    """

    status: str
    metric_id: int
    device_id: str
    quality: str
    issues: list[str]
    root_cause: str
    quality_score: Optional[int] = None
    explanations: Optional[list[str]] = None
    recommendations: Optional[list[str]] = None
