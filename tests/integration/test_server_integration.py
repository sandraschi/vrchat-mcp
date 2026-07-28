"""
Integration tests for VRChat MCP Server

Tests full server startup, tool registration, and shutdown.
"""

import asyncio
import logging
import subprocess
import sys
import time

import pytest
import requests

pytestmark = pytest.mark.integration

# Reduce log noise during testing
logging.getLogger().setLevel(logging.WARNING)


class TestServerIntegration:
    """Integration tests for the complete VRChat MCP server."""

    @pytest.fixture(scope="class")
    def event_loop(self):
        """Create an event loop for the test class."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    async def wait_for_server_ready(self, base_url: str, timeout: float = 10.0) -> bool:
        """Wait for server to be ready by checking health endpoint."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{base_url}/health", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "healthy":
                        return True
            except requests.RequestException:
                pass

            await asyncio.sleep(0.5)

        return False

    @pytest.mark.asyncio
    async def test_server_startup_fastapi(self):
        """Test that the server can start up in FastAPI mode."""
        server_process: subprocess.Popen | None = None

        try:
            # Start server in FastAPI mode
            import shutil

            cmd = [sys.executable, "-m", "vrchat_mcp.cli", "--mode", "fastapi", "--host", "127.0.0.1", "--port", "8999"]
            cmd[0] = shutil.which(cmd[0]) or cmd[0]
            server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Wait for server to start
            server_ready = await self.wait_for_server_ready("http://127.0.0.1:8999", timeout=15.0)
            assert server_ready, "Server failed to start within timeout"

            # Test health endpoint
            response = requests.get("http://127.0.0.1:8999/health", timeout=10)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "services" in data

            # Test OpenAPI docs endpoint
            response = requests.get("http://127.0.0.1:8999/api/docs", timeout=10)
            assert response.status_code == 200

            # Test OpenAPI schema
            response = requests.get("http://127.0.0.1:8999/api/v1/openapi.json", timeout=10)
            assert response.status_code == 200

            schema = response.json()
            assert "openapi" in schema
            assert "paths" in schema

        finally:
            # Clean up server process
            if server_process and server_process.poll() is None:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_process.kill()

    @pytest.mark.asyncio
    async def test_fastapi_tool_endpoints(self):
        """Test that FastAPI tool endpoints are accessible."""
        server_process: subprocess.Popen | None = None

        try:
            # Start server
            import shutil

            cmd = [sys.executable, "-m", "vrchat_mcp.cli", "--mode", "fastapi", "--host", "127.0.0.1", "--port", "9000"]
            cmd[0] = shutil.which(cmd[0]) or cmd[0]
            server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Wait for server to start
            server_ready = await self.wait_for_server_ready("http://127.0.0.1:9000", timeout=15.0)
            assert server_ready, "Server failed to start within timeout"

            # Test server status endpoint
            response = requests.post(
                "http://127.0.0.1:9000/api/v1/get_server_status",
                json={},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert "server" in data
            assert "version" in data
            assert "interfaces" in data

            # Test health status tool endpoint
            response = requests.post(
                "http://127.0.0.1:9000/api/v1/get_health_status",
                json={},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"

            # Test help system
            response = requests.post(
                "http://127.0.0.1:9000/api/v1/get_help",
                json={"topic": "general"},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            assert response.status_code == 200

            data = response.json()
            assert "description" in data

        finally:
            # Clean up
            if server_process and server_process.poll() is None:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_process.kill()

    @pytest.mark.asyncio
    async def test_fastapi_error_handling(self):
        """Test error handling in FastAPI endpoints."""
        server_process: subprocess.Popen | None = None

        try:
            # Start server
            import shutil

            cmd = [sys.executable, "-m", "vrchat_mcp.cli", "--mode", "fastapi", "--host", "127.0.0.1", "--port", "9001"]
            cmd[0] = shutil.which(cmd[0]) or cmd[0]
            server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Wait for server to start
            server_ready = await self.wait_for_server_ready("http://127.0.0.1:9001", timeout=15.0)
            assert server_ready, "Server failed to start within timeout"

            # Test non-existent endpoint
            response = requests.post(
                "http://127.0.0.1:9001/api/v1/nonexistent_tool",
                json={},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            assert response.status_code == 404

            # Test missing required parameters
            response = requests.post(
                "http://127.0.0.1:9001/api/v1/set_parameter",
                json={},  # Missing required fields
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            assert response.status_code == 400

            # Test invalid parameter types
            response = requests.post(
                "http://127.0.0.1:9001/api/v1/set_parameter",
                json={
                    "avatar_id": "test",
                    "parameter": "TestParam",
                    "value": {"invalid": "type"},  # Invalid type
                },
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            # This might return 200 if validation happens later, or 400 if caught early
            assert response.status_code in [200, 400]

        finally:
            # Clean up
            if server_process and server_process.poll() is None:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_process.kill()

    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """Test CORS headers for web access."""
        server_process: subprocess.Popen | None = None

        try:
            # Start server
            import shutil

            cmd = [sys.executable, "-m", "vrchat_mcp.cli", "--mode", "fastapi", "--host", "127.0.0.1", "--port", "9002"]
            cmd[0] = shutil.which(cmd[0]) or cmd[0]
            server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Wait for server to start
            server_ready = await self.wait_for_server_ready("http://127.0.0.1:9002", timeout=15.0)
            assert server_ready, "Server failed to start within timeout"

            # Test CORS preflight request
            response = requests.options(
                "http://127.0.0.1:9002/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type",
                },
                timeout=10,
            )

            # CORS headers should be present
            assert "access-control-allow-origin" in response.headers
            assert "access-control-allow-methods" in response.headers
            assert "access-control-allow-headers" in response.headers

        finally:
            # Clean up
            if server_process and server_process.poll() is None:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_process.kill()

    @pytest.mark.asyncio
    async def test_server_graceful_shutdown(self):
        """Test that the server shuts down gracefully."""
        server_process: subprocess.Popen | None = None

        try:
            # Start server
            import shutil

            cmd = [sys.executable, "-m", "vrchat_mcp.cli", "--mode", "fastapi", "--host", "127.0.0.1", "--port", "9003"]
            cmd[0] = shutil.which(cmd[0]) or cmd[0]
            server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Wait for server to start
            server_ready = await self.wait_for_server_ready("http://127.0.0.1:9003", timeout=15.0)
            assert server_ready, "Server failed to start within timeout"

            # Verify server is responding
            response = requests.get("http://127.0.0.1:9003/health", timeout=10)
            assert response.status_code == 200

        finally:
            # Test graceful shutdown
            if server_process:
                start_time = time.time()
                server_process.terminate()

                try:
                    # Wait for graceful shutdown (should be quick)
                    server_process.wait(timeout=10)
                    shutdown_time = time.time() - start_time

                    # Verify it shut down reasonably quickly
                    assert shutdown_time < 10, f"Server took too long to shut down: {shutdown_time}s"

                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    server_process.kill()
                    pytest.fail("Server failed to shut down gracefully")

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        server_process: subprocess.Popen | None = None

        try:
            # Start server
            import shutil

            cmd = [sys.executable, "-m", "vrchat_mcp.cli", "--mode", "fastapi", "--host", "127.0.0.1", "--port", "9004"]
            cmd[0] = shutil.which(cmd[0]) or cmd[0]
            server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Wait for server to start
            server_ready = await self.wait_for_server_ready("http://127.0.0.1:9004", timeout=15.0)
            assert server_ready, "Server failed to start within timeout"

            # Make concurrent requests
            import concurrent.futures

            import requests

            def make_request():
                return requests.post(
                    "http://127.0.0.1:9004/api/v1/get_health_status",
                    json={},
                    headers={"Content-Type": "application/json"},
                    timeout=5,
                )

            # Make 10 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                responses = [future.result() for future in concurrent.futures.as_completed(futures)]

            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"

        finally:
            # Clean up
            if server_process and server_process.poll() is None:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_process.kill()
