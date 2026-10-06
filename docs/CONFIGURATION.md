# Configuration — vrchat-mcp

All knobs, one place. Copy `.env.example` to `.env` for local overrides
(`.env` is gitignored; never commit secrets).

## Environment variables

| Var | Default | Purpose |
|-----|---------|---------|
| `RESOLVE_TOOL_MODE` equivalent | portmanteau always | Tools are portmanteau by design |
| Debug UI host/port | `127.0.0.1` / `8765` | `--debug-ui-host`, `--debug-ui-port`, `--no-debug-ui` to disable |
| Web dashboard | `10712` (registry) | Frontend dev port |

## Ports (fleet registry)

Web dashboard **10712** is registered. The debug UI default (8765) and any
REST/OSC ports are code-configured — if you bind the backend for fleet use,
claim ports via `mcp-central-docs/fleet-gate/claim_ports.py` and register a
real `fleet-start.config.ps1` (the current stub with `0/0/none` is
unfinished business, not a contract).

## Transports

- `just server` / `serve` — `python -m vrchat_mcp.server` (own runner).
- MCP over stdio for Claude Desktop/Cursor; REST alongside for the dashboard.
