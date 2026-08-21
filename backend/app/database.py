from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .settings import settings


def get_conn() -> sqlite3.Connection:
    """Return a SQLite connection.

    check_same_thread=False is required for FastAPI's threadpool usage.
    """

    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT,
                device_type TEXT NOT NULL,
                os TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                device_type TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                quality TEXT NOT NULL,
                issues_json TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(device_id) REFERENCES devices(device_id)
            );

            CREATE INDEX IF NOT EXISTS idx_metrics_device_time
            ON metrics(device_id, collected_at DESC);

            CREATE INDEX IF NOT EXISTS idx_metrics_type_time
            ON metrics(metric_type, collected_at DESC);

            CREATE INDEX IF NOT EXISTS idx_metrics_quality_time
            ON metrics(quality, collected_at DESC);

            CREATE TABLE IF NOT EXISTS mesh_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                peer_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_mesh_events_time
            ON mesh_events(created_at DESC);
            """
        )
        # Geriye uyumlu migration: yeni kolonlar yoksa ekle
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(metrics)").fetchall()}
        for col, ddl_type in (
            ("quality_score", "INTEGER"),
            ("explanations_json", "TEXT"),
            ("recommendations_json", "TEXT"),
        ):
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE metrics ADD COLUMN {col} {ddl_type}")


def upsert_device(device_id: str, device_name: str | None, device_type: str, os_name: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        existing = conn.execute("SELECT device_id FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE devices
                SET device_name = COALESCE(?, device_name),
                    device_type = ?,
                    os = COALESCE(?, os),
                    last_seen = ?
                WHERE device_id = ?
                """,
                (device_name, device_type, os_name, now, device_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO devices(device_id, device_name, device_type, os, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (device_id, device_name, device_type, os_name, now, now),
            )


def insert_metric(*, device_id: str, device_type: str, metric_type: str, collected_at: datetime,
                  payload: dict[str, Any], quality: str, issues: list[str], root_cause: str,
                  quality_score: int | None = None,
                  explanations: list[str] | None = None,
                  recommendations: list[str] | None = None) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO metrics(
                device_id, device_type, metric_type, collected_at, payload_json,
                quality, issues_json, root_cause, created_at,
                quality_score, explanations_json, recommendations_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                device_type,
                metric_type,
                collected_at.isoformat(),
                json.dumps(payload, ensure_ascii=False),
                quality,
                json.dumps(issues, ensure_ascii=False),
                root_cause,
                created_at,
                quality_score,
                json.dumps(explanations or [], ensure_ascii=False),
                json.dumps(recommendations or [], ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)


def latest_metrics(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM metrics
            ORDER BY collected_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_metric_row_to_dict(row) for row in rows]


def latest_metrics_for_device(device_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM metrics
            WHERE device_id = ?
            ORDER BY collected_at DESC
            LIMIT ?
            """,
            (device_id, limit),
        ).fetchall()
        return [_metric_row_to_dict(row) for row in rows]


def list_devices(stale_after: int, offline_after: int) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
        out = []
        for row in rows:
            last_seen = datetime.fromisoformat(row["last_seen"])
            age = (now - last_seen).total_seconds()
            if age > offline_after:
                status = "offline"
            elif age > stale_after:
                status = "stale"
            else:
                status = "active"
            out.append({
                "device_id": row["device_id"],
                "device_name": row["device_name"],
                "device_type": row["device_type"],
                "os": row["os"],
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
                "status": status,
            })
        return out


def summary_last_metrics(limit: int = 200) -> dict[str, Any]:
    metrics = latest_metrics(limit=limit)
    total = len(metrics)
    if total == 0:
        return {"sample_count": 0, "quality_counts": {}, "root_cause_counts": {}}

    quality_counts: dict[str, int] = {}
    root_counts: dict[str, int] = {}
    for item in metrics:
        quality_counts[item["quality"]] = quality_counts.get(item["quality"], 0) + 1
        root_counts[item["root_cause"]] = root_counts.get(item["root_cause"], 0) + 1

    return {
        "sample_count": total,
        "quality_counts": quality_counts,
        "root_cause_counts": root_counts,
        "latest": metrics[0],
    }


def _metric_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a DB row to an API dict.

    New columns (quality_score, explanations_json, recommendations_json)
    may be absent in older DBs; they are read safely via `row.keys()`.
    """

    keys = set(row.keys())
    out: dict[str, Any] = {
        "id": row["id"],
        "device_id": row["device_id"],
        "device_type": row["device_type"],
        "metric_type": row["metric_type"],
        "collected_at": row["collected_at"],
        "payload": json.loads(row["payload_json"]),
        "quality": row["quality"],
        "issues": json.loads(row["issues_json"]),
        "root_cause": row["root_cause"],
        "created_at": row["created_at"],
    }
    if "quality_score" in keys and row["quality_score"] is not None:
        out["quality_score"] = row["quality_score"]
    if "explanations_json" in keys and row["explanations_json"]:
        out["explanations"] = json.loads(row["explanations_json"])
    if "recommendations_json" in keys and row["recommendations_json"]:
        out["recommendations"] = json.loads(row["recommendations_json"])
    return out


def insert_mesh_event(*, device_id: str, peer_id: str, kind: str,
                      detail: str, created_at: datetime | None = None) -> int:
    """Store a mesh state-change event (peer up/down, path switch, ...)."""
    ts = (created_at or datetime.now(timezone.utc)).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO mesh_events(device_id, peer_id, kind, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (device_id, peer_id, kind, detail, ts),
        )
        return int(cur.lastrowid)


def list_mesh_events(limit: int = 50) -> list[dict[str, Any]]:
    """Newest mesh events first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM mesh_events ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "device_id": r["device_id"],
                "peer_id": r["peer_id"],
                "kind": r["kind"],
                "detail": r["detail"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
