"""
VRChat MCP Interpolation Demo

This script demonstrates the parameter interpolation features of the VRChat MCP.
It shows how to smoothly transition between parameter values using different
easing functions.
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("interpolation_demo")

# This would normally be imported from the actual package
# from vrchat_mcp import MCPClient, AvatarManager

# Mock classes for demonstration
class MCPClient:
    def __init__(self):
        self.avatar = AvatarManager()
        
    async def connect(self):
        logger.info("Connected to VRChat")
        return self
    
    async def close(self):
        logger.info("Disconnected from VRChat")
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

class AvatarManager:
    """Mock AvatarManager for demonstration."""
    
    async def set_parameter(
        self,
        avatar_id: str,
        name: str,
        value: float,
        interpolate: bool = False,
        duration: float = 1.0,
        easing: str = "linear"
    ) -> None:
        """Mock set_parameter with interpolation support."""
        if interpolate:
            logger.info(
                f"Interpolating {name} to {value:.2f} over {duration:.1f}s "
                f"with {easing} easing"
            )
        else:
            logger.info(f"Setting {name} to {value:.2f} (immediate)")
    
    async def set_parameters(
        self,
        avatar_id: str,
        parameters: Dict[str, float],
        interpolate: bool = False,
        duration: float = 1.0,
        easing: str = "linear"
    ) -> None:
        """Mock set_parameters with interpolation support."""
        for name, value in parameters.items():
            await self.set_parameter(
                avatar_id, name, value, interpolate, duration, easing
            )
    
    async def stop_all_interpolations(self) -> None:
        """Mock stop_all_interpolations."""
        logger.info("Stopped all interpolations")

# Demo functions
async def demo_single_parameter(mcp: MCPClient) -> None:
    """Demo interpolating a single parameter."""
    print("\n=== Single Parameter Interpolation ===")
    
    avatar_id = "avtr_12345678"
    param_name = "Viseme"
    
    # Immediate set
    await mcp.avatar.set_parameter(avatar_id, param_name, 0.5)
    
    # Interpolate with default settings
    await mcp.avatar.set_parameter(
        avatar_id, param_name, 1.0,
        interpolate=True, duration=2.0
    )
    
    # Wait for the interpolation to complete
    await asyncio.sleep(2.5)
    
    # Interpolate back with custom easing
    await mcp.avatar.set_parameter(
        avatar_id, param_name, 0.0,
        interpolate=True, duration=1.5, easing="ease_in_out_sine"
    )
    
    await asyncio.sleep(2.0)

async def demo_multiple_parameters(mcp: MCPClient) -> None:
    """Demo interpolating multiple parameters simultaneously."""
    print("\n=== Multiple Parameters Interpolation ===")
    
    avatar_id = "avtr_12345678"
    
    # Set initial values
    await mcp.avatar.set_parameter(avatar_id, "Viseme", 0.0)
    await mcp.avatar.set_parameter(avatar_id, "GestureLeft", 0.0)
    await mcp.avatar.set_parameter(avatar_id, "GestureRight", 0.0)
    
    # Interpolate all at once
    await mcp.avatar.set_parameters(
        avatar_id,
        parameters={
            "Viseme": 1.0,
            "GestureLeft": 2.0,
            "GestureRight": 3.0
        },
        interpolate=True,
        duration=2.0,
        easing="ease_in_out_quad"
    )
    
    await asyncio.sleep(2.5)
    
    # Reset all with a bounce effect
    await mcp.avatar.set_parameters(
        avatar_id,
        parameters={
            "Viseme": 0.0,
            "GestureLeft": 0.0,
            "GestureRight": 0.0
        },
        interpolate=True,
        duration=1.5,
        easing="bounce_out"
    )
    
    await asyncio.sleep(2.0)

async def demo_easing_functions(mcp: MCPClient) -> None:
    """Demo different easing functions."""
    print("\n=== Easing Functions Demo ===")
    
    avatar_id = "avtr_12345678"
    param_name = "Viseme"
    
    # List of easing functions to demonstrate
    easing_functions = [
        "linear",
        "ease_in_quad",
        "ease_out_quad",
        "ease_in_out_quad",
        "ease_in_out_cubic",
        "ease_in_out_sine",
        "ease_in_out_expo",
        "elastic_out",
        "bounce_out"
    ]
    
    for easing in easing_functions:
        # Move up
        await mcp.avatar.set_parameter(
            avatar_id, param_name, 1.0,
            interpolate=True, duration=1.5, easing=easing
        )
        await asyncio.sleep(1.7)  # Slight extra delay
        
        # Move down
        await mcp.avatar.set_parameter(
            avatar_id, param_name, 0.0,
            interpolate=True, duration=1.5, easing=easing
        )
        await asyncio.sleep(1.7)  # Slight extra delay
        
        print(f"\nCompleted demo of '{easing}' easing.\n")

async def main() -> None:
    """Run the interpolation demo."""
    print("VRChat MCP Interpolation Demo")
    print("============================")
    print("This demo shows how to use parameter interpolation")
    print("to create smooth animations in VRChat.\n")
    
    async with MCPClient() as mcp:
        # Run the demos
        await demo_single_parameter(mcp)
        await demo_multiple_parameters(mcp)
        await demo_easing_functions(mcp)
        
        # Clean up
        await mcp.avatar.stop_all_interpolations()
    
    print("\nDemo complete!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
