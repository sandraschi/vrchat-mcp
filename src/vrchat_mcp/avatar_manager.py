"""
Avatar State Manager for VRChat MCP.

This module provides functionality to manage avatar states, including loading avatars,
setting parameters, and handling animations and expressions.
"""

import asyncio
import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .interpolation import EasingFunction, InterpolationManager
from .models import (
    AnimationMap,
    AnimationRequest,
    AvatarLoadRequest,
    AvatarState,
    ExpressionMap,
    ExpressionRequest,
    ParameterMap,
)
from .osc import OSCManager

logger = logging.getLogger(__name__)


@dataclass
class AvatarPreset:
    """A preset configuration for an avatar with predefined parameters and settings."""

    name: str
    avatar_id: str
    parameters: ParameterMap = field(default_factory=dict)
    animations: AnimationMap = field(default_factory=dict)
    expressions: ExpressionMap = field(default_factory=dict)
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def update(self, **kwargs) -> None:
        """Update the preset with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        """Convert the preset to a dictionary."""
        return {
            "name": self.name,
            "avatar_id": self.avatar_id,
            "parameters": self.parameters,
            "animations": {k: v.to_dict() for k, v in self.animations.items()},
            "expressions": {k: v.to_dict() for k, v in self.expressions.items()},
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AvatarPreset":
        """Create a preset from a dictionary."""
        # Convert nested dictionaries back to model instances
        animations = {}
        if "animations" in data:
            for name, anim_data in data.get("animations", {}).items():
                animations[name] = AnimationRequest.from_dict(anim_data)

        expressions = {}
        if "expressions" in data:
            for name, expr_data in data.get("expressions", {}).items():
                expressions[name] = ExpressionRequest.from_dict(expr_data)

        return cls(
            name=data["name"],
            avatar_id=data["avatar_id"],
            parameters=data.get("parameters", {}),
            animations=animations,
            expressions=expressions,
            description=data.get("description", ""),
            tags=data.get("tags", []),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class AvatarManager:
    """Manages avatar states, presets, and transitions."""

    def __init__(self, osc_manager: OSCManager):
        """Initialize the avatar manager.

        Args:
            osc_manager: The OSC manager to use for sending messages
        """
        self.osc = osc_manager
        self.current_avatar: str | None = None
        self.avatar_states: dict[str, AvatarState] = {}
        self.presets: dict[str, AvatarPreset] = {}
        self._state_lock = asyncio.Lock()
        self._presets_loaded = False
        self._presets_file: str | None = None

        # Initialize interpolation manager
        self._interpolation_manager = InterpolationManager(self._on_parameter_interpolated)

        # Track which parameters are currently being interpolated
        self._interpolating_parameters: dict[str, asyncio.Future] = {}
        self._background_tasks: set[asyncio.Task] = set()

        # Register handlers
        self.osc.add_handler("/avatar/change", self._handle_avatar_change)
        self.osc.add_handler("/avatar/parameters/*", self._handle_parameter_update)

        # Start the interpolation manager
        task = asyncio.create_task(self._interpolation_manager.start())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def load_avatar(self, request: str | AvatarLoadRequest) -> bool:
        """Load an avatar with the given ID and optional parameters.

        Args:
            request: Either an avatar ID string or an AvatarLoadRequest instance

        Returns:
            bool: True if the request was sent successfully, False otherwise
        """
        if isinstance(request, str):
            request = AvatarLoadRequest(avatar_id=request)

        async with self._state_lock:
            try:
                # Send the avatar change request
                self.osc.load_avatar(request.avatar_id)

                # If there are parameters to set, send them after a short delay
                if request.parameters:
                    task = asyncio.create_task(
                        self._set_parameters_after_delay(
                            request.avatar_id,
                            request.parameters,
                            delay=1.0,  # Short delay to allow avatar to load
                        )
                    )
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)

                # Update the current avatar
                self.current_avatar = request.avatar_id

                # Initialize state if it doesn't exist
                if request.avatar_id not in self.avatar_states:
                    self.avatar_states[request.avatar_id] = AvatarState(avatar_id=request.avatar_id)

                logger.info(f"Loading avatar: {request.avatar_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to load avatar {request.avatar_id}: {e}", exc_info=True)
                return False

    async def _set_parameters_after_delay(self, avatar_id: str, parameters: dict[str, Any], delay: float = 1.0) -> None:
        """Set parameters after a delay to allow the avatar to load."""
        await asyncio.sleep(delay)
        await self.set_parameters(avatar_id, parameters)

    async def set_parameters(
        self,
        avatar_id: str,
        parameters: dict[str, Any],
        immediate: bool = True,
        interpolate: bool = False,
        duration: float = 1.0,
        easing: EasingFunction | str = EasingFunction.LINEAR,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Set multiple parameters for an avatar with optional interpolation.

        Args:
            avatar_id: The ID of the avatar
            parameters: Dictionary of parameter names and target values
            immediate: Whether to send the updates immediately (if not interpolating)
            interpolate: Whether to interpolate to the target values
            duration: Duration of interpolation in seconds (if interpolate is True)
            easing: Easing function to use for interpolation (if interpolate is True)
            on_complete: Optional callback when interpolation completes
        """
        if not parameters:
            if on_complete:
                on_complete()
            return

        # Convert string easing to EasingFunction if needed
        if isinstance(easing, str):
            try:
                easing = EasingFunction[easing.upper()]
            except KeyError:
                logger.warning(f"Unknown easing function: {easing}, using LINEAR")
                easing = EasingFunction.LINEAR

        async with self._state_lock:
            # Update the state with target values
            if avatar_id not in self.avatar_states:
                self.avatar_states[avatar_id] = AvatarState(avatar_id=avatar_id)

            state = self.avatar_states[avatar_id]
            state.parameters.update(parameters)
            state.timestamp = time.time()

            # If not interpolating, send updates immediately
            if not interpolate:
                if immediate and avatar_id == self.current_avatar:
                    for name, value in parameters.items():
                        try:
                            self.osc.send_message(f"/avatar/parameters/{name}", value)
                        except Exception as e:
                            logger.error(f"Failed to set parameter {name}: {e}", exc_info=True)

                if on_complete:
                    on_complete()
                return

            # Handle interpolation
            if avatar_id != self.current_avatar:
                logger.warning(f"Cannot interpolate parameters for non-current avatar: {avatar_id}")
                if on_complete:
                    on_complete()
                return

            # Start interpolation
            self._interpolation_manager.interpolate_parameters(
                parameters=parameters, duration=duration, easing=easing, on_complete=on_complete
            )

    async def set_parameter(
        self,
        avatar_id: str,
        name: str,
        value: Any,
        immediate: bool = True,
        interpolate: bool = False,
        duration: float = 1.0,
        easing: EasingFunction | str = EasingFunction.LINEAR,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Set a single parameter for an avatar with optional interpolation.

        Args:
            avatar_id: The ID of the avatar
            name: Name of the parameter to set
            value: Target value
            immediate: Whether to send the update immediately (if not interpolating)
            interpolate: Whether to interpolate to the target value
            duration: Duration of interpolation in seconds (if interpolate is True)
            easing: Easing function to use for interpolation (if interpolate is True)
            on_complete: Optional callback when interpolation completes
        """
        await self.set_parameters(
            avatar_id=avatar_id,
            parameters={name: value},
            immediate=immediate,
            interpolate=interpolate,
            duration=duration,
            easing=easing,
            on_complete=on_complete,
        )

    async def play_animation(self, avatar_id: str, animation_request: str | AnimationRequest) -> None:
        """Play an animation on an avatar."""
        if isinstance(animation_request, str):
            animation_request = AnimationRequest(name=animation_request)

        async with self._state_lock:
            # Update the state
            if avatar_id not in self.avatar_states:
                self.avatar_states[avatar_id] = AvatarState(avatar_id=avatar_id)

            state = self.avatar_states[avatar_id]

            # Add or update the animation in the active animations
            animation_dict = animation_request.to_dict()
            state.active_animations = [
                anim for anim in state.active_animations if anim.get("name") != animation_request.name
            ]
            state.active_animations.append(animation_dict)
            state.timestamp = time.time()

            # Send the animation command if this is the current avatar
            if avatar_id == self.current_avatar:
                # In a real implementation, this would send the appropriate OSC messages
                # to play the animation in VRChat
                logger.debug(f"Would play animation: {animation_request.name}")

    async def set_expression(self, avatar_id: str, expression_request: str | ExpressionRequest) -> None:
        """Set an expression on an avatar."""
        if isinstance(expression_request, str):
            expression_request = ExpressionRequest(name=expression_request, value=True)

        async with self._state_lock:
            # Update the state
            if avatar_id not in self.avatar_states:
                self.avatar_states[avatar_id] = AvatarState(avatar_id=avatar_id)

            state = self.avatar_states[avatar_id]

            # Add or update the expression in the active expressions
            expr_dict = expression_request.to_dict()
            state.active_expressions = [
                expr for expr in state.active_expressions if expr.get("name") != expression_request.name
            ]
            state.active_expressions.append(expr_dict)
            state.timestamp = time.time()

            # Send the expression command if this is the current avatar
            if avatar_id == self.current_avatar:
                # In a real implementation, this would send the appropriate OSC messages
                # to set the expression in VRChat
                logger.debug(f"Would set expression: {expression_request.name} = {expression_request.value}")

    # === Preset Management ===

    def add_preset(self, preset: AvatarPreset) -> None:
        """Add or update a preset."""
        self.presets[preset.name.lower()] = preset
        self._save_presets_async()

    def get_preset(self, name: str) -> AvatarPreset | None:
        """Get a preset by name."""
        return self.presets.get(name.lower())

    def delete_preset(self, name: str) -> bool:
        """Delete a preset by name."""
        if name.lower() in self.presets:
            del self.presets[name.lower()]
            self._save_presets_async()
            return True
        return False

    async def load_preset(self, name: str) -> bool:
        """Load a preset by name."""
        preset = self.get_preset(name)
        if not preset:
            logger.warning(f"Preset not found: {name}")
            return False

        # Create a load request from the preset
        request = AvatarLoadRequest(avatar_id=preset.avatar_id, parameters=preset.parameters)

        # Load the avatar
        success = await self.load_avatar(request)
        if not success:
            return False

        # Apply animations
        for anim in preset.animations.values():
            await self.play_animation(preset.avatar_id, anim)

        # Apply expressions
        for expr in preset.expressions.values():
            await self.set_expression(preset.avatar_id, expr)

        return True

    def load_presets_from_file(self, filepath: str) -> None:
        """Load presets from a JSON file."""
        self._presets_file = filepath
        try:
            with open(filepath) as f:
                data = json.load(f)
                self.presets = {name: AvatarPreset.from_dict(preset_data) for name, preset_data in data.items()}
            self._presets_loaded = True
            logger.info(f"Loaded {len(self.presets)} presets from {filepath}")
        except FileNotFoundError:
            logger.warning(f"Presets file not found: {filepath}")
            self.presets = {}
            self._presets_loaded = True
        except Exception as e:
            logger.error(f"Failed to load presets from {filepath}: {e}", exc_info=True)
            self.presets = {}

    def _save_presets_async(self) -> None:
        """Save presets to a file asynchronously."""
        if not self._presets_file:
            return

        presets_data = {name: preset.to_dict() for name, preset in self.presets.items()}

        # Schedule the file write in a separate task
        task = asyncio.create_task(self._save_presets_to_file(self._presets_file, presets_data))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _save_presets_to_file(self, filepath: str, data: dict) -> None:
        """Save presets to a file."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

            # Write to a temporary file first, then rename to ensure atomicity
            temp_file = f"{filepath}.tmp"
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            # On Windows, we can't rename over an existing file, so remove it first
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rename(temp_file, filepath)

            logger.debug(f"Saved {len(data)} presets to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save presets to {filepath}: {e}", exc_info=True)

    # === Event Handlers ===

    def _handle_avatar_change(self, address: str, args: list[Any]) -> None:
        """Handle avatar change events from VRChat."""
        if not args:
            return

        new_avatar_id = args[0]
        if not isinstance(new_avatar_id, str):
            return

        old_avatar_id = self.current_avatar
        self.current_avatar = new_avatar_id

        # Initialize state if it doesn't exist
        if new_avatar_id not in self.avatar_states:
            self.avatar_states[new_avatar_id] = AvatarState(avatar_id=new_avatar_id)

        logger.info(f"Avatar changed from {old_avatar_id} to {new_avatar_id}")

        # In a real implementation, we would also restore the state of the new avatar
        # and apply any pending updates

    def _on_parameter_interpolated(self, param_name: str, value: float) -> None:
        """Callback when a parameter value is updated by the interpolation manager."""
        if not self.current_avatar:
            return

        # Update the state
        if self.current_avatar not in self.avatar_states:
            self.avatar_states[self.current_avatar] = AvatarState(avatar_id=self.current_avatar)

        # Update the parameter in the state
        self.avatar_states[self.current_avatar].parameters[param_name] = value

        # Send the updated value to VRChat
        try:
            self.osc.send_message(f"/avatar/parameters/{param_name}", value)
        except Exception as e:
            logger.error(f"Failed to send interpolated parameter {param_name}: {e}", exc_info=True)

    def _handle_parameter_update(self, address: str, args: list[Any]) -> None:
        """Handle parameter update events from VRChat."""
        if not self.current_avatar or not args:
            return

        # Extract the parameter name from the address
        param_name = address.split("/")[-1]
        param_value = args[0]

        # If this parameter is being interpolated, stop the interpolation
        # to prevent conflicts with external changes
        if param_name in self._interpolation_manager.active_interpolations:
            self._interpolation_manager.stop_interpolation(param_name)

        # Update the state
        if self.current_avatar not in self.avatar_states:
            self.avatar_states[self.current_avatar] = AvatarState(avatar_id=self.current_avatar)

        self.avatar_states[self.current_avatar].parameters[param_name] = param_value
        self.avatar_states[self.current_avatar].timestamp = time.time()

    # === State Management ===

    async def get_avatar_state(self, avatar_id: str) -> AvatarState | None:
        """Get the current state of an avatar."""
        async with self._state_lock:
            return self.avatar_states.get(avatar_id)

    async def save_avatar_state(self, name: str) -> AvatarPreset | None:
        """Save the current avatar's state as a preset."""
        if not self.current_avatar or self.current_avatar not in self.avatar_states:
            return None

        state = self.avatar_states[self.current_avatar]

        # Create a new preset with the current state
        preset = AvatarPreset(
            name=name, avatar_id=self.current_avatar, parameters=state.parameters.copy(), animations={}, expressions={}
        )

        # Add animations and expressions if available
        for anim in state.active_animations:
            preset.animations[anim["name"]] = AnimationRequest.from_dict(anim)

        for expr in state.active_expressions:
            preset.expressions[expr["name"]] = ExpressionRequest.from_dict(expr)

        # Save the preset
        self.add_preset(preset)
        return preset

    async def reset_avatar(self, avatar_id: str, reset_parameters: bool = True) -> None:
        """Reset an avatar to its default state.

        Args:
            avatar_id: ID of the avatar to reset
            reset_parameters: Whether to reset all parameters to their default values
        """
        async with self._state_lock:
            if avatar_id in self.avatar_states:
                # Stop any active interpolations for this avatar
                if avatar_id == self.current_avatar:
                    self._interpolation_manager.stop_all_interpolations()

                # Reset the state
                if reset_parameters:
                    self.avatar_states[avatar_id] = AvatarState(avatar_id=avatar_id)
                else:
                    # Keep parameters but reset other state
                    old_params = self.avatar_states[avatar_id].parameters
                    self.avatar_states[avatar_id] = AvatarState(avatar_id=avatar_id, parameters=old_params)

                # If this is the current avatar, send reset commands
                if avatar_id == self.current_avatar:
                    # In a real implementation, this would send the appropriate OSC messages
                    # to reset the avatar in VRChat
                    logger.debug(f"Would reset avatar: {avatar_id}")

    async def stop_all_animations(self, avatar_id: str) -> None:
        """Stop all animations for an avatar."""
        async with self._state_lock:
            if avatar_id in self.avatar_states:
                self.avatar_states[avatar_id].active_animations = []
                # In a real implementation, send commands to stop animations
                logger.debug(f"Stopped all animations for avatar: {avatar_id}")

    async def stop_all_animations_and_reset(self, avatar_id: str) -> None:
        """Stop all animations and reset parameters to their default values."""
        await self.stop_all_animations(avatar_id)
        await self.reset_avatar(avatar_id, reset_parameters=True)

    async def get_parameter(self, avatar_id: str, param_name: str) -> Any | None:
        """Get the current value of a parameter.

        Args:
            avatar_id: ID of the avatar
            param_name: Name of the parameter to get

        Returns:
            Current value of the parameter, or None if not found
        """
        if avatar_id not in self.avatar_states:
            return None

        return self.avatar_states[avatar_id].parameters.get(param_name)

    def is_parameter_interpolating(self, param_name: str) -> bool:
        """Check if a parameter is currently being interpolated.

        Args:
            param_name: Name of the parameter to check

        Returns:
            True if the parameter is being interpolated, False otherwise
        """
        return self._interpolation_manager.is_interpolating(param_name)

    def stop_parameter_interpolation(self, param_name: str) -> None:
        """Stop interpolation for a specific parameter.

        Args:
            param_name: Name of the parameter to stop interpolating
        """
        self._interpolation_manager.stop_interpolation(param_name)

    async def stop_all_interpolations(self) -> None:
        """Stop all active parameter interpolations."""
        self._interpolation_manager.stop_all_interpolations()

    # === Utility Methods ===

    def list_avatars(self) -> list[str]:
        """Get a list of all known avatar IDs."""
        return list(self.avatar_states.keys())

    def list_presets(self) -> list[str]:
        """Get a list of all preset names."""
        return list(self.presets.keys())

    def search_presets(self, query: str) -> list[AvatarPreset]:
        """Search for presets by name or tags."""
        query = query.lower()
        results = []

        for preset in self.presets.values():
            if (
                query in preset.name.lower()
                or any(query in tag.lower() for tag in preset.tags)
                or query in preset.description.lower()
            ):
                results.append(preset)

        return results
