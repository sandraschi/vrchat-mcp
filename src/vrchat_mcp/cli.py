"""
VRChat MCP CLI Entry Point

Provides command-line interface for running the VRChat MCP server
with both MCP (stdio) and FastAPI (HTTP) interfaces.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from . import VRChatMCP, logger


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure logging for the CLI."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatters
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )

    # Setup console handler (MCP servers must use stderr, not stdout)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(numeric_level)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)


def load_config_from_file(config_file: Optional[str] = None) -> dict:
    """Load configuration from a file if specified."""
    if not config_file:
        return {}

    try:
        import json
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file {config_file}: {e}")
        return {}


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="VRChat MCP Server - Control VRChat avatars and assets via MCP protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings
  vrchat-mcp

  # Run with custom config
  vrchat-mcp --config my_config.json

  # Run with debug logging
  vrchat-mcp --log-level DEBUG

  # Run and save logs to file
  vrchat-mcp --log-file vrchat-mcp.log

  # Run MCP stdio server (default behavior)
  vrchat-mcp
        """
    )


    parser.add_argument(
        "--config",
        type=str,
        help="Path to JSON configuration file"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)"
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file (logs to console if not specified)"
    )

    # OSC Configuration
    osc_group = parser.add_argument_group("OSC Configuration")
    osc_group.add_argument(
        "--osc-client-ip",
        default="127.0.0.1",
        help="OSC client IP address (default: 127.0.0.1)"
    )
    osc_group.add_argument(
        "--osc-client-port",
        type=int,
        default=9000,
        help="OSC client port (default: 9000)"
    )
    osc_group.add_argument(
        "--osc-server-ip",
        default="127.0.0.1",
        help="OSC server IP address (default: 127.0.0.1)"
    )
    osc_group.add_argument(
        "--osc-server-port",
        type=int,
        default=9001,
        help="OSC server port (default: 9001)"
    )

    # Debug UI Configuration
    debug_group = parser.add_argument_group("Debug UI Configuration")
    debug_group.add_argument(
        "--debug-ui",
        action="store_true",
        default=True,
        help="Enable debug UI (default: enabled)"
    )
    debug_group.add_argument(
        "--no-debug-ui",
        action="store_false",
        dest="debug_ui",
        help="Disable debug UI"
    )
    debug_group.add_argument(
        "--debug-ui-host",
        default="127.0.0.1",
        help="Debug UI host (default: 127.0.0.1)"
    )
    debug_group.add_argument(
        "--debug-ui-port",
        type=int,
        default=8765,
        help="Debug UI port (default: 8765)"
    )

    return parser


async def run_mcp_mode(mcp_instance: VRChatMCP) -> None:
    """Run MCP stdio server only (like notepadpp-mcp)."""
    logger.info("Starting VRChat MCP server in MCP stdio mode")

    try:
        # Run MCP stdio server (like notepadpp-mcp)
        await mcp_instance.start()
    except Exception as e:
        logger.error(f"Failed to start MCP mode server: {e}")
        raise


async def main_async(args: argparse.Namespace) -> int:
    """Main async entry point."""
    try:
        # Load configuration from file and merge with command line args
        config = load_config_from_file(args.config)

        # Override config with command line arguments
        config.setdefault("osc", {})
        config["osc"].update({
            "client_ip": args.osc_client_ip,
            "client_port": args.osc_client_port,
            "server_ip": args.osc_server_ip,
            "server_port": args.osc_server_port,
        })

        config.setdefault("debug_ui", {})
        config["debug_ui"].update({
            "enabled": args.debug_ui,
            "host": args.debug_ui_host,
            "port": args.debug_ui_port,
        })

        config.setdefault("logging", {})
        config["logging"].update({
            "level": args.log_level,
            "file": args.log_file,
        })

        # Setup logging
        setup_logging(args.log_level, args.log_file)

        logger.info("Initializing VRChat MCP server...")

        # Create MCP instance
        mcp_instance = VRChatMCP(config)

        # Run MCP stdio server (like notepadpp-mcp)
        await run_mcp_mode(mcp_instance)

        return 0

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.exception(f"Fatal error in server: {e}")
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Run the async main function
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


