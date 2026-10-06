# vrchat-mcp — Copilot instructions

Avatar/osc/npc portmanteau tools (`src/vrchat_mcp/tools/`) drive VRChat over
OSC. Backend entry: `python -m vrchat_mcp.server`. VRChat must run with OSC
enabled. After tool changes run `just lint` and `just test`; never commit
`*.bak*`, `__pycache__/`, or `reports/`.
