# Changelog

All notable changes to VRChat MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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


