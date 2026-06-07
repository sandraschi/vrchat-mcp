"""
Avatar Management Plugin for VRChat MCP.

Provides tools for managing avatars, parameters, and animations.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from ..models import AvatarState, MessageDirection, MessageRecord
from ..plugins import Plugin, event_listener, tool

logger = logging.getLogger(__name__)


@dataclass
class AvatarPreset:
    """Represents a saved avatar preset."""

    name: str
    parameters: dict[str, Any]
    animations: list[dict[str, Any]] = field(default_factory=list)
    expressions: list[dict[str, Any]] = field(default_factory=list)


class AvatarPlugin(Plugin):
    """Plugin for managing avatars, parameters, and animations."""

    def __init__(self):
        self.avatars: dict[str, AvatarState] = {}
        self.presets: dict[str, AvatarPreset] = {}
        self.parameter_history: dict[str, list[dict[str, Any]]] = {}

        # Default presets for common avatar setups
        self._load_default_presets()

    @property
    def name(self) -> str:
        return "avatar_manager"

    @property
    def description(self) -> str:
        return "Manages avatars, parameters, and animations"

    async def on_load(self, mcp):
        """Initialize the plugin with the MCP instance."""
        self.mcp = mcp
        logger.info("Avatar plugin loaded")

    def _load_default_presets(self) -> None:
        """Load default avatar presets."""
        default_presets = {
            "reset": AvatarPreset(
                name="reset",
                parameters={
                    "Viseme": 0.0,
                    "GestureLeft": 0.0,
                    "GestureRight": 0.0,
                    "GestureLeftWeight": 0.0,
                    "GestureRightWeight": 0.0,
                    "VRMode": 1.0,
                    "MouthOpen": 0.0,
                    "MouthSmile": 0.0,
                    "EyesClosed": 0.0,
                    "EyesLookDown": 0.0,
                    "EyesLookLeft": 0.0,
                    "EyesLookRight": 0.0,
                    "EyesLookUp": 0.0,
                },
            ),
            "tpose": AvatarPreset(
                name="tpose",
                parameters={
                    "GestureLeft": 7.0,  # Fist
                    "GestureRight": 7.0,  # Fist
                    "GestureLeftWeight": 1.0,
                    "GestureRightWeight": 1.0,
                },
            ),
        }

        for preset in default_presets.values():
            self.presets[preset.name] = preset

    @tool(
        name="set_avatar_parameter",
        description="Set a parameter value for an avatar",
        category="Avatar",
        args={
            "avatar_id": {"type": "string", "description": "ID of the avatar"},
            "parameter": {"type": "string", "description": "Name of the parameter"},
            "value": {"type": "number|boolean", "description": "Value to set"},
            "interpolate": {"type": "boolean", "description": "Whether to interpolate to the value", "default": False},
            "duration": {"type": "number", "description": "Duration of interpolation in seconds", "default": 0.5},
            "easing": {"type": "string", "description": "Easing function to use", "default": "linear"},
        },
        returns={"success": "boolean", "message": "string"},
        examples=[
            {"description": "Set a parameter directly", "code": "set_avatar_parameter('avatar1', 'Viseme', 0.5)"},
            {
                "description": "Interpolate a parameter",
                "code": (
                    "set_avatar_parameter('avatar1', 'Viseme', 1.0, "
                    "interpolate=True, duration=1.0, easing='ease_in_out')"
                ),
            },
        ],
    )
    async def set_avatar_parameter(
        self,
        avatar_id: str,
        parameter: str,
        value: float | bool | int,
        interpolate: bool = False,
        duration: float = 0.5,
        easing: str = "linear",
    ) -> dict[str, Any]:
        """Set a parameter value for an avatar with optional interpolation."""
        try:
            # Get or create avatar state
            if avatar_id not in self.avatars:
                self.avatars[avatar_id] = AvatarState(avatar_id=avatar_id)

            # Update parameter
            if interpolate and hasattr(self.mcp, "interpolation"):
                current_value = self.avatars[avatar_id].parameters.get(parameter, 0.0)
                await self.mcp.interpolation.start_interpolation(
                    f"{avatar_id}:{parameter}", current_value, float(value), duration, easing
                )
            else:
                self.avatars[avatar_id].parameters[parameter] = value

                # Send OSC message
                if hasattr(self.mcp, "osc_inspector"):
                    await self.mcp.osc_inspector.send_message(f"/avatar/parameters/{parameter}", value)

            # Log parameter change
            if parameter not in self.parameter_history:
                self.parameter_history[parameter] = []

            self.parameter_history[parameter].append(
                {
                    "avatar_id": avatar_id,
                    "value": value,
                    "timestamp": asyncio.get_event_loop().time(),
                    "interpolated": interpolate,
                }
            )

            # Keep only the last 1000 entries per parameter
            if len(self.parameter_history[parameter]) > 1000:
                self.parameter_history[parameter] = self.parameter_history[parameter][-1000:]

            return {"success": True, "message": f"Set {parameter} to {value}"}
        except Exception as e:
            logger.error(f"Error setting avatar parameter: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    @tool(
        name="get_avatar_parameter",
        description="Get a parameter value for an avatar",
        category="Avatar",
        args={
            "avatar_id": {"type": "string", "description": "ID of the avatar"},
            "parameter": {"type": "string", "description": "Name of the parameter"},
        },
        returns={"value": "number|boolean", "exists": "boolean"},
        examples=[{"description": "Get a parameter value", "code": "get_avatar_parameter('avatar1', 'Viseme')"}],
    )
    async def get_avatar_parameter(self, avatar_id: str, parameter: str) -> dict[str, Any]:
        """Get a parameter value for an avatar."""
        if avatar_id not in self.avatars or parameter not in self.avatars[avatar_id].parameters:
            return {"value": None, "exists": False}

        return {"value": self.avatars[avatar_id].parameters[parameter], "exists": True}

    @tool(
        name="apply_avatar_preset",
        description="Apply a saved preset to an avatar",
        category="Avatar",
        args={
            "avatar_id": {"type": "string", "description": "ID of the avatar"},
            "preset_name": {"type": "string", "description": "Name of the preset to apply"},
            "interpolate": {"type": "boolean", "description": "Whether to interpolate parameters", "default": False},
            "duration": {"type": "number", "description": "Duration of interpolation in seconds", "default": 0.5},
        },
        returns={"success": "boolean", "message": "string"},
        examples=[
            {"description": "Apply a preset", "code": "apply_avatar_preset('avatar1', 'reset')"},
            {
                "description": "Apply with interpolation",
                "code": "apply_avatar_preset('avatar1', 'tpose', interpolate=True, duration=1.0)",
            },
        ],
    )
    async def apply_avatar_preset(
        self, avatar_id: str, preset_name: str, interpolate: bool = False, duration: float = 0.5
    ) -> dict[str, Any]:
        """Apply a saved preset to an avatar."""
        if preset_name not in self.presets:
            return {"success": False, "message": f"Preset '{preset_name}' not found"}

        preset = self.presets[preset_name]

        # Apply all parameters in the preset
        for param_name, value in preset.parameters.items():
            await self.set_avatar_parameter(avatar_id, param_name, value, interpolate=interpolate, duration=duration)

        return {"success": True, "message": f"Applied preset '{preset_name}' to avatar '{avatar_id}'"}

    @tool(
        name="save_avatar_preset",
        description="Save the current avatar state as a preset",
        category="Avatar",
        args={
            "preset_name": {"type": "string", "description": "Name for the new preset"},
            "avatar_id": {"type": "string", "description": "ID of the avatar to save", "default": None},
            "include_parameters": {"type": "boolean", "description": "Whether to include parameters", "default": True},
            "include_animations": {"type": "boolean", "description": "Whether to include animations", "default": False},
            "include_expressions": {
                "type": "boolean",
                "description": "Whether to include expressions",
                "default": False,
            },
        },
        returns={"success": "boolean", "message": "string"},
        examples=[{"description": "Save current state as a preset", "code": "save_avatar_preset('my_preset')"}],
    )
    async def save_avatar_preset(
        self,
        preset_name: str,
        avatar_id: str | None = None,
        include_parameters: bool = True,
        include_animations: bool = False,
        include_expressions: bool = False,
    ) -> dict[str, Any]:
        """Save the current avatar state as a preset."""
        if not avatar_id and not self.avatars:
            return {"success": False, "message": "No avatar ID provided and no avatars found"}

        if not avatar_id:
            avatar_id = next(iter(self.avatars.keys()))

        if avatar_id not in self.avatars:
            return {"success": False, "message": f"Avatar '{avatar_id}' not found"}

        avatar = self.avatars[avatar_id]

        # Create new preset
        preset = AvatarPreset(
            name=preset_name,
            parameters=avatar.parameters.copy() if include_parameters else {},
            animations=avatar.active_animations.copy() if include_animations else [],
            expressions=avatar.active_expressions.copy() if include_expressions else [],
        )

        self.presets[preset_name] = preset
        return {"success": True, "message": f"Saved preset '{preset_name}'"}

    @event_listener("osc_message_received")
    async def on_osc_message(self, message: MessageRecord) -> None:
        """Handle incoming OSC messages."""
        if message.direction != MessageDirection.INCOMING:
            return

        # Check if this is a parameter update
        if message.address.startswith("/avatar/parameters/"):
            param_name = message.address.split("/")[-1]
            if not message.args:
                return

            # Update the parameter in our state
            avatar_id = "default"  # In a real implementation, we'd track which avatar is active
            if avatar_id not in self.avatars:
                self.avatars[avatar_id] = AvatarState(avatar_id=avatar_id)

            self.avatars[avatar_id].parameters[param_name] = message.args[0]

            # Log parameter change
            if param_name not in self.parameter_history:
                self.parameter_history[param_name] = []

            self.parameter_history[param_name].append(
                {
                    "avatar_id": avatar_id,
                    "value": message.args[0],
                    "timestamp": asyncio.get_event_loop().time(),
                    "interpolated": False,
                }
            )

            # Keep only the last 1000 entries per parameter
            if len(self.parameter_history[param_name]) > 1000:
                self.parameter_history[param_name] = self.parameter_history[param_name][-1000:]

    @tool(
        name="get_parameter_history",
        description="Get history of parameter changes",
        category="Debug",
        args={
            "parameter": {"type": "string", "description": "Name of the parameter"},
            "limit": {"type": "number", "description": "Maximum number of entries to return", "default": 100},
        },
        returns={"history": "list[dict]", "parameter": "string"},
        examples=[{"description": "Get parameter history", "code": "get_parameter_history('Viseme', limit=50)"}],
    )
    async def get_parameter_history(self, parameter: str, limit: int = 100) -> dict[str, Any]:
        """Get history of parameter changes."""
        if parameter not in self.parameter_history:
            return {"parameter": parameter, "history": []}

        return {"parameter": parameter, "history": self.parameter_history[parameter][-limit:]}


# This allows the plugin to be auto-discovered
PLUGIN_CLASS = AvatarPlugin
