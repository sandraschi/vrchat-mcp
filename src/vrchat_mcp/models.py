"""
Data models for VRChat MCP.

This module defines the data structures used throughout the VRChat MCP system.
"""

from typing import Dict, List, Optional, Any, Union, Literal, Tuple, TypedDict
from enum import Enum, auto
from dataclasses import dataclass, field, asdict, fields
from datetime import datetime
import json
from abc import ABC, abstractmethod

class ParameterValue:
    """Represents a parameter value with type information and metadata."""
    
    def __init__(self, value: Any, value_type: str = None, timestamp: float = None):
        """Initialize a parameter value.
        
        Args:
            value: The parameter value
            value_type: Optional type of the value ('int', 'float', 'bool', 'trigger')
            timestamp: Optional timestamp of when the value was set
        """
        self.value = value
        self.value_type = value_type or self._infer_type(value)
        self.timestamp = timestamp or datetime.now().timestamp()
    
    def _infer_type(self, value: Any) -> str:
        """Infer the parameter type from the value."""
        if isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif value is None:
            return 'trigger'
        return 'string'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary."""
        return {
            'value': self.value,
            'type': self.value_type,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterValue':
        """Create from a dictionary."""
        return cls(
            value=data.get('value'),
            value_type=data.get('type'),
            timestamp=data.get('timestamp')
        )
    
    def __eq__(self, other):
        if not isinstance(other, ParameterValue):
            return False
        return (
            self.value == other.value and 
            self.value_type == other.value_type
        )
    
    def __repr__(self):
        return f"ParameterValue(value={self.value!r}, type='{self.value_type}')"

class InterpolationState:
    """Represents the state of a parameter interpolation."""
    
    def __init__(
        self,
        parameter: str,
        start_value: float,
        target_value: float,
        duration: float,
        start_time: float = None,
        easing: str = 'linear',
        group_id: str = None
    ):
        self.parameter = parameter
        self.start_value = start_value
        self.target_value = target_value
        self.duration = duration
        self.start_time = start_time or time.time()
        self.easing = easing
        self.group_id = group_id
        self._progress = 0.0
    
    @property
    def progress(self) -> float:
        """Get the current progress of the interpolation (0.0 to 1.0)."""
        return min(1.0, (time.time() - self.start_time) / self.duration)
    
    @property
    def is_complete(self) -> bool:
        """Check if the interpolation is complete."""
        return self.progress >= 1.0
    
    def get_current_value(self) -> float:
        """Get the current interpolated value."""
        if self.is_complete:
            return self.target_value
            
        # Apply easing function
        t = self.progress
        if self.easing == 'linear':
            return self.start_value + (self.target_value - self.start_value) * t
        elif self.easing == 'ease_in':
            return self.start_value + (self.target_value - self.start_value) * (t * t)
        elif self.easing == 'ease_out':
            t = 1 - (1 - t) * (1 - t)
            return self.start_value + (self.target_value - self.start_value) * t
        elif self.easing == 'ease_in_out':
            t = t * t * (3 - 2 * t)
            return self.start_value + (self.target_value - self.start_value) * t
        else:
            # Default to linear
            return self.start_value + (self.target_value - self.start_value) * t
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary."""
        return {
            'parameter': self.parameter,
            'start_value': self.start_value,
            'target_value': self.target_value,
            'current_value': self.get_current_value(),
            'duration': self.duration,
            'elapsed': time.time() - self.start_time,
            'progress': self.progress,
            'easing': self.easing,
            'group_id': self.group_id,
            'is_complete': self.is_complete
        }

class MessageDirection(Enum):
    """Direction of an OSC message."""
    INCOMING = "incoming"
    OUTGOING = "outgoing"

@dataclass
class MessageRecord:
    """Record of an OSC message for debugging and inspection."""
    address: str
    args: List[Any]
    direction: MessageDirection
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary."""
        return {
            'address': self.address,
            'args': self.args,
            'direction': self.direction.value,
            'timestamp': self.timestamp,
            'time': datetime.fromtimestamp(self.timestamp).isoformat()
        }

class AvatarParameterType(Enum):
    """Types of avatar parameters in VRChat."""
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    TRIGGER = "trigger"

@dataclass
class AvatarLoadRequest:
    """Request to load a specific avatar with optional parameters."""
    avatar_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher priority requests will be processed first
    timeout: Optional[float] = None  # Seconds to wait for avatar to load
    
    def to_dict(self) -> dict:
        """Convert the request to a dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AvatarLoadRequest':
        """Create a request from a dictionary."""
        return cls(**data)

@dataclass
class AvatarParameterRequest:
    """Request to set an avatar parameter."""
    name: str
    value: Union[int, float, bool]
    parameter_type: Optional[AvatarParameterType] = None
    immediate: bool = True  # Whether to send the update immediately
    
    def __post_init__(self):
        """Set the parameter type based on the value if not specified."""
        if self.parameter_type is None:
            if isinstance(self.value, bool):
                self.parameter_type = AvatarParameterType.BOOL
            elif isinstance(self.value, int):
                self.parameter_type = AvatarParameterType.INT
            elif isinstance(self.value, float):
                self.parameter_type = AvatarParameterType.FLOAT
    
    def to_dict(self) -> dict:
        """Convert the request to a dictionary."""
        data = asdict(self)
        if self.parameter_type is not None:
            data['parameter_type'] = self.parameter_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AvatarParameterRequest':
        """Create a request from a dictionary."""
        if 'parameter_type' in data and data['parameter_type'] is not None:
            data['parameter_type'] = AvatarParameterType(data['parameter_type'])
        return cls(**data)

@dataclass
class AnimationRequest:
    """Request to play an animation."""
    name: str
    layer: int = 0
    fade_duration: float = 0.1
    weight: float = 1.0
    speed: float = 1.0
    time_offset: float = 0.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert the request to a dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AnimationRequest':
        """Create a request from a dictionary."""
        return cls(**data)

class ExpressionType(Enum):
    """Types of expressions in VRChat."""
    BOOL = "bool"
    FLOAT = "float"
    INT = "int"
    TRIGGER = "trigger"

@dataclass
class ExpressionRequest:
    """Request to set an expression."""
    name: str
    value: Union[bool, float, int, str, None] = None
    expression_type: Optional[ExpressionType] = None
    blend_duration: float = 0.1
    
    def __post_init__(self):
        """Set the expression type based on the value if not specified."""
        if self.expression_type is None and self.value is not None:
            if isinstance(self.value, bool):
                self.expression_type = ExpressionType.BOOL
            elif isinstance(self.value, int):
                self.expression_type = ExpressionType.INT
            elif isinstance(self.value, float):
                self.expression_type = ExpressionType.FLOAT
            elif isinstance(self.value, str) and self.value.lower() == 'trigger':
                self.expression_type = ExpressionType.TRIGGER
    
    def to_dict(self) -> dict:
        """Convert the request to a dictionary."""
        data = asdict(self)
        if self.expression_type is not None:
            data['expression_type'] = self.expression_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ExpressionRequest':
        """Create a request from a dictionary."""
        if 'expression_type' in data and data['expression_type'] is not None:
            data['expression_type'] = ExpressionType(data['expression_type'])
        return cls(**data)

@dataclass
class NPCConversationRequest:
    """Request to start or update an NPC conversation."""
    conversation_id: str
    message: Optional[str] = None
    choices: List[Dict[str, str]] = field(default_factory=list)  # List of {text: string, value: string}
    timeout: Optional[float] = None  # Seconds before the conversation times out
    
    def to_dict(self) -> dict:
        """Convert the request to a dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NPCConversationRequest':
        """Create a request from a dictionary."""
        return cls(**data)

@dataclass
class OSCMessage:
    """A generic OSC message."""
    address: str
    args: List[Any] = field(default_factory=list)
    
    def to_osc_format(self) -> tuple:
        """Convert to the format expected by python-osc."""
        return (self.address, *self.args)
    
    @classmethod
    def from_osc_format(cls, address: str, *args) -> 'OSCMessage':
        """Create from python-osc format."""
        return cls(address=address, args=list(args))

@dataclass
class AvatarState:
    """Represents the state of an avatar."""
    avatar_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    active_animations: List[Dict[str, Any]] = field(default_factory=list)
    active_expressions: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def to_dict(self) -> dict:
        """Convert the state to a dictionary."""
        return {
            'avatar_id': self.avatar_id,
            'parameters': self.parameters,
            'active_animations': self.active_animations,
            'active_expressions': self.active_expressions,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AvatarState':
        """Create a state from a dictionary."""
        return cls(**data)

@dataclass
class ConnectionStats:
    """Statistics about the OSC connection."""
    messages_sent: int = 0
    messages_received: int = 0
    last_message_sent: Optional[float] = None
    last_message_received: Optional[float] = None
    errors: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert the stats to a dictionary."""
        return asdict(self)
    
    def record_message_sent(self):
        """Record that a message was sent."""
        self.messages_sent += 1
        self.last_message_sent = datetime.now().timestamp()
    
    def record_message_received(self):
        """Record that a message was received."""
        self.messages_received += 1
        self.last_message_received = datetime.now().timestamp()
    
    def record_error(self, error: str):
        """Record an error."""
        self.errors += 1
        self.last_error = error
        self.last_error_time = datetime.now().timestamp()

# Type aliases for better type hints
OSCAddress = str
OSCHandler = callable
ParameterMap = Dict[str, Any]
AnimationMap = Dict[str, AnimationRequest]
ExpressionMap = Dict[str, ExpressionRequest]
