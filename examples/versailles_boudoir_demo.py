"""
Versailles Boudoir Demo for VRChat MCP

This script demonstrates the VRChat MCP with a Versailles boudoir scenario,
showcasing FastSearch integration, NPC control, and asset management.
"""
import asyncio
import logging
import random
from typing import Dict, List, Optional

from vrchat_mcp.tools import OSCManager, NPCManager, fast_search
from vrchat_mcp.models import OSCMessage, OSCBundle, NPCAction, NPCState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("versailles_demo")

class VersaillesBoudoirDemo:
    """
    A demo showcasing a Versailles boudoir scenario in VRChat.
    
    Features:
    - FastSearch for discovering and controlling avatar parameters
    - NPCs with predefined behaviors and interactions
    - Scene transitions and atmosphere controls
    - Interactive elements and animations
    """
    
    def __init__(self):
        """Initialize the demo with default settings."""
        self.osc = OSCManager({
            'send_port': 9000,
            'receive_port': 9001,
            'auto_index_parameters': True
        })
        
        self.npc_manager = NPCManager()
        self.scene_state = {
            'time_of_day': 'afternoon',
            'mood': 'elegant',
            'active_npcs': {}
        }
        
        # Predefined NPCs for the boudoir scene
        self.npcs = {
            'marie_antoinette': {
                'id': 'npc_ma',
                'name': 'Marie Antoinette',
                'avatar_id': 'avtr_marie_antoinette',
                'default_pose': 'sitting_elegant',
                'moods': ['elegant', 'playful', 'regal'],
                'interests': ['gossip', 'fashion', 'parties']
            },
            'lady_in_waiting': {
                'id': 'npc_liw',
                'name': 'Lady in Waiting',
                'avatar_id': 'avtr_lady_waiting',
                'default_pose': 'standing_attentive',
                'moods': ['attentive', 'curious', 'helpful'],
                'interests': ['serving', 'gossip', 'etiquette']
            },
            'noble_guest': {
                'id': 'npc_ng',
                'name': 'Noble Guest',
                'avatar_id': 'avtr_noble_guest',
                'default_pose': 'standing_conversational',
                'moods': ['charming', 'intrigued', 'amused'],
                'interests': ['politics', 'art', 'gossip']
            }
        }
        
        # Register FastSearch indexes
        self._register_search_indexes()
    
    def _register_search_indexes(self) -> None:
        """Register search indexes for the boudoir scenario."""
        # Index NPCs
        for npc_id, npc_data in self.npcs.items():
            asyncio.create_task(
                fast_search.index_npc(
                    npc_id=npc_id,
                    name=npc_data['name'],
                    description=f"{npc_data['name']} in the Versailles boudoir scene",
                    tags=[f"mood:{mood}" for mood in npc_data['moods']] + 
                         npc_data['interests']
                )
            )
        
        # Index scene parameters
        scene_params = [
            ('time_of_day', 'Time of day in the boudoir', ['time', 'lighting', 'atmosphere']),
            ('mood', 'Overall mood of the scene', ['atmosphere', 'ambience', 'feeling']),
            ('music_volume', 'Background music volume', ['audio', 'sound', 'ambience']),
            ('light_intensity', 'Light intensity in the boudoir', ['lighting', 'atmosphere', 'visuals'])
        ]
        
        for param, desc, tags in scene_params:
            asyncio.create_task(
                fast_search.index_parameter(
                    param_name=f"boudoir/{param}",
                    param_type='float',
                    description=desc,
                    tags=tags
                )
            )
    
    async def initialize(self) -> None:
        """Initialize the demo setup."""
        logger.info("Initializing Versailles Boudoir Demo...")
        
        # Connect to VRChat
        await self.osc.connect()
        
        # Load NPCs
        for npc_id, npc_data in self.npcs.items():
            await self.npc_manager.add_npc(
                npc_id=npc_data['id'],
                name=npc_data['name'],
                avatar_id=npc_data['avatar_id'],
                default_state=NPCState(
                    pose=npc_data['default_pose'],
                    position=(0, 0, 0),  # Will be set by scene
                    rotation=(0, 0, 0)
                )
            )
            self.scene_state['active_npcs'][npc_id] = 'idle'
        
        logger.info("Demo initialization complete")
    
    async def set_scene_mood(self, mood: str) -> None:
        """Set the mood of the boudoir scene."""
        logger.info(f"Setting scene mood to: {mood}")
        self.scene_state['mood'] = mood
        
        # Update lighting and atmosphere based on mood
        if mood == 'romantic':
            await self.osc.send_message(OSCMessage("/avatar/parameters/Boudoir/Lighting/Intensity", 0.7))
            await self.osc.send_message(OSCMessage("/avatar/parameters/Boudoir/Lighting/Color", [1.0, 0.8, 0.9]))  # Soft pink
        elif mood == 'mysterious':
            await self.osc.send_message(OSCMessage("/avatar/parameters/Boudoir/Lighting/Intensity", 0.5))
            await self.osc.send_message(OSCMessage("/avatar/parameters/Boudoir/Lighting/Color", [0.5, 0.3, 0.8]))  # Deep purple
        else:  # elegant
            await self.osc.send_message(OSCMessage("/avatar/parameters/Boudoir/Lighting/Intensity", 1.0))
            await self.osc.send_message(OSCMessage("/avatar/parameters/Boudoir/Lighting/Color", [1.0, 0.95, 0.9]))  # Warm white
    
    async def start_npc_interaction(self, npc_id: str, interaction_type: str) -> None:
        """Start an interaction with an NPC."""
        if npc_id not in self.scene_state['active_npcs']:
            logger.warning(f"NPC {npc_id} not found in active NPCs")
            return
            
        npc_data = self.npcs[npc_id]
        logger.info(f"Starting {interaction_type} interaction with {npc_data['name']}")
        
        # Update NPC state
        self.scene_state['active_npcs'][npc_id] = f"interacting_{interaction_type}"
        
        # Trigger appropriate animation and behavior
        if interaction_type == 'greeting':
            await self.npc_manager.execute_action(
                npc_id=npc_data['id'],
                action=NPCAction(
                    type="animation",
                    name="wave_hand",
                    duration=2.0
                )
            )
            # Play greeting sound
            await self.osc.send_message(OSCMessage(
                "/avatar/parameters/Boudoir/Audio/PlayOneShot",
                f"greeting_{random.randint(1, 3)}"
            ))
        
        # More interaction types can be added here
    
    async def search_parameters(self, query: str) -> List[Dict]:
        """Search for parameters using FastSearch."""
        results = await fast_search.search_parameters(query)
        logger.info(f"Found {len(results)} parameters matching '{query}'")
        return results
    
    async def search_npcs(self, query: str) -> List[Dict]:
        """Search for NPCs using FastSearch."""
        results = await fast_search.search_npcs(query)
        logger.info(f"Found {len(results)} NPCs matching '{query}'")
        return results
    
    async def run_demo_sequence(self) -> None:
        """Run a demo sequence showcasing the boudoir features."""
        logger.info("Starting Versailles Boudoir demo sequence...")
        
        # Set initial scene
        await self.set_scene_mood('elegant')
        
        # Have NPCs enter the scene
        for npc_id in self.npcs:
            await self.npc_manager.teleport_npc(
                npc_id=self.npcs[npc_id]['id'],
                position=(
                    random.uniform(-2, 2),
                    0,
                    random.uniform(-2, 2)
                )
            )
            await asyncio.sleep(1.0)
        
        # Demonstrate parameter search
        logger.info("Demonstrating parameter search...")
        lighting_params = await self.search_parameters("lighting")
        if lighting_params:
            logger.info(f"Found lighting parameter: {lighting_params[0]}")
        
        # Demonstrate NPC search
        logger.info("Demonstrating NPC search...")
        npc_results = await self.search_npcs("elegant")
        if npc_results:
            logger.info(f"Found NPC: {npc_results[0]}")
        
        # Start an interaction
        if 'marie_antoinette' in self.npcs:
            await self.start_npc_interaction('marie_antoinette', 'greeting')
        
        logger.info("Demo sequence complete!")

async def main():
    """Main entry point for the demo."""
    demo = VersaillesBoudoirDemo()
    
    try:
        await demo.initialize()
        await demo.run_demo_sequence()
        
        # Keep the demo running for interaction
        logger.info("Demo is running. Press Ctrl+C to exit.")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Demo stopped by user")
    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
    finally:
        # Cleanup
        await demo.osc.disconnect()
        logger.info("Demo cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())
