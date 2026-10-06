# Troubleshooting — vrchat-mcp

## Avatar does not respond

1. VRChat must be running with OSC enabled (Settings → OSC).
2. Check the debug UI (`:8765`) — if no traffic arrives, the problem is on
   the VRChat side, not the bridge.
3. Verify the avatar ID / parameter names match exactly (case-sensitive).

## Dashboard shows disconnected

1. Backend up? `just server` runs `python -m vrchat_mcp.server`.
2. Port zombie? `Get-NetTCPConnection -LocalPort <port>`; kill the owner.
3. Wrong port? Dashboard is 10712 (registry); debug UI is 8765 by default.

## Biome `ci` fails on `src/vrchat_mcp/web/app.js`

That file is plain JS inside the Python package and IS linted (repo-root
`biome ci .` covers it). Fix with `biome check --write`, never exclude it.

## Tests red / coverage floor missed

- `just test` runs unit + local; `tests/integration` needs a live server
  (deselected by default marker).
- Coverage floor is 80% (`pytest.ini`); a red floor needs a test-writing pass,
  not a threshold edit.

## `pyright` reports hundreds of errors

Install via dev extras and run `python -m pyright src/` (the console script
is absent in some envs; nodeenv bootstraps on first run). Triage by rule
before fixing; do not add bare `# type: ignore`.
