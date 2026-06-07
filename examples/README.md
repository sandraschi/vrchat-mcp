# VRChat MCP Examples

This directory contains example scripts demonstrating the capabilities of the VRChat MCP.

## Versailles Boudoir Demo

An immersive demo showcasing a Versailles boudoir scenario with NPCs, interactive elements, and FastSearch integration.

### Features

- **NPC System**: Interact with historical characters like Marie Antoinette and her court
- **Scene Management**: Control lighting, mood, and atmosphere
- **FastSearch**: Quickly find and control parameters and NPCs
- **Interactive Elements**: Trigger animations, sounds, and scene transitions

### Prerequisites

- Python 3.8+
- VRChat running with OSC enabled
- Required Python packages (install with `pip install -r requirements.txt` in the project root)

### Running the Demo

1. Ensure VRChat is running with OSC enabled in the settings
2. Navigate to the project root directory
3. Run the demo script:
   ```bash
   python -m examples.versailles_boudoir_demo
   ```

### Demo Controls

Once running, the demo will automatically start a sequence. You can also interact with it programmatically:

```python
# Search for parameters
params = await demo.search_parameters("lighting")

# Search for NPCs
npcs = await demo.search_npcs("elegant")

# Change scene mood
await demo.set_scene_mood("romantic")

# Interact with an NPC
await demo.start_npc_interaction("marie_antoinette", "greeting")
```

### Customization

You can customize the demo by modifying the `versailles_boudoir_demo.py` file:

- Add more NPCs to the `self.npcs` dictionary
- Create new interaction types in `start_npc_interaction`
- Add more scene parameters and controls

## Additional Examples

More examples will be added in future updates.
