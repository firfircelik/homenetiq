# Quality Engine Changelog

**Date:** 2026-06-14
**Scope:** Quality scoring, issue detection, root cause classification, recommendation generation.

## What changed

### New modules
- `backend/app/thresholds.py` — All threshold values in `@dataclass(frozen=True) Thresholds`. No more magic numbers; can be overridden via YAML/env in the future.
- `backend/app/recommendations.py` — `recommend(issues, root_cause) -> list[str]`. Root-cause tip first, then per-issue tip.

### Changed modules
- `backend/app/quality.py` — `classify_quality()` now returns `(quality, issues, quality_score, explanations)` 4-tuple. Score 0-100; category thresholds: 80 (good), 50 (warning). `_normalize_band`, `_packet_loss`, `_rssi` helpers added (`signal`/`rssi`, `packet_loss`/`packet_loss_percent` aliases; band string normalization). Cumulative severe-issue penalty (2: -5, 3+: -10) added.
- `backend/app/root_cause.py` — Order and labels updated. New values: `wifi_congestion_issue`, `gateway_or_lan_issue`, `wan_or_isp_issue`, `single_device_issue`, `probe_or_backend_issue`. Old labels (`wifi_signal_issue`, `dns_issue`, `healthy`, `unknown_issue`, `local_ap_issue`) preserved.
- `backend/app/models.py` — `StoreResponse` and `MetricOut` extended backwards-compatibly: new optional fields `quality_score`, `explanations`, `recommendations`.
- `backend/app/main.py` — `POST /api/v1/metrics` now includes 4 fields + recommendations in the response.
- `backend/app/database.py` — Added `quality_score`, `explanations_json`, `recommendations_json` columns. `init_db()` performs safe `ALTER TABLE` migration. `insert_metric()` and `_metric_row_to_dict()` support the new fields; old rows are read safely via `row.keys()`.

### Tests
- `tests/test_quality.py` — old 4 tests updated to the new 4-tuple signature.
- `tests/test_quality_engine.py` — 21 new tests:
  - 9 scenarios: perfect/weak_signal/low_snr/high_gateway_and_internet/wan_only/slow_dns/packet_loss/2.4ghz+low_tx/ap_unreachable
  - payload alias compatibility: `packet_loss` vs `packet_loss_percent`, `signal` vs `rssi`, band variants
  - recommendation: actionable text, dedup, root-cause-first order
  - score: 0-100 bounds, category thresholds, 4-tuple structure
  - 3 helper unit tests (`_normalize_band`, `_packet_loss`, `_rssi`)

**Total tests: 19 → 40 (21 new). All green.**

### Documentation
- `docs/QUALITY_ENGINE.md` — new. Score formula, issue list, root cause list, recommendation logic, payload aliases, limitations, API contract.
- `README.md` — added link to `docs/QUALITY_ENGINE.md` in the "More" section.

## Known limitations

1. **Score/category boundary:** A single `slow_dns` issue subtracts only 10 points; `quality` can still be "good" while the root cause is `dns_issue`. Logic: "good network, slightly slow DNS". v2 will refine category boundaries.
2. **Thresholds are hard-coded:** `Thresholds` dataclass is currently hardcoded. YAML/env override is intentionally out of scope.
3. **Recommendations are static:** not personalised for the installation or device.
4. **No multi-payload correlation:** metrics from multiple devices are not compared.
5. **Single-language (English) recommendations:** no i18n.

## Future improvements

1. **YAML threshold override:** `config/quality.yaml` → `settings.quality_thresholds` injection.
2. **Trend analysis:** look at the last N metrics' score movement to detect "deteriorating" patterns.
3. **Multi-device correlation:** if multiple probes on the same AP report bad results at the same time → AP-side issue.
4. **Recommendations i18n:** add `en`/`tr` mapping to the recommendation dictionary.
5. **Time-weighted score:** down-weight very old payloads.
6. **Confidence level:** return a separate field for how certain the root cause is (high/medium/low).
7. **Browser-side enrichment:** `localStorage` + `navigator.connection` to provide additional client-side metrics.

## Test run

```bash
pytest tests/ -v
```

Result: **40 passed**.
