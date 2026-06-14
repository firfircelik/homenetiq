"""HTTP client, retry/backoff, config loader testleri."""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from agents.config_loader import (
    AgentConfig,
    ConfigError,
    load_agent_config,
    load_yaml_config,
)
from agents.http_client import (
    HttpError,
    post_metric,
    post_metric_with_retry,
)


# ---------- HTTP: Authorization header ----------

class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None) -> None:
        self.status_code = status_code
        self._json = json_body or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._json


def test_post_metric_sends_authorization_and_body(monkeypatch):
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeResponse(200, {"ok": True})

    monkeypatch.setattr("agents.http_client.requests.post", fake_post)
    out = post_metric(
        "http://x/api/v1/metrics",
        {"a": 1},
        {"Authorization": "Bearer TOKEN", "Content-Type": "application/json"},
        timeout=5,
    )
    assert out == {"ok": True}
    assert captured["url"] == "http://x/api/v1/metrics"
    assert captured["json"] == {"a": 1}
    assert captured["headers"]["Authorization"] == "Bearer TOKEN"
    assert captured["timeout"] == 5


def test_post_metric_raises_on_http_error(monkeypatch):
    def fake_post(url, json, headers, timeout):
        return _FakeResponse(500)

    monkeypatch.setattr("agents.http_client.requests.post", fake_post)
    with pytest.raises(requests.HTTPError):
        post_metric("http://x", {}, {}, timeout=1)


# ---------- Retry/backoff ----------

def test_post_metric_with_retry_succeeds_first_try(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, json, headers, timeout):
        calls["n"] += 1
        return _FakeResponse(200, {"id": 1})

    monkeypatch.setattr("agents.http_client.requests.post", fake_post)
    # Skip sleep
    monkeypatch.setattr("agents.http_client.time.sleep", lambda s: None)
    out = post_metric_with_retry("u", {}, {}, max_attempts=3, retry_delay_seconds=1, timeout=1)
    assert out == {"id": 1}
    assert calls["n"] == 1


def test_post_metric_with_retry_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, json, headers, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            return _FakeResponse(503)
        return _FakeResponse(200, {"ok": True})

    monkeypatch.setattr("agents.http_client.requests.post", fake_post)
    monkeypatch.setattr("agents.http_client.time.sleep", lambda s: None)
    out = post_metric_with_retry("u", {}, {}, max_attempts=5, retry_delay_seconds=0, timeout=1)
    assert out == {"ok": True}
    assert calls["n"] == 3


def test_post_metric_with_retry_raises_after_max_attempts(monkeypatch):
    def fake_post(url, json, headers, timeout):
        return _FakeResponse(500)

    monkeypatch.setattr("agents.http_client.requests.post", fake_post)
    monkeypatch.setattr("agents.http_client.time.sleep", lambda s: None)
    with pytest.raises(HttpError):
        post_metric_with_retry("u", {}, {}, max_attempts=2, retry_delay_seconds=0, timeout=1)


# ---------- Config loader ----------

def test_load_yaml_config_missing_file(tmp_path: Path):
    with pytest.raises(ConfigError) as exc:
        load_yaml_config(tmp_path / "nope.yaml")
    assert "not found" in str(exc.value)


def test_load_yaml_config_invalid_yaml(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text(": : not yaml")
    with pytest.raises(ConfigError) as exc:
        load_yaml_config(p)
    assert "parse" in str(exc.value).lower() or "yaml" in str(exc.value).lower()


def test_load_agent_config_minimal(tmp_path: Path):
    p = tmp_path / "cfg.yaml"
    p.write_text("""
device:
  id: dev-1
  name: My Device
  type: wifi_probe
  os: linux
  agent_version: "1.0.0"
backend:
  url: http://x/api/v1/metrics
  token: tok
""")
    cfg = load_agent_config(p)
    assert isinstance(cfg, AgentConfig)
    assert cfg.device_id == "dev-1"
    assert cfg.backend_url == "http://x/api/v1/metrics"
    assert cfg.api_token == "tok"
    assert cfg.privacy_mode == "redact"
    assert cfg.privacy_salt == ""
    assert cfg.interval_seconds == 30
    # extra should hold agent-specific fields like targets
    assert "targets" in cfg.extra or cfg.extra == {}


def test_load_agent_config_missing_device_id(tmp_path: Path):
    p = tmp_path / "cfg.yaml"
    p.write_text("""
device:
  name: X
  type: wifi_probe
  os: linux
  agent_version: "1.0.0"
backend:
  url: http://x
""")
    with pytest.raises(ConfigError) as exc:
        load_agent_config(p)
    assert "id" in str(exc.value)


def test_load_agent_config_missing_backend_url(tmp_path: Path):
    p = tmp_path / "cfg.yaml"
    p.write_text("""
device:
  id: dev-1
  name: X
  type: wifi_probe
  os: linux
  agent_version: "1.0.0"
backend:
  token: tok
""")
    with pytest.raises(ConfigError) as exc:
        load_agent_config(p)
    assert "url" in str(exc.value)


def test_load_agent_config_with_privacy_and_collector(tmp_path: Path):
    p = tmp_path / "cfg.yaml"
    p.write_text("""
device:
  id: dev-1
  name: X
  type: wifi_probe
  os: linux
  agent_version: "1.0.0"
backend:
  url: http://x
collector:
  interval_seconds: 60
  retry_delay_seconds: 5
  timeout_seconds: 7
privacy:
  mode: hash
  salt: my-salt
targets:
  gateway_ip: 192.168.1.1
  ap_ip: 192.168.1.103
  internet_ip: 1.1.1.1
""")
    cfg = load_agent_config(p)
    assert cfg.interval_seconds == 60
    assert cfg.retry_delay_seconds == 5
    assert cfg.timeout_seconds == 7
    assert cfg.privacy_mode == "hash"
    assert cfg.privacy_salt == "my-salt"
    assert cfg.extra["targets"]["gateway_ip"] == "192.168.1.1"


def test_agent_config_backend_headers_includes_authorization():
    cfg = AgentConfig(
        device_id="d", device_name="n", device_type="t", os="o",
        agent_version="1.0.0", backend_url="u", api_token="TOK",
    )
    h = cfg.backend_headers()
    assert h["Authorization"] == "Bearer TOK"
    assert h["Content-Type"] == "application/json"
    assert "User-Agent" in h
    assert "1.0.0" in h["User-Agent"]


def test_agent_config_backend_headers_no_token_means_no_auth():
    cfg = AgentConfig(
        device_id="d", device_name="n", device_type="t", os="o",
        agent_version="1.0.0", backend_url="u", api_token="",
    )
    h = cfg.backend_headers()
    assert "Authorization" not in h
