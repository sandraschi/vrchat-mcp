#!/usr/bin/env python3
"""
Local FastAPI Interface Test Script

Tests the VRChat MCP server FastAPI HTTP interface locally.
This script tests the REST API endpoints including /health and /api/docs.
"""

import asyncio
import json
import sys
import subprocess
import time
import requests
from typing import Dict, Any, Optional
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FastAPITester:
    """Test harness for FastAPI HTTP interface."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", server_command: Optional[list] = None):
        self.base_url = base_url.rstrip('/')
        self.server_command = server_command or [sys.executable, "-m", "vrchat_mcp.cli", "--mode", "fastapi", "--host", "127.0.0.1", "--port", "8000"]
        self.server_process: Optional[subprocess.Popen] = None

    async def start_server(self) -> None:
        """Start the FastAPI server process."""
        logger.info(f"Starting FastAPI server on {self.base_url}...")
        self.server_process = subprocess.Popen(
            self.server_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for server to start (check health endpoint)
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get(urljoin(self.base_url, "/health"), timeout=2)
                if response.status_code == 200:
                    logger.info("FastAPI server started successfully")
                    return
            except requests.RequestException:
                pass

            logger.debug(f"Waiting for server to start (attempt {attempt + 1}/{max_attempts})")
            await asyncio.sleep(1)

        raise RuntimeError("Server failed to start within timeout")

    async def stop_server(self) -> None:
        """Stop the FastAPI server process."""
        if self.server_process:
            logger.info("Stopping FastAPI server...")
            self.server_process.terminate()
            try:
                await asyncio.wait_for(asyncio.create_subprocess_shell(
                    f"taskkill /PID {self.server_process.pid} /T /F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                ), timeout=5.0)
            except asyncio.TimeoutError:
                self.server_process.kill()
            logger.info("FastAPI server stopped")

    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an HTTP request to the FastAPI server."""
        url = urljoin(self.base_url, endpoint)
        logger.debug(f"Making {method} request to {url}")
        return requests.request(method, url, **kwargs)

    async def test_health_endpoint(self) -> bool:
        """Test /health endpoint."""
        logger.info("Testing /health endpoint...")

        try:
            response = self.make_request("GET", "/health")

            if response.status_code != 200:
                logger.error(f"/health returned status {response.status_code}")
                return False

            try:
                data = response.json()
                logger.info(f"Health response: {data}")

                # Check required fields
                if "status" not in data:
                    logger.error("Health response missing 'status' field")
                    return False

                if data["status"] != "healthy":
                    logger.warning(f"Health status is '{data['status']}', expected 'healthy'")

                logger.info("✅ /health endpoint test passed")
                return True

            except json.JSONDecodeError:
                logger.error("Health endpoint did not return valid JSON")
                return False

        except Exception as e:
            logger.error(f"/health endpoint test failed: {e}")
            return False

    async def test_docs_endpoint(self) -> bool:
        """Test /api/docs endpoint."""
        logger.info("Testing /api/docs endpoint...")

        try:
            response = self.make_request("GET", "/api/docs")

            if response.status_code != 200:
                logger.error(f"/api/docs returned status {response.status_code}")
                return False

            # Check if it's HTML (OpenAPI docs page)
            if "text/html" not in response.headers.get("content-type", ""):
                logger.warning("Expected HTML content for /api/docs")

            # Check for OpenAPI indicators
            content = response.text.lower()
            if "openapi" not in content and "swagger" not in content:
                logger.warning("OpenAPI documentation not detected in /api/docs")

            logger.info("✅ /api/docs endpoint test passed")
            return True

        except Exception as e:
            logger.error(f"/api/docs endpoint test failed: {e}")
            return False

    async def test_openapi_schema(self) -> bool:
        """Test /api/v1/openapi.json endpoint."""
        logger.info("Testing OpenAPI schema endpoint...")

        try:
            response = self.make_request("GET", "/api/v1/openapi.json")

            if response.status_code != 200:
                logger.error(f"OpenAPI schema returned status {response.status_code}")
                return False

            try:
                schema = response.json()
                logger.info("OpenAPI schema retrieved successfully")

                # Check for required OpenAPI fields
                required_fields = ["openapi", "info", "paths"]
                for field in required_fields:
                    if field not in schema:
                        logger.error(f"OpenAPI schema missing '{field}' field")
                        return False

                # Check for VRChat MCP paths
                paths = schema.get("paths", {})
                expected_paths = ["/health", "/api/docs"]
                for path in expected_paths:
                    if path not in paths:
                        logger.warning(f"Expected path '{path}' not found in OpenAPI schema")

                logger.info("✅ OpenAPI schema test passed")
                return True

            except json.JSONDecodeError:
                logger.error("OpenAPI schema endpoint did not return valid JSON")
                return False

        except Exception as e:
            logger.error(f"OpenAPI schema test failed: {e}")
            return False

    async def test_api_endpoints(self) -> bool:
        """Test various API endpoints for tool access."""
        logger.info("Testing API tool endpoints...")

        test_endpoints = [
            {
                "path": "/api/v1/get_server_status",
                "method": "POST",
                "data": {},
                "description": "Server status endpoint"
            },
            {
                "path": "/api/v1/get_health_status",
                "method": "POST",
                "data": {},
                "description": "Health status endpoint"
            },
            {
                "path": "/api/v1/get_help",
                "method": "POST",
                "data": {"topic": "general"},
                "description": "Help system endpoint"
            },
            {
                "path": "/api/v1/set_parameter",
                "method": "POST",
                "data": {
                    "avatar_id": "test_avatar_123",
                    "parameter": "TestParameter",
                    "value": 0.5
                },
                "description": "Parameter setting endpoint"
            }
        ]

        passed = 0
        total = len(test_endpoints)

        for endpoint in test_endpoints:
            try:
                response = self.make_request(
                    endpoint["method"],
                    endpoint["path"],
                    json=endpoint["data"],
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code not in [200, 201]:
                    logger.error(f"{endpoint['description']} returned status {response.status_code}")
                    continue

                try:
                    data = response.json()
                    logger.info(f"✅ {endpoint['description']} test passed")
                    passed += 1
                except json.JSONDecodeError:
                    logger.error(f"{endpoint['description']} did not return valid JSON")
                    continue

            except Exception as e:
                logger.error(f"{endpoint['description']} test failed: {e}")
                continue

        logger.info(f"API endpoints test: {passed}/{total} passed")
        return passed == total

    async def test_error_handling(self) -> bool:
        """Test error handling for invalid requests."""
        logger.info("Testing error handling...")

        error_tests = [
            {
                "path": "/api/v1/nonexistent_tool",
                "method": "POST",
                "data": {},
                "expected_status": 404,
                "description": "Non-existent tool endpoint"
            },
            {
                "path": "/api/v1/get_parameter",
                "method": "POST",
                "data": {},  # Missing required parameters
                "expected_status": 400,
                "description": "Missing required parameters"
            },
            {
                "path": "/api/v1/set_parameter",
                "method": "POST",
                "data": {"invalid": "data"},
                "expected_status": 400,
                "description": "Invalid parameter format"
            }
        ]

        passed = 0
        total = len(error_tests)

        for test in error_tests:
            try:
                response = self.make_request(
                    test["method"],
                    test["path"],
                    json=test["data"],
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code != test["expected_status"]:
                    logger.error(f"{test['description']} returned {response.status_code}, expected {test['expected_status']}")
                    continue

                logger.info(f"✅ {test['description']} error handling test passed")
                passed += 1

            except Exception as e:
                logger.error(f"{test['description']} error handling test failed: {e}")
                continue

        logger.info(f"Error handling test: {passed}/{total} passed")
        return passed == total

    async def test_cors_headers(self) -> bool:
        """Test CORS headers for web access."""
        logger.info("Testing CORS headers...")

        try:
            # Test preflight request
            response = self.make_request(
                "OPTIONS",
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )

            # Check for CORS headers
            cors_headers = [
                "access-control-allow-origin",
                "access-control-allow-methods",
                "access-control-allow-headers"
            ]

            missing_headers = []
            for header in cors_headers:
                if header not in response.headers:
                    missing_headers.append(header)

            if missing_headers:
                logger.warning(f"Missing CORS headers: {missing_headers}")
                return False

            logger.info("✅ CORS headers test passed")
            return True

        except Exception as e:
            logger.error(f"CORS headers test failed: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """Run all FastAPI interface tests."""
        logger.info("Starting FastAPI interface tests...")

        try:
            await self.start_server()

            tests = [
                self.test_health_endpoint,
                self.test_docs_endpoint,
                self.test_openapi_schema,
                self.test_api_endpoints,
                self.test_error_handling,
                self.test_cors_headers
            ]

            passed = 0
            total = len(tests)

            for test in tests:
                if await test():
                    passed += 1
                logger.info("")  # Add spacing between tests

            logger.info(f"Test Results: {passed}/{total} tests passed")

            if passed == total:
                logger.info("🎉 All FastAPI interface tests passed!")
                return True
            else:
                logger.error(f"❌ {total - passed} tests failed")
                return False

        finally:
            await self.stop_server()


async def main():
    """Main test function."""
    tester = FastAPITester()

    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())


