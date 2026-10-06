# Onboarding — vrchat-mcp

First-timer path from zero to driving your avatar.

## 1. What you need

- **VRChat** running with OSC enabled (Settings → OSC → Enabled).
- **Python 3.12+** with `uv`, **Node 20+** for the dashboard.
- Optional: local LLM (Ollama) for agentic workflows.

## 2. Sanity check (5 minutes)

```powershell
just bootstrap        # deps + pre-commit hooks + web frontend
just server           # backend: python -m vrchat_mcp.server
```

Open VRChat, enable OSC, then ask your assistant for avatar status
(avatar tools read live OSC state). Open the debug UI for raw traffic.

## 3. Common pitfalls

- **No avatar response** — VRChat closed, OSC disabled, or wrong avatar ID.
  See `docs/TROUBLESHOOTING.md`.
- **Dashboard shows disconnected** — backend down or wrong port; the debug UI
  port defaults to 8765 (flags `--debug-ui-host/--debug-ui-port`).

## 4. Money / accounts

None. VRChat Free works; no cloud account is required for any default flow.
