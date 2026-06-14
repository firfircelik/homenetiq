"""Agent protocol version.

All agents add this version to their payloads as the `agent_version`
field. The backend uses this only for logging/analytics; missing or
different versions do not cause errors.
"""

AGENT_PROTOCOL_VERSION = "1.0.0"
