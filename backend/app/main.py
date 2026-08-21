from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException

from .database import (
    init_db,
    insert_metric,
    insert_mesh_event,
    latest_metrics,
    latest_metrics_for_device,
    list_devices,
    list_mesh_events,
    summary_last_metrics,
    upsert_device,
)
from .models import MetricIn, StoreResponse
from .notifier import detect_transitions, send_notification
from .quality import classify_quality
from .recommendations import recommend
from .root_cause import classify_root_cause
from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the DB schema on application startup.

    `on_event("startup")` was deprecated in FastAPI 0.93+; the modern
    approach is the `lifespan` async context manager. It fires reliably
    both for normal runs and inside the `TestClient` context manager.
    """

    init_db()
    yield


app = FastAPI(
    title="HomeNetIQ Backend",
    description="Home network and Wi-Fi telemetry backend API",
    version="1.0.0",
    lifespan=lifespan,
)


def require_token(authorization: str | None = Header(default=None)) -> None:
    """Simple Bearer token check.

    Sufficient as a first security layer on a local network. Not enough
    if the backend is exposed to the public internet.
    """

    if not settings.require_auth:
        return
    expected = f"Bearer {settings.api_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


@app.get("/health")
def health():
    return {"status": "ok", "service": "homenetiq-backend"}


@app.get("/api/v1/mesh/pubkey")
def mesh_pubkey():
    """Serve the local meshlink coordinator's public key for LAN enrollment.

    Used by `scripts/join.sh` on client devices so they don't have to copy
    the key by hand. A public key is a *pinned identity*, not a secret —
    but note that serving it over plain HTTP means enrollment trusts the
    LAN at first use (TOFU). See docs/MESH_INTEGRATION.md.
    """
    if not settings.mesh_pubkey:
        raise HTTPException(status_code=404, detail="mesh pubkey not configured")
    return {"coord_pubkey": settings.mesh_pubkey}


@app.post("/api/v1/metrics", response_model=StoreResponse, dependencies=[Depends(require_token)])
def ingest_metric(metric: MetricIn):
    collected_at = metric.normalized_collected_at()

    quality, issues, quality_score, explanations = classify_quality(metric.metric_type, metric.payload)
    root_cause = classify_root_cause(metric.metric_type, metric.payload, issues)
    recommendations = recommend(issues, root_cause)

    # --- mesh state-change detection (BEFORE inserting the new sample) ---
    mesh_events: list[tuple[str, str]] = []
    if metric.metric_type == "mesh":
        peer_id = metric.payload.get("peer_id")
        if peer_id:
            prev_payload = None
            for row in latest_metrics_for_device(metric.device_id, limit=10):
                row_peer = (row.get("payload") or {}).get("peer_id")
                if row_peer == peer_id:
                    prev_payload = row.get("payload")
                    break
        else:
            peer_id = ""
        mesh_events = detect_transitions(prev_payload, metric.payload)

    upsert_device(metric.device_id, metric.device_name, metric.device_type, metric.os)
    metric_id = insert_metric(
        device_id=metric.device_id,
        device_type=metric.device_type,
        metric_type=metric.metric_type,
        collected_at=collected_at,
        payload=metric.payload,
        quality=quality,
        issues=issues,
        root_cause=root_cause,
        quality_score=quality_score,
        explanations=explanations,
        recommendations=recommendations,
    )

    # --- record + notify mesh state changes (after successful insert) ---
    if metric.metric_type == "mesh":
        for kind, detail in mesh_events:
            insert_mesh_event(
                device_id=metric.device_id,
                peer_id=str(metric.payload.get("peer_id") or ""),
                kind=kind,
                detail=detail,
            )
            send_notification(
                title=f"HomeNetIQ mesh: {kind}",
                body=f"{detail}\n(device: {metric.device_id})",
            )

    return StoreResponse(
        status="stored",
        metric_id=metric_id,
        device_id=metric.device_id,
        quality=quality,
        issues=issues,
        root_cause=root_cause,
        quality_score=quality_score,
        explanations=explanations,
        recommendations=recommendations,
    )


@app.get("/api/v1/metrics/latest")
def get_latest_metrics(limit: int = 50):
    return latest_metrics(limit=limit)


@app.get("/api/v1/mesh/events")
def get_mesh_events(limit: int = 50):
    """Recent mesh state-change events (peer up/down, path switches)."""
    return list_mesh_events(limit=limit)


@app.get("/api/v1/devices")
def get_devices():
    return list_devices(settings.stale_after_seconds, settings.offline_after_seconds)


@app.get("/api/v1/devices/{device_id}/latest")
def get_device_latest(device_id: str, limit: int = 50):
    return latest_metrics_for_device(device_id=device_id, limit=limit)


@app.get("/api/v1/summary")
def get_summary(limit: int = 200):
    return summary_last_metrics(limit=limit)


@app.get("/api/v1/anomalies")
def get_anomalies(limit: int = 50):
    # In v1, an anomaly is interpreted as quality != good.
    rows = latest_metrics(limit=limit * 3)
    anomalies = [row for row in rows if row["quality"] != "good"]
    return anomalies[:limit]
