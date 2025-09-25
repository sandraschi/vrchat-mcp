"""
Pytest configuration and shared fixtures for VRChat MCP tests.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from vrchat_mcp.plugins.example_plugin import ExamplePlugin


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Provide a standard mock configuration for testing."""
    return {
        "osc": {
            "client_ip": "127.0.0.1",
            "client_port": 9000,
            "server_ip": "127.0.0.1",
            "server_port": 9001,
        },
        "debug_ui": {
            "enabled": False,  # Disable for tests
            "host": "127.0.0.1",
            "port": 8765
        },
        "logging": {
            "level": "WARNING",  # Reduce log noise during tests
            "file": None
        }
    }


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary directory for test data."""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()
    return test_dir


# Custom markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# Test selection helpers
def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # Mark unit tests
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark slow tests (can be extended with specific test names)
        if "slow" in item.keywords or "performance" in str(item.name).lower():
            item.add_marker(pytest.mark.slow)


@pytest.fixture
def example_plugin():
    """Create an instance of the ExamplePlugin for testing."""
    return ExamplePlugin()


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server for testing."""
    mock_server = MagicMock()
    mock_server.start = AsyncMock()
    mock_server.stop = AsyncMock()
    mock_server.register_tool = AsyncMock()
    return mock_server