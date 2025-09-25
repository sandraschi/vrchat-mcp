"""
VRChat MCP Tools

This package contains various tools and utilities for the VRChat MCP server.
"""

from .osc.tools import OSCManager
from .npc.tools import NPCManager
from .avatar.tools import AvatarManager
from .shared.fastsearch import FastSearch, fast_search

# Initialize the FastSearch instance with standard VRChat parameters
fast_search = FastSearch()

__all__ = [
    'OSCManager',
    'NPCManager',
    'AvatarManager',
    'FastSearch',
    'fast_search'
]
