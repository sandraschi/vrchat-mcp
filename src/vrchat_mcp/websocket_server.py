"""
WebSocket Server for VRChat MCP.

This module provides a WebSocket interface for controlling and monitoring
the VRChat MCP system in real-time.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Callable, Awaitable, Set
from dataclasses import asdict
import websockets
from websockets.server import WebSocketServerProtocol

from .models import (
    AvatarLoadRequest,
    AvatarParameterRequest,
    AnimationRequest,
    ExpressionRequest,
    NPCConversationRequest,
    AvatarState,
    ConnectionStats
)
from .avatar_manager import AvatarManager

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for real-time control and monitoring of VRChat MCP."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        avatar_manager: Optional[AvatarManager] = None,
        osc_manager: Optional[Any] = None,
        auth_token: Optional[str] = None,
        rate_limit: int = 100  # Messages per minute per connection
    ):
        """Initialize the WebSocket server.
        
        Args:
            host: Host to bind the server to
            port: Port to listen on
            avatar_manager: AvatarManager instance for avatar control
            osc_manager: OSCManager instance for direct OSC access
            auth_token: Optional authentication token (if None, no auth required)
            rate_limit: Maximum messages per minute per connection
        """
        self.host = host
        self.port = port
        self.avatar_manager = avatar_manager
        self.osc_manager = osc_manager
        self.auth_token = auth_token
        self.rate_limit = rate_limit
        
        # Track connected clients
        self.clients: Set[WebSocketServerProtocol] = set()
        self.client_info: Dict[WebSocketServerProtocol, Dict[str, Any]] = {}
        
        # Message handlers by message type
        self.message_handlers: Dict[str, Callable[[Dict, WebSocketServerProtocol], Awaitable[Dict]]] = {
            "auth": self._handle_auth,
            "load_avatar": self._handle_load_avatar,
            "set_parameter": self._handle_set_parameter,
            "set_parameters": self._handle_set_parameters,
            "play_animation": self._handle_play_animation,
            "set_expression": self._handle_set_expression,
            "load_preset": self._handle_load_preset,
            "save_preset": self._handle_save_preset,
            "delete_preset": self._handle_delete_preset,
            "list_presets": self._handle_list_presets,
            "get_avatar_state": self._handle_get_avatar_state,
            "get_connection_stats": self._handle_get_connection_stats,
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            "ping": self._handle_ping
        }
        
        # Subscriptions by client
        self.subscriptions: Dict[WebSocketServerProtocol, Set[str]] = {}
        
        # Event types that can be subscribed to
        self.valid_subscriptions = {
            "avatar_changed",
            "parameter_updated",
            "animation_played",
            "expression_set",
            "preset_loaded",
            "preset_saved",
            "preset_deleted",
            "error_occurred"
        }
        
        # Start the server
        self.server: Optional[asyncio.Server] = None
        self.server_task: Optional[asyncio.Task] = None
    
    # === Server Lifecycle ===
    
    async def start(self) -> None:
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5,
            max_size=10 * 1024 * 1024  # 10MB max message size
        )
        logger.info(f"WebSocket server started on {self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")
    
    # === Connection Handling ===
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle a new WebSocket connection."""
        # Generate a unique client ID
        client_id = str(uuid.uuid4())
        client_info = {
            'id': client_id,
            'authenticated': not bool(self.auth_token),  # Auto-authenticate if no auth token is set
            'connected_at': asyncio.get_event_loop().time(),
            'message_count': 0,
            'last_message_time': 0,
            'rate_limited_until': 0,
            'remote': f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        }
        
        # Add to client tracking
        self.clients.add(websocket)
        self.client_info[websocket] = client_info
        self.subscriptions[websocket] = set()
        
        logger.info(f"New WebSocket connection from {client_info['remote']} (ID: {client_id})")
        
        try:
            # Send welcome message
            await self._send_message(websocket, {
                'type': 'welcome',
                'client_id': client_id,
                'requires_auth': bool(self.auth_token),
                'server': 'VRChat MCP',
                'version': '1.0.0',
                'timestamp': asyncio.get_event_loop().time()
            })
            
            # Handle messages
            async for message in websocket:
                try:
                    await self._handle_message(websocket, message)
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
                    await self._send_error(websocket, "internal_error", str(e))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed by client {client_id}")
        except Exception as e:
            logger.error(f"WebSocket error for client {client_id}: {e}", exc_info=True)
        finally:
            # Clean up
            if websocket in self.clients:
                self.clients.remove(websocket)
            if websocket in self.client_info:
                del self.client_info[websocket]
            if websocket in self.subscriptions:
                del self.subscriptions[websocket]
            
            logger.info(f"Client {client_id} disconnected")
    
    async def _handle_message(self, websocket: WebSocketServerProtocol, message: str) -> None:
        """Handle an incoming WebSocket message."""
        client_info = self.client_info.get(websocket)
        if not client_info:
            return
        
        # Check rate limiting
        current_time = asyncio.get_event_loop().time()
        if current_time < client_info['rate_limited_until']:
            await self._send_error(websocket, "rate_limit_exceeded", "Rate limit exceeded")
            return
        
        # Update message count and timestamp
        client_info['message_count'] += 1
        client_info['last_message_time'] = current_time
        
        # Parse message
        try:
            data = json.loads(message)
            if not isinstance(data, dict) or 'type' not in data:
                raise ValueError("Invalid message format")
            
            message_type = data['type']
            
            # Check authentication for non-auth messages
            if message_type != 'auth' and not client_info['authenticated']:
                await self._send_error(websocket, "not_authenticated", "Authentication required")
                return
            
            # Find and call the appropriate handler
            if message_type in self.message_handlers:
                response = await self.message_handlers[message_type](data, websocket)
                if response:
                    await self._send_message(websocket, response)
            else:
                await self._send_error(websocket, "unknown_message_type", f"Unknown message type: {message_type}")
        
        except json.JSONDecodeError:
            await self._send_error(websocket, "invalid_json", "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self._send_error(websocket, "processing_error", str(e))
    
    # === Message Handlers ===
    
    async def _handle_auth(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle authentication."""
        if not self.auth_token:
            return {
                'type': 'auth_response',
                'authenticated': True,
                'message': 'Authentication not required'
            }
        
        token = data.get('token')
        if token == self.auth_token:
            self.client_info[websocket]['authenticated'] = True
            return {
                'type': 'auth_response',
                'authenticated': True,
                'message': 'Authentication successful'
            }
        else:
            return {
                'type': 'auth_response',
                'authenticated': False,
                'error': 'invalid_token',
                'message': 'Invalid authentication token'
            }
    
    async def _handle_load_avatar(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle load_avatar command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            request = AvatarLoadRequest(
                avatar_id=data['avatar_id'],
                parameters=data.get('parameters', {})
            )
            
            success = await self.avatar_manager.load_avatar(request)
            
            return {
                'type': 'load_avatar_response',
                'success': success,
                'avatar_id': request.avatar_id
            }
        except KeyError as e:
            return {
                'type': 'error',
                'code': 'missing_field',
                'field': str(e),
                'message': f'Missing required field: {e}'
            }
        except Exception as e:
            logger.error(f"Error loading avatar: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'load_failed',
                'message': f'Failed to load avatar: {str(e)}'
            }
    
    async def _handle_set_parameter(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle set_parameter command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            request = AvatarParameterRequest(
                name=data['name'],
                value=data['value'],
                parameter_type=data.get('type'),
                immediate=data.get('immediate', True)
            )
            
            # Get the current avatar ID
            current_avatar = self.avatar_manager.current_avatar
            if not current_avatar:
                return {
                    'type': 'error',
                    'code': 'no_avatar_loaded',
                    'message': 'No avatar is currently loaded'
                }
            
            await self.avatar_manager.set_parameter(
                current_avatar,
                request.name,
                request.value,
                immediate=request.immediate
            )
            
            return {
                'type': 'set_parameter_response',
                'success': True,
                'parameter': request.name,
                'value': request.value
            }
        except KeyError as e:
            return {
                'type': 'error',
                'code': 'missing_field',
                'field': str(e),
                'message': f'Missing required field: {e}'
            }
        except Exception as e:
            logger.error(f"Error setting parameter: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'set_parameter_failed',
                'message': f'Failed to set parameter: {str(e)}'
            }
    
    async def _handle_set_parameters(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle set_parameters command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            parameters = data['parameters']
            immediate = data.get('immediate', True)
            
            # Get the current avatar ID
            current_avatar = self.avatar_manager.current_avatar
            if not current_avatar:
                return {
                    'type': 'error',
                    'code': 'no_avatar_loaded',
                    'message': 'No avatar is currently loaded'
                }
            
            await self.avatar_manager.set_parameters(
                current_avatar,
                parameters,
                immediate=immediate
            )
            
            return {
                'type': 'set_parameters_response',
                'success': True,
                'parameters_updated': len(parameters)
            }
        except KeyError as e:
            return {
                'type': 'error',
                'code': 'missing_field',
                'field': str(e),
                'message': f'Missing required field: {e}'
            }
        except Exception as e:
            logger.error(f"Error setting parameters: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'set_parameters_failed',
                'message': f'Failed to set parameters: {str(e)}'
            }
    
    async def _handle_play_animation(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle play_animation command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            request = AnimationRequest(
                name=data['name'],
                layer=data.get('layer', 0),
                fade_duration=data.get('fade_duration', 0.1),
                weight=data.get('weight', 1.0),
                speed=data.get('speed', 1.0),
                time_offset=data.get('time_offset', 0.0),
                parameters=data.get('parameters', {})
            )
            
            # Get the current avatar ID
            current_avatar = self.avatar_manager.current_avatar
            if not current_avatar:
                return {
                    'type': 'error',
                    'code': 'no_avatar_loaded',
                    'message': 'No avatar is currently loaded'
                }
            
            await self.avatar_manager.play_animation(current_avatar, request)
            
            return {
                'type': 'play_animation_response',
                'success': True,
                'animation': request.name
            }
        except KeyError as e:
            return {
                'type': 'error',
                'code': 'missing_field',
                'field': str(e),
                'message': f'Missing required field: {e}'
            }
        except Exception as e:
            logger.error(f"Error playing animation: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'play_animation_failed',
                'message': f'Failed to play animation: {str(e)}'
            }
    
    async def _handle_set_expression(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle set_expression command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            request = ExpressionRequest(
                name=data['name'],
                value=data.get('value', True),
                expression_type=data.get('type'),
                blend_duration=data.get('blend_duration', 0.1)
            )
            
            # Get the current avatar ID
            current_avatar = self.avatar_manager.current_avatar
            if not current_avatar:
                return {
                    'type': 'error',
                    'code': 'no_avatar_loaded',
                    'message': 'No avatar is currently loaded'
                }
            
            await self.avatar_manager.set_expression(current_avatar, request)
            
            return {
                'type': 'set_expression_response',
                'success': True,
                'expression': request.name,
                'value': request.value
            }
        except KeyError as e:
            return {
                'type': 'error',
                'code': 'missing_field',
                'field': str(e),
                'message': f'Missing required field: {e}'
            }
        except Exception as e:
            logger.error(f"Error setting expression: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'set_expression_failed',
                'message': f'Failed to set expression: {str(e)}'
            }
    
    async def _handle_load_preset(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle load_preset command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            preset_name = data['name']
            success = await self.avatar_manager.load_preset(preset_name)
            
            if not success:
                return {
                    'type': 'error',
                    'code': 'preset_not_found',
                    'message': f'Preset not found: {preset_name}'
                }
            
            return {
                'type': 'load_preset_response',
                'success': True,
                'preset': preset_name
            }
        except KeyError as e:
            return {
                'type': 'error',
                'code': 'missing_field',
                'field': str(e),
                'message': f'Missing required field: {e}'
            }
        except Exception as e:
            logger.error(f"Error loading preset: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'load_preset_failed',
                'message': f'Failed to load preset: {str(e)}'
            }
    
    async def _handle_save_preset(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle save_preset command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            preset_name = data['name']
            preset = await self.avatar_manager.save_avatar_state(preset_name)
            
            if not preset:
                return {
                    'type': 'error',
                    'code': 'save_preset_failed',
                    'message': 'Failed to save preset'
                }
            
            return {
                'type': 'save_preset_response',
                'success': True,
                'preset': preset_name,
                'avatar_id': preset.avatar_id
            }
        except KeyError as e:
            return {
                'type': 'error',
                'code': 'missing_field',
                'field': str(e),
                'message': f'Missing required field: {e}'
            }
        except Exception as e:
            logger.error(f"Error saving preset: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'save_preset_failed',
                'message': f'Failed to save preset: {str(e)}'
            }
    
    async def _handle_delete_preset(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle delete_preset command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            preset_name = data['name']
            success = self.avatar_manager.delete_preset(preset_name)
            
            if not success:
                return {
                    'type': 'error',
                    'code': 'preset_not_found',
                    'message': f'Preset not found: {preset_name}'
                }
            
            return {
                'type': 'delete_preset_response',
                'success': True,
                'preset': preset_name
            }
        except KeyError as e:
            return {
                'type': 'error',
                'code': 'missing_field',
                'field': str(e),
                'message': f'Missing required field: {e}'
            }
        except Exception as e:
            logger.error(f"Error deleting preset: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'delete_preset_failed',
                'message': f'Failed to delete preset: {str(e)}'
            }
    
    async def _handle_list_presets(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle list_presets command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            query = data.get('query', '')
            if query:
                presets = self.avatar_manager.search_presets(query)
            else:
                preset_names = self.avatar_manager.list_presets()
                presets = [self.avatar_manager.get_preset(name) for name in preset_names]
                presets = [p for p in presets if p is not None]
            
            return {
                'type': 'list_presets_response',
                'presets': [p.to_dict() for p in presets]
            }
        except Exception as e:
            logger.error(f"Error listing presets: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'list_presets_failed',
                'message': f'Failed to list presets: {str(e)}'
            }
    
    async def _handle_get_avatar_state(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle get_avatar_state command."""
        if not self.avatar_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'Avatar management is not available'
            }
        
        try:
            avatar_id = data.get('avatar_id')
            if not avatar_id:
                # Get the current avatar
                avatar_id = self.avatar_manager.current_avatar
                if not avatar_id:
                    return {
                        'type': 'error',
                        'code': 'no_avatar_loaded',
                        'message': 'No avatar is currently loaded'
                    }
            
            state = await self.avatar_manager.get_avatar_state(avatar_id)
            if not state:
                return {
                    'type': 'error',
                    'code': 'avatar_not_found',
                    'message': f'Avatar not found: {avatar_id}'
                }
            
            return {
                'type': 'avatar_state',
                'avatar_id': avatar_id,
                'state': state.to_dict()
            }
        except Exception as e:
            logger.error(f"Error getting avatar state: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'get_avatar_state_failed',
                'message': f'Failed to get avatar state: {str(e)}'
            }
    
    async def _handle_get_connection_stats(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle get_connection_stats command."""
        if not self.osc_manager:
            return {
                'type': 'error',
                'code': 'not_available',
                'message': 'OSC management is not available'
            }
        
        try:
            stats = self.osc_manager.get_connection_stats()
            return {
                'type': 'connection_stats',
                'stats': stats.to_dict()
            }
        except Exception as e:
            logger.error(f"Error getting connection stats: {e}", exc_info=True)
            return {
                'type': 'error',
                'code': 'get_connection_stats_failed',
                'message': f'Failed to get connection stats: {str(e)}'
            }
    
    async def _handle_subscribe(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle subscribe command."""
        event_type = data.get('event_type')
        if not event_type:
            return {
                'type': 'error',
                'code': 'missing_field',
                'field': 'event_type',
                'message': 'Missing required field: event_type',
                'valid_event_types': list(self.valid_subscriptions)
            }
        
        if event_type not in self.valid_subscriptions:
            return {
                'type': 'error',
                'code': 'invalid_event_type',
                'event_type': event_type,
                'message': f'Invalid event type: {event_type}',
                'valid_event_types': list(self.valid_subscriptions)
            }
        
        self.subscriptions[websocket].add(event_type)
        
        return {
            'type': 'subscribe_response',
            'success': True,
            'event_type': event_type,
            'subscribed': list(self.subscriptions[websocket])
        }
    
    async def _handle_unsubscribe(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle unsubscribe command."""
        event_type = data.get('event_type')
        
        if not event_type:
            # Unsubscribe from all events
            self.subscriptions[websocket].clear()
            return {
                'type': 'unsubscribe_response',
                'success': True,
                'unsubscribed_from': 'all',
                'remaining_subscriptions': []
            }
        
        if event_type in self.subscriptions[websocket]:
            self.subscriptions[websocket].remove(event_type)
        
        return {
            'type': 'unsubscribe_response',
            'success': True,
            'event_type': event_type,
            'remaining_subscriptions': list(self.subscriptions[websocket])
        }
    
    async def _handle_ping(self, data: Dict, websocket: WebSocketServerProtocol) -> Dict:
        """Handle ping command."""
        return {
            'type': 'pong',
            'timestamp': asyncio.get_event_loop().time(),
            'client_id': self.client_info[websocket]['id'] if websocket in self.client_info else 'unknown'
        }
    
    # === Event Broadcasting ===
    
    async def broadcast_event(self, event_type: str, data: Dict) -> None:
        """Broadcast an event to all subscribed clients."""
        if not self.clients:
            return
        
        message = {
            'type': 'event',
            'event_type': event_type,
            'timestamp': asyncio.get_event_loop().time(),
            'data': data
        }
        
        # Send to all subscribed clients
        for websocket in list(self.clients):
            if websocket in self.subscriptions and event_type in self.subscriptions[websocket]:
                try:
                    await self._send_message(websocket, message)
                except Exception as e:
                    logger.error(f"Error sending event to client: {e}", exc_info=True)
    
    # === Utility Methods ===
    
    async def _send_message(self, websocket: WebSocketServerProtocol, message: Dict) -> None:
        """Send a JSON message to a WebSocket client."""
        try:
            await websocket.send(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
    
    async def _send_error(
        self, 
        websocket: WebSocketServerProtocol, 
        code: str, 
        message: str, 
        details: Optional[Dict] = None
    ) -> None:
        """Send an error message to a WebSocket client."""
        error = {
            'type': 'error',
            'code': code,
            'message': message
        }
        
        if details:
            error['details'] = details
        
        await self._send_message(websocket, error)
    
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self.clients)
    
    def get_connected_clients(self) -> List[Dict]:
        """Get information about connected clients."""
        return [
            {
                'id': info['id'],
                'remote': info['remote'],
                'connected_at': info['connected_at'],
                'message_count': info['message_count'],
                'subscriptions': list(self.subscriptions.get(ws, []))
            }
            for ws, info in self.client_info.items()
            if ws in self.clients
        ]
