"""
FastSearch utility for VRChat MCP.

Provides quick lookup and indexing functionality for avatars, assets, and parameters.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class FastSearch:
    """Fast search and indexing utility for VRChat MCP."""

    def __init__(self):
        """Initialize the FastSearch instance."""
        self.parameters: Dict[str, Dict[str, Any]] = {}
        self.osc_endpoints: Dict[str, Dict[str, Any]] = {}
        logger.info("FastSearch initialized")

    async def index_parameter(self, param_name: str, param_type: str = "Float", source: str = "unknown", first_seen: Optional[float] = None) -> None:
        """Index a parameter for fast lookup."""
        if first_seen is None:
            first_seen = asyncio.get_event_loop().time()

        self.parameters[param_name] = {
            "type": param_type,
            "source": source,
            "first_seen": first_seen,
            "last_seen": asyncio.get_event_loop().time()
        }

        logger.debug(f"Indexed parameter: {param_name}")

    async def index_osc_endpoint(self, endpoint: str, description: str = "", first_seen: Optional[float] = None) -> None:
        """Index an OSC endpoint for fast lookup."""
        if first_seen is None:
            first_seen = asyncio.get_event_loop().time()

        self.osc_endpoints[endpoint] = {
            "description": description,
            "first_seen": first_seen,
            "last_seen": asyncio.get_event_loop().time()
        }

        logger.debug(f"Indexed OSC endpoint: {endpoint}")

    def search_parameters(self, query: str) -> List[Dict[str, Any]]:
        """Search for parameters matching the query."""
        results = []
        query_lower = query.lower()

        for param_name, param_data in self.parameters.items():
            if query_lower in param_name.lower():
                results.append({
                    "name": param_name,
                    **param_data
                })

        return results

    def search_osc_endpoints(self, query: str) -> List[Dict[str, Any]]:
        """Search for OSC endpoints matching the query."""
        results = []
        query_lower = query.lower()

        for endpoint, endpoint_data in self.osc_endpoints.items():
            if query_lower in endpoint.lower() or query_lower in endpoint_data.get("description", "").lower():
                results.append({
                    "endpoint": endpoint,
                    **endpoint_data
                })

        return results

    def get_parameter_info(self, param_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific parameter."""
        return self.parameters.get(param_name)

    def get_endpoint_info(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific OSC endpoint."""
        return self.osc_endpoints.get(endpoint)

# Create a global instance
fast_search = FastSearch()

