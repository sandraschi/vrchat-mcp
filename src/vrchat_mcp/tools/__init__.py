"""
VRChat MCP Tools

This package contains various tools and utilities for the VRChat MCP server.
"""

from .avatar.tools import AvatarManager
from .npc.tools import NPCManager
from .osc.tools import OSCManager
from .shared.fastsearch import FastSearch

# Initialize the FastSearch instance with standard VRChat parameters
_fast_search = FastSearch()
fast_search = _fast_search

__all__ = ["AvatarManager", "FastSearch", "NPCManager", "OSCManager", "fast_search"]
