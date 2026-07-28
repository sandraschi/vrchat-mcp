#!/usr/bin/env python3
"""
Local MCP Interface Test Script

Tests the VRChat MCP server stdio interface locally.
This script simulates Claude Desktop connecting to the MCP server.
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MCPTester:
    """Test harness for MCP stdio interface."""

    def __init__(self, server_command: list):
        self.server_command = server_command
        self.server_process: subprocess.Popen | None = None
        self.server_stdout = None
        self.server_stdin = None

    async def start_server(self) -> None:
        """Start the MCP server process."""
        logger.info("Starting MCP server...")

        # Resolve command path for S603/S607 compliance
        import shutil

        cmd = list(self.server_command)
        cmd[0] = shutil.which(cmd[0]) or cmd[0]

        self.server_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        self.server_stdin = self.server_process.stdin
        self.server_stdout = self.server_process.stdout

        # Give server time to start
        await asyncio.sleep(2)
        logger.info("MCP server started")

    async def stop_server(self) -> None:
        """Stop the MCP server process."""
        if self.server_process:
            logger.info("Stopping MCP server...")
            self.server_process.terminate()
            try:
                await asyncio.wait_for(self.server_process.wait(), timeout=5.0)
            except TimeoutError:
                self.server_process.kill()
            logger.info("MCP server stopped")

    async def send_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        if not self.server_stdin:
            raise RuntimeError("Server not started")

        # Send request
        request_json = json.dumps(request)
        logger.debug(f"Sending request: {request_json}")
        self.server_stdin.write(request_json + "\n")
        self.server_stdin.flush()

        # Read response
        if not self.server_stdout:
            raise RuntimeError("Server stdout not available")

        response_line = self.server_stdout.readline().strip()
        if not response_line:
            raise RuntimeError("No response received from server")

        logger.debug(f"Received response: {response_line}")
        return json.loads(response_line)

    async def test_tools_list(self) -> bool:
        """Test tools/list request."""
        logger.info("Testing tools/list...")

        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

        try:
            response = await self.send_request(request)

            if "error" in response:
                logger.error(f"tools/list failed: {response['error']}")
                return False

            tools = response.get("result", {}).get("tools", [])
            logger.info(f"Found {len(tools)} tools")

            # Check for required tools
            tool_names = [tool.get("name") for tool in tools]
            required_tools = [
                "get_server_status",
                "get_health_status",
                "get_help",
                "get_avatar_state",
                "load_avatar",
                "set_parameter",
                "get_parameter",
                "send_osc_message",
                "get_osc_statistics",
            ]

            missing_tools = [tool for tool in required_tools if tool not in tool_names]
            if missing_tools:
                logger.error(f"Missing required tools: {missing_tools}")
                return False

            logger.info("✅ tools/list test passed")
            return True

        except Exception as e:
            logger.error(f"tools/list test failed: {e}")
            return False

    async def test_server_status(self) -> bool:
        """Test get_server_status tool."""
        logger.info("Testing get_server_status...")

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_server_status", "arguments": {}},
        }

        try:
            response = await self.send_request(request)

            if "error" in response:
                logger.error(f"get_server_status failed: {response['error']}")
                return False

            result = response.get("result", {})
            logger.info(f"Server status: {result.get('status', 'unknown')}")

            # Check required fields
            required_fields = ["server", "version", "status", "interfaces"]
            for field in required_fields:
                if field not in result:
                    logger.error(f"Missing field '{field}' in server status")
                    return False

            logger.info("✅ get_server_status test passed")
            return True

        except Exception as e:
            logger.error(f"get_server_status test failed: {e}")
            return False

    async def test_health_status(self) -> bool:
        """Test get_health_status tool."""
        logger.info("Testing get_health_status...")

        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_health_status", "arguments": {}},
        }

        try:
            response = await self.send_request(request)

            if "error" in response:
                logger.error(f"get_health_status failed: {response['error']}")
                return False

            result = response.get("result", {})
            status = result.get("status", "unknown")
            logger.info(f"Health status: {status}")

            if status != "healthy":
                logger.warning(f"Health status is '{status}', expected 'healthy'")

            logger.info("✅ get_health_status test passed")
            return True

        except Exception as e:
            logger.error(f"get_health_status test failed: {e}")
            return False

    async def test_help_system(self) -> bool:
        """Test get_help tool with different topics."""
        logger.info("Testing get_help system...")

        test_topics = ["general", "tools", "invalid_topic"]

        for topic in test_topics:
            request = {
                "jsonrpc": "2.0",
                "id": 4 + test_topics.index(topic),
                "method": "tools/call",
                "params": {"name": "get_help", "arguments": {"topic": topic}},
            }

            try:
                response = await self.send_request(request)

                if "error" in response:
                    logger.error(f"get_help('{topic}') failed: {response['error']}")
                    return False

                result = response.get("result", {})
                if topic == "invalid_topic":
                    if "error" not in result:
                        logger.error("get_help should return error for invalid topic")
                        return False
                else:
                    if "description" not in result:
                        logger.error(f"get_help('{topic}') missing description")
                        return False

                logger.info(f"✅ get_help('{topic}') test passed")

            except Exception as e:
                logger.error(f"get_help('{topic}') test failed: {e}")
                return False

        return True

    async def test_parameter_operations(self) -> bool:
        """Test avatar parameter operations."""
        logger.info("Testing parameter operations...")

        test_avatar_id = "test_avatar_123"

        # Test set_parameter
        set_request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "set_parameter",
                "arguments": {"avatar_id": test_avatar_id, "parameter": "TestParameter", "value": 0.75},
            },
        }

        try:
            response = await self.send_request(set_request)
            if "error" in response:
                logger.error(f"set_parameter failed: {response['error']}")
                return False

            logger.info("✅ set_parameter test passed")

        except Exception as e:
            logger.error(f"set_parameter test failed: {e}")
            return False

        # Test get_parameter
        get_request = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "get_parameter",
                "arguments": {"avatar_id": test_avatar_id, "parameter": "TestParameter"},
            },
        }

        try:
            response = await self.send_request(get_request)
            if "error" in response:
                logger.error(f"get_parameter failed: {response['error']}")
                return False

            logger.info("✅ get_parameter test passed")
            return True

        except Exception as e:
            logger.error(f"get_parameter test failed: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """Run all MCP interface tests."""
        logger.info("Starting MCP interface tests...")

        try:
            await self.start_server()

            tests = [
                self.test_tools_list,
                self.test_server_status,
                self.test_health_status,
                self.test_help_system,
                self.test_parameter_operations,
            ]

            passed = 0
            total = len(tests)

            for test in tests:
                if await test():
                    passed += 1
                logger.info("")  # Add spacing between tests

            logger.info(f"Test Results: {passed}/{total} tests passed")

            if passed == total:
                logger.info("🎉 All MCP interface tests passed!")
                return True
            else:
                logger.error(f"❌ {total - passed} tests failed")
                return False

        finally:
            await self.stop_server()


async def main():
    """Main test function."""
    # Command to run the MCP server
    server_command = [sys.executable, "-m", "vrchat_mcp.server"]

    # Alternative: run via CLI
    # server_command = ["vrchat-mcp", "--mode", "mcp"]

    tester = MCPTester(server_command)

    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
