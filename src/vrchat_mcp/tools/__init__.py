"""
VRChat MCP Tools

This package contains various tools and utilities for the VRChat MCP server.
"""

from .osc import OSCManager
from .npc import NPCManager
from .fastsearch import FastSearch, fast_search

# Initialize the FastSearch instance with standard VRChat parameters
fast_search = FastSearch()

__all__ = [
    'OSCManager',
    'NPCManager',
    'FastSearch',
    'fast_search'
]
