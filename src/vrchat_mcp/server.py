"""
VRChat MCP Server

FastMCP 2.10+ server implementation for VRChat MCP with stdio interface.
"""

import asyncio
import json
import logging
import signal
import sys
from typing import Any, Dict, Optional, Union, List, Callable, Awaitable

from fastmcp import FastMCP, JSONRPCRequest, JSONRPCResponse, JSONRPCError
from pydantic import BaseModel, ValidationError

from . import mcp, logger
from .osc import OSCManager
from .models import (
    AvatarLoadRequest,
    AvatarParameterRequest,
    AnimationRequest,
    ExpressionRequest,
    NPCConversationRequest,
    SuccessResponse,
    ErrorResponse
)

# Type aliases
JSONRPCResult = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
JSONRPCNotification = Callable[[str, Optional[Dict[str, Any]]], Awaitable[None]]

class VRChatMCPServer:
    """VRChat MCP server implementation with JSON-RPC 2.0 over stdio."""
    
    def __init__(self):
        """Initialize the VRChat MCP server."""
        self._stop_event = asyncio.Event()
        self._notification_handlers: Dict[str, JSONRPCNotification] = {}
        self._request_handlers: Dict[str, Callable[..., Awaitable[JSONRPCResult]]] = {}
        
        # Register built-in JSON-RPC methods
        self.register_method("echo", self._handle_echo)
        
        # Initialize the OSC manager
        self.osc_manager = OSCManager()
        
        # Register VRChat MCP methods
        self.register_method("load_avatar", self._handle_load_avatar)
        self.register_method("set_parameter", self._handle_set_parameter)
        self.register_method("play_animation", self._handle_play_animation)
        self.register_method("set_expression", self._handle_set_expression)
        self.register_method("start_conversation", self._handle_start_conversation)
        
        # Track connection state
        self._is_connected = False
    
    def register_method(self, name: str, handler: Callable[..., Awaitable[JSONRPCResult]]) -> None:
        """Register a JSON-RPC method handler."""
        self._request_handlers[name] = handler
    
    def register_notification_handler(self, method: str, handler: JSONRPCNotification) -> None:
        """Register a notification handler."""
        self._notification_handlers[method] = handler
    
    async def _handle_echo(self, message: str) -> str:
        """Handle echo test method."""
        return f"Echo: {message}"
    
    async def _handle_load_avatar(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle avatar loading request."""
        try:
            # Validate request against Pydantic model
            req = AvatarLoadRequest(**request)
            
            # Log the avatar loading attempt
            logger.info(f"Loading avatar: {req.preset_name} (ID: {req.avatar_id or 'default'})")
            
            # Send the avatar load command via OSC
            if req.avatar_id:
                self.osc_manager.load_avatar(req.avatar_id)
            else:
                # If no avatar_id is provided, try using the preset_name
                # Note: This assumes preset_name can be used as an avatar ID
                self.osc_manager.load_avatar(req.preset_name)
            
            # Set any initial parameters if provided
            if req.parameters:
                for param_name, param_value in req.parameters.items():
                    self.osc_manager.send_parameter(param_name, param_value)
            
            # Return success response
            return SuccessResponse(
                message=f"Avatar '{req.preset_name}' load requested",
                data={"preset_name": req.preset_name, "avatar_id": req.avatar_id or req.preset_name}
            ).dict()
            
        except ValidationError as e:
            error_msg = f"Invalid request: {str(e)}"
            logger.error(error_msg)
            return ErrorResponse(
                error="Invalid request",
                message=error_msg,
                details={"errors": e.errors()}
            ).dict()
        except Exception as e:
            error_msg = f"Failed to load avatar: {str(e)}"
            logger.exception(error_msg)
            return ErrorResponse(
                error="Avatar load failed",
                message=error_msg,
                code=500
            ).dict()
    
    async def _handle_set_parameter(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle parameter setting request."""
        try:
            req = AvatarParameterRequest(**request)
            
            # Log the parameter setting attempt
            logger.info(f"Setting parameter '{req.parameter_name}' to {req.value}")
            
            # Send the parameter update via OSC
            self.osc_manager.send_parameter(req.parameter_name, req.value)
            
            return SuccessResponse(
                message=f"Parameter '{req.parameter_name}' set to {req.value}",
                data={"parameter_name": req.parameter_name, "value": req.value}
            ).dict()
            
        except ValidationError as e:
            return ErrorResponse(
                error="Invalid parameter request",
                message=str(e),
                details={"errors": e.errors()}
            ).dict()
        except Exception as e:
            error_msg = f"Failed to set parameter: {str(e)}"
            logger.exception(error_msg)
            return ErrorResponse(
                error="Parameter set failed",
                message=error_msg,
                code=500
            ).dict()
    
    async def _handle_play_animation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle animation play request."""
        try:
            req = AnimationRequest(**request)
            
            # TODO: Implement actual animation logic
            logger.info(f"Playing animation '{req.animation_name}' on layer {req.layer}")
            
            return SuccessResponse(
                message=f"Animation '{req.animation_name}' started",
                data={"animation_name": req.animation_name, "layer": req.layer}
            ).dict()
            
        except ValidationError as e:
            return ErrorResponse(
                error="Invalid animation request",
                message=str(e),
                details={"errors": e.errors()}
            ).dict()
    
    async def _handle_set_expression(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle expression setting request."""
        try:
            req = ExpressionRequest(**request)
            
            # TODO: Implement actual expression logic
            logger.info(f"Setting expression '{req.expression_name}' to intensity {req.intensity}")
            
            return SuccessResponse(
                message=f"Expression '{req.expression_name}' set to {req.intensity}",
                data={"expression_name": req.expression_name, "intensity": req.intensity}
            ).dict()
            
        except ValidationError as e:
            return ErrorResponse(
                error="Invalid expression request",
                message=str(e),
                details={"errors": e.errors()}
            ).dict()
    
    async def _handle_start_conversation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle NPC conversation request."""
        try:
            req = NPCConversationRequest(**request)
            
            # TODO: Implement actual conversation logic
            logger.info(f"Starting conversation with NPC {req.npc_id}: {req.message}")
            
            # Simulate a response
            response = f"Hello! This is a simulated response from NPC {req.npc_id} to: {req.message}"
            
            return SuccessResponse(
                message="Conversation started",
                data={"npc_id": req.npc_id, "response": response}
            ).dict()
            
        except ValidationError as e:
            return ErrorResponse(
                error="Invalid conversation request",
                message=str(e),
                details={"errors": e.errors()}
            ).dict()
    
    async def _handle_jsonrpc_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a single JSON-RPC request."""
        try:
            # Parse the JSON-RPC request
            jsonrpc_request = JSONRPCRequest(**request)
            
            # Check if it's a notification (no id)
            if jsonrpc_request.id is None:
                if jsonrpc_request.method in self._notification_handlers:
                    asyncio.create_task(
                        self._notification_handlers[jsonrpc_request.method](jsonrpc_request.params or {})
                    )
                return None
            
            # Handle the request
            if jsonrpc_request.method in self._request_handlers:
                try:
                    # Call the handler with the params
                    if jsonrpc_request.params is None:
                        result = await self._request_handlers[jsonrpc_request.method]()
                    elif isinstance(jsonrpc_request.params, dict):
                        result = await self._request_handlers[jsonrpc_request.method](jsonrpc_request.params)
                    elif isinstance(jsonrpc_request.params, list):
                        result = await self._request_handlers[jsonrpc_request.method](*jsonrpc_request.params)
                    else:
                        raise JSONRPCError(
                            code=-32602,
                            message="Invalid params",
                            data={"params": jsonrpc_request.params}
                        )
                    
                    # Return the successful response
                    return JSONRPCResponse(
                        id=jsonrpc_request.id,
                        result=result
                    ).dict()
                    
                except JSONRPCError as e:
                    # Return JSON-RPC error
                    return e.to_response(jsonrpc_request.id).dict()
                    
                except Exception as e:
                    # Handle unexpected errors
                    logger.exception(f"Error handling method {jsonrpc_request.method}")
                    return JSONRPCError(
                        code=-32603,
                        message="Internal error",
                        data={"error": str(e)}
                    ).to_response(jsonrpc_request.id).dict()
            else:
                # Method not found
                return JSONRPCError(
                    code=-32601,
                    message=f"Method not found: {jsonrpc_request.method}"
                ).to_response(jsonrpc_request.id).dict()
                
        except Exception as e:
            # Handle parse errors
            logger.exception("Error parsing JSON-RPC request")
            return JSONRPCError(
                code=-32700,
                message="Parse error",
                data={"error": str(e)}
            ).to_response(request.get('id') if isinstance(request, dict) else None).dict()
    
    async def _read_stdin(self) -> AsyncIterator[str]:
        """Read lines from stdin asynchronously."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        while not self._stop_event.is_set():
            try:
                # Read a line from stdin
                line = await asyncio.wait_for(reader.readline(), timeout=0.1)
                if not line:
                    break
                yield line.decode('utf-8').strip()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error reading from stdin: {e}")
                break
    
    async def run(self):
        """Run the server's main loop."""
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._stop_event.set)
        
        logger.info("VRChat MCP server starting...")
        
        # Start the OSC manager
        try:
            await self.osc_manager.start()
            self._is_connected = True
            logger.info("OSC manager started successfully")
        except Exception as e:
            logger.error(f"Failed to start OSC manager: {e}")
            self._is_connected = False
        
        try:
            # Main loop
            async for line in self._read_stdin():
                if not line.strip():
                    continue
                    
                try:
                    # Parse the JSON-RPC request
                    request = json.loads(line)
                    
                    # Handle the request
                    response = await self._handle_jsonrpc_request(request)
                    
                    # Send the response if there is one
                    if response is not None:
                        print(json.dumps(response), flush=True)
                        
                except json.JSONDecodeError as e:
                    # Handle invalid JSON
                    error_response = JSONRPCError(
                        code=-32700,
                        message="Parse error",
                        data={"error": f"Invalid JSON: {str(e)}"}
                    ).to_response(None).dict()
                    print(json.dumps(error_response), flush=True)
                    
                except Exception as e:
                    logger.exception("Unexpected error processing request")
                    error_response = JSONRPCError(
                        code=-32603,
                        message="Internal error",
                        data={"error": str(e)}
                    ).to_response(None).dict()
                    print(json.dumps(error_response), flush=True)
        
        except asyncio.CancelledError:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.exception("Fatal error in server main loop")
        finally:
            # Stop the OSC manager
            try:
                if self._is_connected:
                    await self.osc_manager.stop()
                    self._is_connected = False
            except Exception as e:
                logger.error(f"Error stopping OSC manager: {e}")
            
            logger.info("VRChat MCP server stopped")

def main():
    """Entry point for the VRChat MCP server."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    
    # Create and run the server
    server = VRChatMCPServer()
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception("Fatal error in server")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
