# VRChat MCP

A FastMCP 2.10 implementation for controlling VRChat avatars and assets with support for intelligent NPCs, OSC communication, and more.

## Features

- **FastMCP 2.10 Compatible** - Full support for stdio and HTTP interfaces
- **OSC Integration** - Bidirectional communication with VRChat using Open Sound Control
- **Intelligent NPCs** - Advanced conversation management with language model integration
- **Avatar Control** - Dynamic parameter management and animation control
- **FastSearch** - Quick lookup of avatars, assets, and parameters
- **Horizon Worlds Ready** - Designed with cross-platform compatibility in mind
- **DXT Packaging** - Easy deployment with DXT app packaging

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/vrchat-mcp.git
   cd vrchat-mcp
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Install development dependencies (optional):
   ```bash
   pip install -e ".[dev]"
   ```

## Configuration

Create a `.env` file in the project root with your configuration:

```ini
# OSC Configuration
OSC_SEND_HOST=127.0.0.1
OSC_SEND_PORT=9000
OSC_RECEIVE_HOST=127.0.0.1
OSC_RECEIVE_PORT=9001

# NPC Configuration
DEFAULT_MODEL=gpt-4
MAX_CONVERSATION_HISTORY=10
RESPONSE_TIMEOUT=30.0
ENABLE_EMOTIONS=true
```

## Usage

### Starting the Server

```bash
python -m vrchat_mcp.server
```

### Using the MCP Client

```python
from fastmcp import MCPClient

async def main():
    async with MCPClient("stdio") as client:
        # Load an avatar
        await client.call("load_avatar", {
            "preset_name": "my_avatar",
            "parameters": {"happy": 1.0, "talking": True}
        })
        
        # Set an avatar parameter
        await client.call("set_parameter", {
            "parameter_name": "happy",
            "value": 0.5
        })
        
        # Start an NPC conversation
        response = await client.call("start_conversation", {
            "npc_id": "guide_bot",
            "message": "Hello, how are you?"
        })
        print(response)

asyncio.run(main())
```

## VRChat Setup

1. Enable OSC in VRChat:
   - Go to Settings → OSC
   - Enable both "OSC" and "ChatBox"
   - Set the correct ports (default: 9000 for sending, 9001 for receiving)

2. Configure your avatar:
   - Add an `Avatar Parameters` component
   - Define parameters you want to control
   - Set up animations and expressions to respond to these parameters

## DXT Packaging

To create a DXT package:

```bash
dxt build
```

This will create a `.dxt` package in the `dist` directory that can be installed in any DXT-compatible environment.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

This project uses `black` for code formatting and `isort` for import sorting:

```bash
black src/
isort src/
```

## Documentation

For detailed documentation, see the [docs](docs/) directory:

- [API Reference](docs/api.md)
- [Tutorials](docs/tutorials/)
- [Configuration](docs/configuration.md)
- [Advanced Usage](docs/advanced.md)

## License

MIT

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## Support

For support, please open an issue on the [GitHub repository](https://github.com/yourusername/vrchat-mcp/issues).
