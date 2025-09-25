"""
Avatar Tools for VRChat MCP

This module provides tools for managing VRChat avatars, including state tracking,
parameter management, and avatar switching functionality.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from ...models import AvatarState, ParameterValue
from ...interpolation import InterpolationSystem, EasingFunction

logger = logging.getLogger(__name__)

class AvatarManager:
    """
    Manages VRChat avatar state and operations.

    Provides functionality for loading avatars, managing parameters,
    tracking avatar state, and coordinating with OSC communication.
    """

    def __init__(self, osc_manager=None, interpolation_system=None):
        """Initialize the avatar manager."""
        self.osc_manager = osc_manager
        self.interpolation = interpolation_system

        # Track avatar states
        self.avatars: Dict[str, AvatarState] = {}
        self.current_avatar_id: Optional[str] = None

        # Parameter interpolation tasks
        self._interpolation_tasks: Dict[str, asyncio.Task] = {}

        logger.info("AvatarManager initialized")

    async def load_avatar(self, avatar_id: str) -> Dict[str, Any]:
        """
        Load an avatar by ID.

        Args:
            avatar_id: The ID of the avatar to load

        Returns:
            Dictionary with load status and avatar information
        """
        try:
            if self.osc_manager:
                # Send avatar change command via OSC
                await self.osc_manager.send_parameter("VRC_Avatar", avatar_id)
                self.current_avatar_id = avatar_id

                # Initialize avatar state if not exists
                if avatar_id not in self.avatars:
                    self.avatars[avatar_id] = AvatarState(
                        avatar_id=avatar_id,
                        parameters={},
                        loaded_at=asyncio.get_event_loop().time()
                    )

                logger.info(f"Avatar load requested: {avatar_id}")
                return {
                    "status": "success",
                    "avatar_id": avatar_id,
                    "message": f"Avatar '{avatar_id}' load requested"
                }
            else:
                return {
                    "status": "error",
                    "error": "OSC manager not available",
                    "avatar_id": avatar_id
                }

        except Exception as e:
            logger.error(f"Failed to load avatar {avatar_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "avatar_id": avatar_id
            }

    async def get_avatar_state(self, avatar_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the current state of an avatar.

        Args:
            avatar_id: Optional avatar ID (defaults to current avatar)

        Returns:
            Dictionary with avatar state information
        """
        avatar_id = avatar_id or self.current_avatar_id

        if not avatar_id:
            return {
                "status": "error",
                "error": "No avatar ID specified and no current avatar"
            }

        if avatar_id not in self.avatars:
            return {
                "status": "error",
                "error": f"Avatar '{avatar_id}' not found",
                "avatar_id": avatar_id
            }

        avatar_state = self.avatars[avatar_id]

        return {
            "status": "success",
            "avatar_id": avatar_id,
            "current": avatar_id == self.current_avatar_id,
            "parameters": avatar_state.parameters,
            "loaded_at": avatar_state.loaded_at,
            "parameter_count": len(avatar_state.parameters)
        }

    async def set_parameter(
        self,
        avatar_id: str,
        parameter_name: str,
        value: Union[bool, float, int, str],
        interpolate: bool = False,
        duration: float = 0.5,
        easing: str = "linear"
    ) -> bool:
        """
        Set a parameter value for an avatar.

        Args:
            avatar_id: ID of the avatar
            parameter_name: Name of the parameter to set
            value: Value to set
            interpolate: Whether to interpolate to the value
            duration: Interpolation duration in seconds
            easing: Easing function name

        Returns:
            True if successful, False otherwise
        """
        try:
            if avatar_id not in self.avatars:
                self.avatars[avatar_id] = AvatarState(
                    avatar_id=avatar_id,
                    parameters={},
                    loaded_at=asyncio.get_event_loop().time()
                )

            if interpolate and self.interpolation:
                # Cancel any existing interpolation for this parameter
                param_key = f"{avatar_id}:{parameter_name}"
                if param_key in self._interpolation_tasks:
                    self._interpolation_tasks[param_key].cancel()

                # Get current value
                current_value = self.avatars[avatar_id].parameters.get(parameter_name, 0.0)
                if isinstance(current_value, bool):
                    current_value = 1.0 if current_value else 0.0

                # Start interpolation
                task = asyncio.create_task(
                    self._interpolate_parameter(
                        avatar_id, parameter_name, float(current_value), float(value),
                        duration, easing
                    )
                )
                self._interpolation_tasks[param_key] = task
                return True
            else:
                # Set parameter directly
                if self.osc_manager:
                    await self.osc_manager.send_parameter(parameter_name, value, avatar_id)

                # Update local state
                self.avatars[avatar_id].parameters[parameter_name] = value

                logger.debug(f"Set parameter {parameter_name} = {value} for avatar {avatar_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to set parameter {parameter_name} for avatar {avatar_id}: {e}")
            return False

    async def get_parameter(self, avatar_id: str, parameter_name: str, default: Any = None) -> Optional[Union[bool, float, int, str]]:
        """
        Get a parameter value for an avatar.

        Args:
            avatar_id: ID of the avatar
            parameter_name: Name of the parameter to get

        Returns:
            Parameter value or None if not found
        """
        if avatar_id in self.avatars:
            return self.avatars[avatar_id].parameters.get(parameter_name, default)

        # Try to get from OSC manager if avatar not in local state
        if self.osc_manager:
            result = self.osc_manager.get_parameter_value(parameter_name, avatar_id, default)
            return result

        return default

    async def _interpolate_parameter(
        self,
        avatar_id: str,
        parameter_name: str,
        start_value: float,
        end_value: float,
        duration: float,
        easing: str
    ) -> None:
        """
        Interpolate a parameter value over time.

        Args:
            avatar_id: ID of the avatar
            parameter_name: Name of the parameter
            start_value: Starting value
            end_value: Ending value
            duration: Duration in seconds
            easing: Easing function name
        """
        try:
            param_key = f"{avatar_id}:{parameter_name}"

            # Get easing function
            easing_func = getattr(self.interpolation, f"ease_{easing}", self.interpolation.ease_linear)

            start_time = asyncio.get_event_loop().time()

            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= duration:
                    # Final value
                    current_value = end_value
                    if self.osc_manager:
                        await self.osc_manager.send_parameter(parameter_name, current_value, avatar_id)
                    self.avatars[avatar_id].parameters[parameter_name] = current_value
                    break

                # Calculate interpolated value
                t = elapsed / duration
                eased_t = easing_func(t)
                current_value = start_value + (end_value - start_value) * eased_t

                # Send parameter update
                if self.osc_manager:
                    await self.osc_manager.send_parameter(parameter_name, current_value, avatar_id)

                # Update local state
                self.avatars[avatar_id].parameters[parameter_name] = current_value

                # Wait for next frame (roughly 60 FPS)
                await asyncio.sleep(1/60)

            # Clean up task reference
            if param_key in self._interpolation_tasks:
                del self._interpolation_tasks[param_key]

            logger.debug(f"Parameter interpolation completed: {parameter_name} = {end_value}")

        except asyncio.CancelledError:
            logger.debug(f"Parameter interpolation cancelled: {parameter_name}")
        except Exception as e:
            logger.error(f"Error during parameter interpolation: {e}")

    def list_avatars(self) -> List[str]:
        """Get a list of all tracked avatar IDs."""
        return list(self.avatars.keys())

    def get_current_avatar(self) -> Optional[str]:
        """Get the ID of the currently loaded avatar."""
        return self.current_avatar_id

    async def cleanup(self) -> None:
        """Clean up resources and cancel ongoing interpolations."""
        # Cancel all interpolation tasks
        for task in self._interpolation_tasks.values():
            task.cancel()

        self._interpolation_tasks.clear()

        logger.info("AvatarManager cleanup completed")

