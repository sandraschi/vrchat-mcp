"""
Parameter Interpolation System for VRChat MCP.

This module provides smooth transitions between parameter values using various
easing functions and interpolation methods.
"""

import asyncio
import math
import time
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np

class EasingFunction(Enum):
    """Easing functions for parameter interpolation."""
    LINEAR = auto()
    EASE_IN_QUAD = auto()
    EASE_OUT_QUAD = auto()
    EASE_IN_OUT_QUAD = auto()
    EASE_IN_CUBIC = auto()
    EASE_OUT_CUBIC = auto()
    EASE_IN_OUT_CUBIC = auto()
    EASE_IN_SINE = auto()
    EASE_OUT_SINE = auto()
    EASE_IN_OUT_SINE = auto()
    EASE_IN_EXPO = auto()
    EASE_OUT_EXPO = auto()
    EASE_IN_OUT_EXPO = auto()
    ELASTIC_OUT = auto()
    BOUNCE_OUT = auto()

@dataclass
class InterpolationTarget:
    """Target value and interpolation settings for a parameter."""
    name: str
    start_value: float
    target_value: float
    start_time: float
    duration: float
    easing: EasingFunction = EasingFunction.LINEAR
    on_complete: Optional[Callable[[], None]] = None
    _current_value: float = field(init=False)
    
    def __post_init__(self):
        self._current_value = self.start_value
    
    @property
    def current_value(self) -> float:
        """Get the current interpolated value."""
        return self._current_value
    
    @property
    def progress(self) -> float:
        """Get the current progress (0.0 to 1.0)."""
        elapsed = time.time() - self.start_time
        return min(max(elapsed / self.duration, 0.0), 1.0) if self.duration > 0 else 1.0
    
    @property
    def is_complete(self) -> bool:
        """Check if the interpolation is complete."""
        return self.progress >= 1.0
    
    def update(self, current_time: float) -> bool:
        """Update the current value based on the easing function.
        
        Args:
            current_time: Current time in seconds
            
        Returns:
            bool: True if the interpolation is complete, False otherwise
        """
        t = (current_time - self.start_time) / self.duration
        t = max(0.0, min(t, 1.0))  # Clamp to [0, 1]
        
        # Apply easing function
        if self.easing == EasingFunction.LINEAR:
            value = t
        elif self.easing == EasingFunction.EASE_IN_QUAD:
            value = t * t
        elif self.easing == EasingFunction.EASE_OUT_QUAD:
            value = t * (2 - t)
        elif self.easing == EasingFunction.EASE_IN_OUT_QUAD:
            t *= 2
            if t < 1:
                value = 0.5 * t * t
            else:
                t -= 1
                value = -0.5 * (t * (t - 2) - 1)
        elif self.easing == EasingFunction.EASE_IN_CUBIC:
            value = t * t * t
        elif self.easing == EasingFunction.EASE_OUT_CUBIC:
            t -= 1
            value = t * t * t + 1
        elif self.easing == EasingFunction.EASE_IN_OUT_CUBIC:
            t *= 2
            if t < 1:
                value = 0.5 * t * t * t
            else:
                t -= 2
                value = 0.5 * (t * t * t + 2)
        elif self.easing == EasingFunction.EASE_IN_SINE:
            value = 1 - math.cos(t * (math.pi / 2))
        elif self.easing == EasingFunction.EASE_OUT_SINE:
            value = math.sin(t * (math.pi / 2))
        elif self.easing == EasingFunction.EASE_IN_OUT_SINE:
            value = -0.5 * (math.cos(math.pi * t) - 1)
        elif self.easing == EasingFunction.EASE_IN_EXPO:
            value = math.pow(2, 10 * (t - 1)) if t > 0 else 0.0
        elif self.easing == EasingFunction.EASE_OUT_EXPO:
            value = -math.pow(2, -10 * t) + 1 if t < 1 else 1.0
        elif self.easing == EasingFunction.EASE_IN_OUT_EXPO:
            if t == 0 or t == 1:
                value = t
            else:
                t = t * 2
                if t < 1:
                    value = 0.5 * math.pow(2, 10 * (t - 1))
                else:
                    t -= 1
                    value = 0.5 * (-math.pow(2, -10 * t) + 2)
        elif self.easing == EasingFunction.ELASTIC_OUT:
            if t == 0:
                value = 0.0
            elif t == 1:
                value = 1.0
            else:
                p = 0.3
                s = p / 4.0
                value = math.pow(2, -10 * t) * math.sin((t - s) * (2 * math.pi) / p) + 1.0
        elif self.easing == EasingFunction.BOUNCE_OUT:
            if t < 1 / 2.75:
                value = 7.5625 * t * t
            elif t < 2 / 2.75:
                t -= 1.5 / 2.75
                value = 7.5625 * t * t + 0.75
            elif t < 2.5 / 2.75:
                t -= 2.25 / 2.75
                value = 7.5625 * t * t + 0.9375
            else:
                t -= 2.625 / 2.75
                value = 7.5625 * t * t + 0.984375
        else:
            value = t  # Default to linear
        
        # Update current value
        self._current_value = self.start_value + (self.target_value - self.start_value) * value
        
        # Check if complete
        if t >= 1.0 and self.on_complete:
            self.on_complete()
            return True
            
        return t >= 1.0

class InterpolationManager:
    """Manages parameter interpolations and updates."""
    
    def __init__(self, update_callback: Callable[[str, float], None]):
        """Initialize the interpolation manager.
        
        Args:
            update_callback: Function to call when a parameter value updates.
                            Signature: (parameter_name: str, value: float) -> None
        """
        self.active_interpolations: Dict[str, InterpolationTarget] = {}
        self.update_callback = update_callback
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the interpolation update loop."""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._update_loop())
    
    async def stop(self) -> None:
        """Stop the interpolation update loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    async def _update_loop(self) -> None:
        """Main update loop for interpolations."""
        while self._running:
            current_time = time.time()
            completed = []
            
            # Update all active interpolations
            for param_name, target in list(self.active_interpolations.items()):
                if target.update(current_time):
                    completed.append(param_name)
                
                # Notify of the updated value
                self.update_callback(param_name, target.current_value)
            
            # Remove completed interpolations
            for param_name in completed:
                if param_name in self.active_interpolations:
                    del self.active_interpolations[param_name]
            
            # Sleep to maintain reasonable update rate (60fps)
            await asyncio.sleep(1.0 / 60.0)
    
    def interpolate(
        self,
        param_name: str,
        target_value: float,
        duration: float = 1.0,
        easing: EasingFunction = EasingFunction.LINEAR,
        on_complete: Optional[Callable[[], None]] = None
    ) -> None:
        """Start interpolating a parameter to a target value.
        
        Args:
            param_name: Name of the parameter to interpolate
            target_value: Target value to interpolate to
            duration: Duration of the interpolation in seconds
            easing: Easing function to use
            on_complete: Optional callback when interpolation completes
        """
        current_value = 0.0
        
        # If there's an active interpolation for this parameter, use its current value
        if param_name in self.active_interpolations:
            current_value = self.active_interpolations[param_name].current_value
        
        # Create and store the new interpolation target
        target = InterpolationTarget(
            name=param_name,
            start_value=current_value,
            target_value=target_value,
            start_time=time.time(),
            duration=max(0.0001, duration),  # Avoid division by zero
            easing=easing,
            on_complete=on_complete
        )
        
        self.active_interpolations[param_name] = target
        
        # If not running, start the update loop
        if not self._running and not self._task:
            asyncio.create_task(self.start())
    
    def interpolate_parameters(
        self,
        parameters: Dict[str, float],
        duration: float = 1.0,
        easing: EasingFunction = EasingFunction.LINEAR,
        on_complete: Optional[Callable[[], None]] = None
    ) -> None:
        """Interpolate multiple parameters simultaneously.
        
        Args:
            parameters: Dictionary of parameter names to target values
            duration: Duration of the interpolation in seconds
            easing: Easing function to use
            on_complete: Optional callback when all interpolations complete
        """
        if not parameters:
            if on_complete:
                on_complete()
            return
        
        # Track completion of all interpolations
        remaining = len(parameters)
        
        def completion_handler() -> None:
            nonlocal remaining
            remaining -= 1
            if remaining <= 0 and on_complete:
                on_complete()
        
        # Start each interpolation
        for param_name, target_value in parameters.items():
            self.interpolate(
                param_name=param_name,
                target_value=target_value,
                duration=duration,
                easing=easing,
                on_complete=completion_handler if param_name == list(parameters.keys())[-1] else None
            )
    
    def stop_interpolation(self, param_name: str) -> None:
        """Stop an active interpolation for a parameter.
        
        Args:
            param_name: Name of the parameter to stop interpolating
        """
        if param_name in self.active_interpolations:
            del self.active_interpolations[param_name]
    
    def stop_all_interpolations(self) -> None:
        """Stop all active interpolations."""
        self.active_interpolations.clear()
    
    def get_current_value(self, param_name: str) -> Optional[float]:
        """Get the current interpolated value of a parameter.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            Current value if the parameter is being interpolated, None otherwise
        """
        target = self.active_interpolations.get(param_name)
        return target.current_value if target else None
    
    def is_interpolating(self, param_name: str) -> bool:
        """Check if a parameter is currently being interpolated.
        
        Args:
            param_name: Name of the parameter to check
            
        Returns:
            True if the parameter is being interpolated, False otherwise
        """
        return param_name in self.active_interpolations
