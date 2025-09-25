"""
Pydantic models for VRChat MCP requests and responses.

This module defines the data structures used for communication with the VRChat MCP server.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

# Base response models
class StatusResponse(BaseModel):
    """Base response model with status information."""
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class SuccessResponse(StatusResponse):
    """Successful operation response."""
    status: str = "success"
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(StatusResponse):
    """Error response model."""
    status: str = "error"
    error: str
    code: Optional[int] = None

# Request models
class AvatarLoadRequest(BaseModel):
    """Request model for loading a VRChat avatar."""
    preset_name: str = Field(..., description="Name of the avatar preset to load")
    avatar_id: Optional[str] = Field(None, description="Optional avatar ID for multi-avatar support")
    parameters: Optional[Dict[str, Union[bool, float, int, str]]] = Field(
        None,
        description="Initial parameters to set on the avatar"
    )

class AvatarParameterRequest(BaseModel):
    """Request model for setting avatar parameters."""
    parameter_name: str = Field(..., description="Name of the parameter to set")
    value: Union[bool, float, int, str] = Field(..., description="Value to set")
    avatar_id: Optional[str] = Field(None, description="Optional avatar ID for multi-avatar support")

class AnimationRequest(BaseModel):
    """Request model for playing animations."""
    animation_name: str = Field(..., description="Name of the animation to play")
    layer: int = Field(0, description="Animation layer")
    weight: float = Field(1.0, description="Animation weight")
    fade_duration: float = Field(0.1, description="Fade duration in seconds")
    avatar_id: Optional[str] = Field(None, description="Optional avatar ID")

class ExpressionRequest(BaseModel):
    """Request model for setting facial expressions."""
    expression_name: str = Field(..., description="Name of the expression to set")
    intensity: float = Field(1.0, description="Expression intensity (0.0 to 1.0)")
    avatar_id: Optional[str] = Field(None, description="Optional avatar ID")

class NPCConversationRequest(BaseModel):
    """Request model for NPC conversations."""
    npc_id: str = Field(..., description="ID of the NPC to converse with")
    message: str = Field(..., description="Message to send to the NPC")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the conversation")

# OSC Models
class OSCMessage(BaseModel):
    """Model for OSC messages."""
    address: str
    args: List[Union[bool, float, int, str, bytes]]

class OSCBundle(BaseModel):
    """Model for OSC bundles."""
    timestamp: Optional[float] = None
    content: List[Union[OSCMessage, 'OSCBundle']]

# Avatar State Models
class ParameterValue(BaseModel):
    """Model for parameter values with metadata."""
    name: str
    value: Union[bool, float, int, str]
    timestamp: Optional[float] = None

class AvatarState(BaseModel):
    """Model for avatar state tracking."""
    avatar_id: str
    parameters: Dict[str, Union[bool, float, int, str]] = {}
    loaded_at: Optional[float] = None

# Search Models
class SearchResult(BaseModel):
    """Model for search results."""
    id: str
    name: str
    description: Optional[str] = None
    score: float
    type: str
    metadata: Dict[str, Any] = {}

class SearchRequest(BaseModel):
    """Request model for search operations."""
    query: str
    limit: int = 10
    offset: int = 0
    filters: Optional[Dict[str, Any]] = None

# Export all models
__all__ = [
    'StatusResponse',
    'SuccessResponse',
    'ErrorResponse',
    'AvatarLoadRequest',
    'AvatarParameterRequest',
    'AnimationRequest',
    'ExpressionRequest',
    'NPCConversationRequest',
    'OSCMessage',
    'OSCBundle',
    'ParameterValue',
    'AvatarState',
    'SearchResult',
    'SearchRequest'
]