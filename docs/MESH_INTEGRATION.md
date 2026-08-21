# Mesh Integration (meshlink)

HomeNetIQ can monitor the health of a [meshlink](https://github.com/firfircelik/network-project)
encrypted P2P mesh VPN alongside Wi-Fi/LAN/WAN telemetry.

## What you get

- **New metric type `mesh`** — one metric per mesh peer with:
  `peer_id`, `established`, `path` (`direct`/`relay`/`none`), `rtt_ms`,
  `rekeys`, `session_age_s`, `endpoint`, `registry_count`, `coordinator_up_s`.
- **Quality rules** — unestablished peers, relay fallbacks, high tunnel RTT
  and empty registries lower the 0–100 score (see `backend/app/quality.py`).
- **Root causes** — `mesh_peer_offline`, `nat_traversal_limited`,
  `nat_traversal_failed`, `mesh_path_degraded`,
  `coordinator_registration_issue`.
- **Dashboard page** — "🔐 Mesh VPN": peer table, direct/relay counts,
  RTT trend chart, diagnosis notes.

## How it works

```
meshlink (Go)                       HomeNetIQ (Python)
agent status --json ──stdout JSON──▶ collectors/meshlink_agent.py
                                    │ parse → canonical payload(s)
                                    ▼
                                    POST /api/v1/metrics ──▶ quality engine ──▶ dashboard
```

The collector only *reads* meshlink status; it never configures the mesh.

## Setup

```sh
./scripts/install.sh          # venv + meshlink binaries + config + systemd units
sudo systemctl enable --now homenetiq-backend homenetiq-mesh-agent
```

Manual alternative:

```sh
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cp config/meshlink_agent.yaml.example config/meshlink_agent.yaml  # düzenle
.venv/bin/python collectors/meshlink_agent.py --config config/meshlink_agent.yaml --once
```

Key config fields (`meshlink:` section):

| Field | Meaning |
|---|---|
| `bin` | path to the meshlink **agent** binary |
| `name` / `keyfile` | this device's mesh identity |
| `coordinator` / `coord_pubkey` | control-plane address + pinned key |
| `probe_peer` | optional: ping this peer before snapshotting so the report contains a real path/RTT |

> The installer captures `coord_pubkey` from a coordinator started with the
> **persistent** keyfile `data/coordinator.key`. Run your real coordinator
> with that same file, otherwise agents correctly reject it (key pinning).

## Notes

- `rtt_ms` is `null` until a probe succeeds; use `probe_peer` for immediate
  measurements.
- A transient status agent may briefly report `established=false` right after
  start; scheduled runs (30 s interval) converge once paths form.
