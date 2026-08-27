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

The collector only *reads* meshlink status; it never configures or operates
the mesh. Coordinator, relay and membership stay in meshlink. HomeNetIQ
pins `schema_version` (see `docs/MESH_STATUS.schema.json`): unknown **major**
is a hard error; extra fields on a known major are ignored.

`GET /api/v1/mesh/pubkey` is a coordinator **pin** for enrollment UX, not
membership. Joining requires meshlink `--preauth` when the coordinator was
started with `-preauth`.

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
| `preauth` | meshlink enrollment token (required when the coordinator has `-preauth`) |

> The installer captures `coord_pubkey` from a coordinator started with the
> **persistent** keyfile `data/coordinator.key`. Run your real coordinator
> with that same file, otherwise agents correctly reject it (key pinning).

## Notifications & events

Set `HOMENETIQ_NOTIFY_URL` (e.g. an ntfy topic) and every mesh state change —
peer down/up, direct↔relay switch — is POSTed there **and** stored in the
`mesh_events` table, exposed at `GET /api/v1/mesh/events` and shown in the
dashboard's "Recent Events" feed. The URL is also editable live from the
dashboard's "⚙️ Settings" page (persisted to `data/settings.json`).

## Real VPN traffic (TUN, two devices)

```sh
# HOST machine (root):
sudo ./scripts/tun-pair.sh server
# CLIENT machine:
sudo ./scripts/tun-pair.sh client <HOST_LAN_IP>
# then real traffic: ping 10.42.0.1 / ssh user@10.42.0.1
```

Overlay subnet is 10.42.0.0/24 (host .1, client .2). Requires root on both
ends (TUN device creation).

## Joining a client device (one command)

On the second device:

```sh
HOMENETIQ_API_TOKEN=... MESHLINK_PREAUTH=... ./scripts/join.sh <HOST_IP> [name]
```

The script pulls the pinned coordinator public key from the host backend
(`GET /api/v1/mesh/pubkey`, Bearer token required) and starts the agent
with `--preauth`. The pubkey is an identity pin, not a join credential.

## Notes

- `rtt_ms` is `null` until a probe succeeds; use `probe_peer` for immediate
  measurements.
- A transient status agent may briefly report `established=false` right after
  start; scheduled runs (30 s interval) converge once paths form.
