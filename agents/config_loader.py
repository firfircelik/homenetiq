"""Configuration loading.

Agent YAML config files have required and optional fields. When a required
field is missing, a clear error is raised.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(KeyError):
    """Raised when a required config field is missing or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Read a YAML file and return it as a dict. Raises ConfigError on failure."""
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"Config file not found: {p}")
    try:
        data = yaml.safe_load(p.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"Config YAML parse error: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Config YAML must be a dict at the top level")
    return data


@dataclass
class AgentConfig:
    """Validated and normalized agent configuration.

    `load_agent_config()` builds this from YAML. All agents share these
    top-level fields; agent-specific extra fields live in `extra`.
    """

    # Device
    device_id: str
    device_name: str
    device_type: str
    os: str
    agent_version: str

    # Backend
    backend_url: str
    api_token: str = ""

    # Collector behavior
    interval_seconds: int = 30
    retry_delay_seconds: int = 10
    timeout_seconds: int = 10

    # Privacy
    privacy_mode: str = "redact"  # "redact" | "hash"
    privacy_salt: str = ""

    # Agent-specific extras (e.g. interface, target IPs)
    extra: dict[str, Any] = field(default_factory=dict)

    def backend_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "User-Agent": f"homenetiq-agent/{self.agent_version}"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers


_REQUIRED_DEVICE_KEYS = ("id", "name", "type", "os", "agent_version")
_REQUIRED_BACKEND_KEYS = ("url",)


def load_agent_config(path: str | Path) -> AgentConfig:
    """Read a YAML config file, validate it, and return an AgentConfig.

    Required fields:
      device.id, device.name, device.type, device.os, device.agent_version
      backend.url

    Optional fields:
      backend.token
      collector.interval_seconds
      collector.retry_delay_seconds
      collector.timeout_seconds
      privacy.mode, privacy.salt
    """

    raw = load_yaml_config(path)

    device = raw.get("device")
    if not isinstance(device, dict):
        raise ConfigError("Config must have a 'device' section (dict)")

    missing = [k for k in _REQUIRED_DEVICE_KEYS if k not in device or device[k] in (None, "")]
    if missing:
        raise ConfigError(f"Config device section missing field(s): {', '.join(missing)}")

    backend = raw.get("backend")
    if not isinstance(backend, dict):
        raise ConfigError("Config must have a 'backend' section (dict)")
    missing_b = [k for k in _REQUIRED_BACKEND_KEYS if k not in backend or backend[k] in (None, "")]
    if missing_b:
        raise ConfigError(f"Config backend section missing field(s): {', '.join(missing_b)}")

    collector = raw.get("collector", {}) or {}
    privacy = raw.get("privacy", {}) or {}

    # Extra: anything not in the known top-level keys
    known_top = {"device", "backend", "collector", "privacy"}
    extra = {k: v for k, v in raw.items() if k not in known_top}

    return AgentConfig(
        device_id=str(device["id"]),
        device_name=str(device["name"]),
        device_type=str(device["type"]),
        os=str(device["os"]),
        agent_version=str(device["agent_version"]),
        backend_url=str(backend["url"]),
        api_token=str(backend.get("token", "")) or "",
        interval_seconds=int(collector.get("interval_seconds", 30)),
        retry_delay_seconds=int(collector.get("retry_delay_seconds", 10)),
        timeout_seconds=int(collector.get("timeout_seconds", 10)),
        privacy_mode=str(privacy.get("mode", "redact")),
        privacy_salt=str(privacy.get("salt", "")) or "",
        extra=extra,
    )
