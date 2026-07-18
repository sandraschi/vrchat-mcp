# VRChat MCP: SOTA Industrial v14.1.0

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

**Unified Control Plane for VRChat Avatar Orchestration & Protocol Telemetry.**

> ⚠️ **This server is runtime control only — it does not build worlds.**
> `manage_world` is metadata/search (REST), not content authoring. For the
> actual Unity/VRChat SDK build pipeline (scene assembly, asset import,
> validation) using `unity3d-mcp`, and an honest account of what's
> automatable vs. still manual (Udon scripting, world publish), see
> **[docs/Building_VRChat_Worlds_With_Unity3D_MCP.md](docs/Building_VRChat_Worlds_With_Unity3D_MCP.md)**.

## Quick Start

```powershell
git clone https://github.com/sandraschi/vrchat-mcp
cd vrchat-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

### Manual Setup

If you don't have `just` installed:

## ── Architectural Overview ───────────────────────────────────────────────────

VRChat MCP is an industrialized automation layer designed for 2026-era agentic workflows. It leverages high-fidelity OSC integration to provide character state management, smooth parameter interpolation, and real-time protocol traffic analysis.

- **FastMCP 3.2.0 Core**: Strict JSON-RPC protocol compliance with zero-stdout commitment.
- **Portmanteau Design**: Consolidated high-utility tools for reduced cognitive load.
- **SOTA Dashboard**: Premium React-based telemetry interface (Port 10796).
- **Dual Transport**: Supports both Standard I/O (Claude Desktop) and HTTP Streamable modes.

## ── Unified Portmanteau Tools ────────────────────────────────────────────────

### `manage_avatar`
Consolidated character management engine.
- `get_state`: Full metadata retrieval (OSC + REST metadata enrichment).
- `load`: Trigger specific avatar instance loading.
- `set_param`: Industrial parameter updates with duration/easing support.
- `get_param`: Precise query for current parameter values.

### `manage_world`
World discovery and instance telemetry (REST API Required).
- `get_info`: Fetch metadata for a world ID.
- `search`: Search for active worlds and instances.

### `manage_economy`
Creator Economy and Credits (REST API Required).
- `balance`: View current VRChat Credit balance.
- `products`: List active Udon products and subscriptions.

### `manage_input`
Industrial Input Simulation (OSC).
- `chatbox`: Send text (max 144 chars) with typing indicators.
- `jump`: Trigger atomic jump actions.
- `move`/`look`: Set movement/look vectors (-1.0 to 1.0).

### `manage_osc`
Protocol-level traffic control plane.
- `send`: Dispatch raw OSC packets.
- `stats`: Real-time traffic telemetry.

### `manage_system`
Administrative and diagnostic control hub.
- `status`: Availability checklist for all components (OSC, REST, Pipeline).
- `metrics`: Performance telemetry (RPS, Latency, Errors).
- `auth_2fa`: Verify login via 2FA handshake (Email/TOTP).
- `secrets`: Industrial secret management for `VRCHAT_USERNAME`, `VRCHAT_PASSWORD`.

## ── Authentication & 2FA ───────────────────────────────────────────────────

VRChat MCP utilizes the official REST API for high-fidelity data.
1. **Credentials**: Set `VRCHAT_USERNAME` and `VRCHAT_PASSWORD` via `manage_system(operation="secrets")`.
2. **2FA Handshake**: If prompted in the logs, provide your code via `manage_system(operation="auth_2fa", value="123456")`.
3. **Pipeline**: Upon successful auth, the server automatically connects to the **Websocket Pipeline** for real-time notifications.

## ── Installation & Deployment ────────────────────────────────────────────────

### Standard Fleet Installation
```bash
# Clone the industrialized repository
git clone d:/Dev/repos/vrchat-mcp
cd vrchat-mcp

# Deploy SOTA environment
uv sync
```

### Claude Desktop Configuration
Add the following to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "vrchat-mcp": {
    "command": "uv",
    "args": [
      "--directory", "D:/Dev/repos/vrchat-mcp",
      "run", "vrchat-mcp"
    ]
  }
}
```

## ── Operational Ports ────────────────────────────────────────────────────────

| Component | Default Port | Environment Variable |
|-----------|--------------|----------------------|
| **MCP Backend** | `10795` | `MCP_PORT` |
| **SOTA Web UI** | `10796` | `VITE_PORT` |
| **OSC Send** | `9000` | `OSC_SEND_PORT` |
| **OSC Receive** | `9001` | `OSC_RECV_PORT` |

## ── Development Operations ───────────────────────────────────────────────────

Managed via the industrialized `justfile`:
- `just lint`: Execute Ruff SOTA v14.1 quality audit.
- `just fix`: Apply automated hardening and formatting.
- `just up`: Launch the full SOTA stack (Backend + Dashboard).

---
**Architected by FlowEngineer sandraschi**
© 2026 Android Robotics Doctrine - Industrial Fleet Documentation.


## 🛡️ Industrial Quality Stack

This project adheres to **SOTA 14.1** industrial standards for high-fidelity agentic orchestration:

- **Python (Core)**: [Ruff](https://astral.sh/ruff) for linting and formatting. Zero-tolerance for `print` statements in core handlers (`T201`).
- **Webapp (UI)**: [Biome](https://biomejs.dev/) for sub-millisecond linting. Strict `noConsoleLog` enforcement.
- **Protocol Compliance**: Hardened `stdout/stderr` isolation to ensure crash-resistant JSON-RPC communication.
- **Automation**: [Justfile](./justfile) recipes for all fleet operations (`just lint`, `just fix`, `just dev`).
- **Security**: Automated audits via `bandit` and `safety`.
