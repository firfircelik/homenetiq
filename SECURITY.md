# Security Policy

## Supported versions

Current line is HomeNetIQ v1.x (self-hosted). Fixes land on `main`.

## Reporting

Please **do not** open a public issue for a suspected vulnerability.

Use a private GitHub advisory:

https://github.com/firfircelik/homenetiq/security/advisories/new

Include version, component (backend / dashboard / collector), and impact.
Do not attach real LAN IPs, tokens, or mesh preauth secrets.

## Operator notes

- `HOMENETIQ_REQUIRE_GET_AUTH` defaults **on**. Dashboard and `join.sh` must send `HOMENETIQ_API_TOKEN`.
- Empty or `change-me-local-token` refuses to start unless `HOMENETIQ_ALLOW_INSECURE=1`.
- Bind uvicorn to `127.0.0.1` and put Caddy/nginx in front for LAN (`contrib/Caddyfile`).
- `/api/v1/mesh/pubkey` is a coordinator **pin**, not mesh membership. Membership is meshlink `-preauth`.
- HomeNetIQ **observes** an optional mesh; it does not operate the coordinator.
