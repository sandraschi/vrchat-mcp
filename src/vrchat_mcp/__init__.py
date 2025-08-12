"""
VRChat MCP - A FastMCP 2.10 implementation for controlling VRChat avatars and assets.

This module provides a comprehensive interface for interacting with VRChat avatars,
including OSC control, parameter management, and NPC behavior.
"""

__version__ = "0.1.0"

import asyncio
import logging
from typing import Any, Dict, Optional

from fastmcp import FastMCP, JSONRPCRequest, JSONRPCResponse, JSONRPCError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Create the main MCP instance
mcp = FastMCP(
    name="vrchat-mcp",
    version=__version__,
    description="MCP server for VRChat avatar and asset control",
    protocol=["stdio"]  # We'll start with stdio only for now
)
