# Tools — vrchat-mcp

MCP tools are registered in `src/vrchat_mcp/server.py` (`manage_*` portmanteau
functions over OSC + avatar state). All return dialogic dicts — always read
`status`/`success` and `message` first.

| Tool | Operations |
|------|-----------|
| `manage_avatar` | load, state, set_parameter, list, current |
| `manage_osc` | send message/bundle/parameter, connect, disconnect |
| `manage_world` | info, query instances |
| `manage_economy` | status operations |
| `manage_social` | friends/social operations |
| `manage_input` | movement/input actions |
| `manage_system` | help, status, health |

Domain logic lives in `src/vrchat_mcp/tools/{avatar,osc,npc}/` (manager
classes like `AvatarManager`, `OSCManager`, `TVShowNLPProcessor`) and
`src/vrchat_mcp/tools/shared/` (`fastsearch.py`).

## REST/debug

- Debug UI (live traffic, message log, OSC sender): served on `:8765`
  (`--debug-ui-host/--debug-ui-port`, `--no-debug-ui` to disable).
  Frontend source: `src/vrchat_mcp/web/` (plain JS + HTML + CSS, Biome-linted).
- Web dashboard: `web_sota/` on the registered 10712 port.
- REST surface: see `src/vrchat_mcp/server.py` + `__init__.py` (`/health`,
  OpenAPI JSON) and `docs/USAGE.md` if present.

Full parameter reference: tool docstrings + `llms-full.txt` when regenerated.
