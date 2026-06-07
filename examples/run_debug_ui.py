#!/usr/bin/env python3
"""
Run the VRChat MCP server with the debug UI enabled.

This script starts the MCP server with the debug UI enabled and configures
logging and OSC settings for development.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vrchat_mcp import VRChatMCP  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("vrchat_mcp_debug.log")],
)

# Configuration
CONFIG = {
    "osc": {
        "client_ip": "127.0.0.1",
        "client_port": 9000,
        "server_ip": "127.0.0.1",
        "server_port": 9001,
    },
    "debug_ui": {"enabled": True, "host": "127.0.0.1", "port": 8765},
    "logging": {"level": "DEBUG", "file": "vrchat_mcp_debug.log"},
}


async def main():
    """Run the VRChat MCP server with debug UI."""
    print("Starting VRChat MCP Debug Server...")
    print(f"OSC Client: {CONFIG['osc']['client_ip']}:{CONFIG['osc']['client_port']}")
    print(f"OSC Server: {CONFIG['osc']['server_ip']}:{CONFIG['osc']['server_port']}")
    print(f"Debug UI: http://{CONFIG['debug_ui']['host']}:{CONFIG['debug_ui']['port']}")

    # Create and start the MCP server
    mcp = VRChatMCP(config=CONFIG)

    try:
        await mcp.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise
    finally:
        await mcp.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
