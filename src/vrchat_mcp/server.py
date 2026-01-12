"""
VRChat MCP Server

Thin FastMCP 2.12+ server implementation with dual interface support.
This file is kept minimal (< 150 lines) per MCP Production Checklist requirements.
"""

import asyncio
import logging
import sys
from typing import Any, Dict

from . import VRChatMCP, logger


def main() -> int:
    """Entry point for the VRChat MCP server."""
    try:
        # Create the VRChat MCP instance (this handles all the logic)
        mcp_instance = VRChatMCP()

        logger.info("Starting VRChat MCP server with dual interface support...")
        logger.info("MCP stdio interface: Available for Claude Desktop integration")
        logger.info(
            "FastAPI HTTP interface: Available with /api/docs and /health endpoints"
        )

        # Start the server in MCP stdio mode for MCP clients
        asyncio.run(mcp_instance.start(mode="mcp"))

        return 0

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.exception("Fatal error in server")
        return 1


if __name__ == "__main__":
    sys.exit(main())
