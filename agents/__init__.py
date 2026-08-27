"""Shared utilities for all agents/collectors.

Goal: reduce code duplication and keep agent payloads consistent. Nothing
offensive here — only telemetry collection from the user's own device on
their own network.
"""

from .config_loader import (
    AgentConfig,
    ConfigError,
    empty_required_targets,
    load_agent_config,
    load_yaml_config,
)
from .http_client import HttpError, post_metric, post_metric_with_retry
from .ping import ping_stats
from .privacy import apply_privacy, bssid_hash, bssid_redact  # noqa: F401
from .time_utils import now_iso
from .version import AGENT_PROTOCOL_VERSION

__all__ = [
    "AgentConfig",
    "ConfigError",
    "empty_required_targets",
    "load_agent_config",
    "load_yaml_config",
    "post_metric",
    "post_metric_with_retry",
    "HttpError",
    "ping_stats",
    "apply_privacy",
    "bssid_hash",
    "bssid_redact",
    "now_iso",
    "AGENT_PROTOCOL_VERSION",
]
