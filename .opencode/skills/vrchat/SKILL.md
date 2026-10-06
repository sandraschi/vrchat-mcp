---
name: vrchat
description: Drive VRChat via OSC (avatars, NPCs, toggles) using the avatar/osc/npc portmanteau tools
---

# VRChat skill

- Tool surface: avatar/osc/npc portmanteau tools under `src/vrchat_mcp/tools/`
  plus system help/status — see `docs/TOOLS.md` when present, else tool docstrings.
- Recall: VRChat must run with OSC enabled; the debug UI (`:8765`) shows live traffic.
- Save: after tool changes run `just lint` + `just test`; never commit `*.bak*` or `__pycache__/`.
