# Changelog

All notable changes to VRChat MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-09-03

### Fixed
- **`manage_economy(operation="balance")` was returning fabricated data**: hardcoded
  `{"credits": 5000, "status": "active"}` regardless of the actual account, with a comment
  claiming the real `EconomyApi` call was "pending server-side rollout." It wasn't -
  `EconomyApi.get_balance(user_id)` has been a real method on the already-installed
  `vrchatapi` SDK the whole time. Now calls it for real. `manage_economy(operation=
  "products")` had the same issue (hardcoded empty placeholder) - fixed with
  `get_product_purchases`/`get_current_subscriptions`.
- **`pipeline_client.py`'s reconnect was fake**: on `ConnectionClosed` it logged
  "Reconnecting..." then immediately gave up (`is_running = False; break`) - the log message
  promised behavior the code never implemented. Now does a real bounded reconnect (5 attempts,
  linear backoff) before giving up.

### Added (friends/users/notifications - vrchat-mcp only used 3 of vrchatapi's 18 API classes)
- `manage_social` (new portmanteau tool): `list_friends`, `friend_status`,
  `send_friend_request`, `accept_friend_request`, `unfriend`, `get_user`, `get_user_by_name`,
  `search_users`, `notifications` (REST snapshot), `recent_events` (reads the Pipeline
  websocket's in-memory buffer, see below). Wires up `FriendsApi`/`UsersApi`/
  `NotificationsApi` in `api_client.py`, none of which were used before this.
  `purchase_product_listing` and bulk-delete notification/persistence operations were
  deliberately NOT wired up (real-money and bulk-destructive actions, out of scope for an
  auto-callable read/write tool). groups/instances/avatars/inventory/etc. also remain
  unwired - a real gap, not claimed as covered.
- `pipeline_client.py` gained a bounded (50-event) ring buffer of every event received,
  regardless of whether a handler was registered for its type - previously, an event with no
  registered handler was only logged at debug level and otherwise dropped entirely, with no
  way to query "what happened while I wasn't listening."
- **Verification**: offline only (no live VRChat login/2FA performed) - `manage_social`'s full
  dispatch (all 10 operations, including the no-REST-client and no-pipeline error paths) and
  `manage_economy`'s fixed balance/products dispatch were tested against mocked API clients;
  the pipeline event buffer's append/filter/limit/bounded-size behavior was tested directly.
  Real vrchatapi method signatures (`get_balance`, `get_friends`, `search_users`, etc.) were
  introspected from the installed package before writing the calls, not guessed from docs.
  What was NOT verified: an actual authenticated call to any of these endpoints (that needs a
  real account + 2FA flow this session didn't run).

## [14.1.0] - 2026-04-13

### Added
- Integrated official VRChat REST API (`vrchatapi`) for high-fidelity metadata.
- Integrated VRChat "Pipeline" (Websocket) for real-time notifications (Invites, Friends).
- New Portmanteau Tool: `manage_world` (Search, Get Info).
- New Portmanteau Tool: `manage_economy` (VRChat Credits, Creator Economy products).
- New Portmanteau Tool: `manage_input` (OSC-simulated Chatbox text and Movement axes).
- Industrial 2FA Handshake flow in `manage_system(operation="auth_2fa")`.
- Proactive 60-second caching for REST API compliance.
- FastMCP 3.2.0 dual interface implementation (MCP stdio + FastAPI HTTP).
- `/api/docs` OpenAPI documentation endpoint and `/health` check.
- SOTA Dashboard (React) for real-time telemetry and OSC traffic monitoring.
- DXT/MCPB industrial packaging workflow.

### Changed
- Updated to FastMCP 2.12+ framework
- Restructured server.py to be thin (< 150 lines) per production checklist
- Organized tools into proper category subdirectories
- Updated CLI to support dual interface modes
- Improved error handling and type hints throughout

### Fixed
- Implemented proper MCP tool registration with multiline decorators
- Added comprehensive input validation
- Enhanced logging with structured format
- Fixed import paths for modular architecture

### Technical Improvements
- Dual interface support (stdio MCP + HTTP FastAPI)
- Modular tool organization with clean separation of concerns
- Comprehensive test coverage with unit and integration tests
- Production-ready packaging and deployment workflow
- Cross-platform PowerShell compatibility
- CORS-enabled FastAPI for web access

## [0.1.0] - 2024-01-15

### Added
- Initial FastMCP implementation for VRChat avatar control
- OSC communication system for VRChat integration
- Basic avatar parameter management
- Plugin system with decorator-based registration
- Debug UI with WebSocket support
- FastSearch integration for asset lookup
- NPC conversation management system
- Interpolation system for smooth parameter transitions

### Technical Details
- FastMCP 2.10 compatible
- Python 3.8+ support
- OSC over UDP for VRChat communication
- WebSocket-based debug interface
- Plugin architecture with event system
- Pydantic models for type safety


