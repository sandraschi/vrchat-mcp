# VRChat MCP with Standalone Headsets

This guide explains how to use VRChat MCP with standalone VR headsets (Pico 4, Quest 2) using Virtual Desktop and a relay server setup.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Setup Options](#setup-options)
   - [Option 1: Virtual Desktop (Recommended)](#option-1-virtual-desktop-recommended)
   - [Option 2: Relay Server (Advanced)](#option-2-relay-server-advanced)
3. [Interaction Scenarios](#interaction-scenarios)
4. [Troubleshooting](#troubleshooting)

## Prerequisites

- A gaming PC capable of running VRChat
- Standalone VR headset (Pico 4/Quest 2)
- Virtual Desktop installed on your headset and PC
- 5GHz WiFi network (for best performance)
- VRChat account

## Setup Options

### Option 1: Virtual Desktop (Recommended)

#### 1. Install Required Software
1. Install Virtual Desktop Streamer on your PC
2. Install Virtual Desktop app on your headset
3. Install VRChat on your PC via Steam

#### 2. Configure Virtual Desktop
1. Launch Virtual Desktop Streamer on your PC
2. Launch Virtual Desktop on your headset
3. Connect to your PC from the headset

#### 3. Run VRChat with MCP
1. Launch VRChat through Virtual Desktop
2. On your PC, start the VRChat MCP server
3. MCP will automatically connect to VRChat via OSC

### Option 2: Relay Server (Advanced)

This method is more complex but doesn't require running the full PC version of VRChat.

#### 1. Install Relay Server
```bash
# On your PC
pip install python-osc websockets
```

#### 2. Create `relay_server.py`
```python
import asyncio
import websockets
from pythonosc import udp_client, dispatcher, osc_server

class RelayServer:
    def __init__(self, local_port=9000, remote_port=9001):
        self.local_port = local_port
        self.remote_port = remote_port
        self.clients = set()
        self.osc_client = udp_client.SimpleUDPClient("127.0.0.1", remote_port)
        
    async def register(self, websocket):
        self.clients.add(websocket)
        print(f"New client connected. Total clients: {len(self.clients)}")
        
    async def unregister(self, websocket):
        self.clients.remove(websocket)
        print(f"Client disconnected. Remaining clients: {len(self.clients)}")
    
    async def forward_to_osc(self, message):
        # Forward WebSocket message to OSC
        # Format: "/osc/address value"
        try:
            path, *values = message.split()
            self.osc_client.send_message(path, [float(v) for v in values])
        except Exception as e:
            print(f"Error forwarding to OSC: {e}")
    
    async def forward_to_ws(self, path, *args):
        # Forward OSC message to WebSocket clients
        message = f"{path} {' '.join(map(str, args))}"
        if self.clients:
            await asyncio.wait([client.send(message) for client in self.clients])
    
    async def handler(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                await self.forward_to_osc(message)
        finally:
            await self.unregister(websocket)

async def start_osc_server(relay):
    disp = dispatcher.Dispatcher()
    disp.set_default_handler(relay.forward_to_ws)
    
    server = osc_server.AsyncIOOSCUDPServer(
        ("0.0.0.0", relay.local_port), 
        disp, 
        asyncio.get_event_loop()
    )
    transport, protocol = await server.create_serve_endpoint()
    
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        transport.close()

async def main():
    relay = RelayServer()
    
    # Start WebSocket server
    ws_server = await websockets.serve(
        relay.handler, 
        "0.0.0.0", 
        8765
    )
    
    # Start OSC server
    osc_task = asyncio.create_task(start_osc_server(relay))
    
    print("Relay server started. Press Ctrl+C to stop.")
    
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        ws_server.close()
        await ws_server.wait_closed()
        osc_task.cancel()
        await osc_task

if __name__ == "__main__":
    asyncio.run(main())
```

#### 3. Create Mobile App (Basic Example)
You'll need a simple mobile/web app to connect to the relay. Here's a basic example:

```html
<!-- index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>VRChat MCP Mobile</title>
    <style>
        button { padding: 15px; margin: 5px; font-size: 16px; }
        #status { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>VRChat MCP Control</h1>
    <div>
        <button onclick="sendCommand('/avatar/parameters/Wave', 1)">Wave</button>
        <button onclick="sendCommand('/avatar/parameters/Dance', 1)">Dance</button>
    </div>
    <div id="status">Disconnected</div>

    <script>
        let ws;
        const statusDiv = document.getElementById('status');
        
        function connect() {
            // Replace with your PC's local IP
            ws = new WebSocket('ws://YOUR_PC_IP:8765');
            
            ws.onopen = () => {
                statusDiv.textContent = 'Connected to MCP';
                statusDiv.style.color = 'green';
            };
            
            ws.onclose = () => {
                statusDiv.textContent = 'Disconnected. Retrying...';
                statusDiv.style.color = 'red';
                setTimeout(connect, 2000);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }
        
        function sendCommand(path, value) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(`${path} ${value}`);
            }
        }
        
        // Initial connection
        connect();
    </script>
</body>
</html>
```

## Interaction Scenarios

### 1. Basic Avatar Control
- **Setup**: Virtual Desktop + PC VRChat
- **Flow**:
  1. Launch VRChat through Virtual Desktop
  2. MCP detects your avatar
  3. Use MCP to control avatar parameters
  4. See real-time updates in VR

### 2. NPC Interactions
- **Setup**: Virtual Desktop + PC VRChat
- **Flow**:
  1. Enter a private instance
  2. MPC spawns NPCs (like the chambermaid)
  3. NPCs can be controlled via MCP commands
  4. See NPCs react to your actions

### 3. Environment Control
- **Setup**: Any method
- **Flow**:
  1. MCP sends OSC commands to control world parameters
  2. Adjust lighting, weather, or time of day
  3. See changes reflected in real-time

## Troubleshooting

### Common Issues
1. **Connection Timeout**
   - Ensure both devices are on the same network
   - Check Windows Firewall settings
   - Verify the correct IP address is used

2. **Latency**
   - Use 5GHz WiFi
   - Reduce streaming quality in Virtual Desktop
   - Close bandwidth-intensive applications

3. **OSC Not Working**
   - Enable OSC in VRChat settings
   - Check port numbers match (default is 9000)
   - Restart VRChat after changing settings

### Debugging
1. Check MCP server logs for connection attempts
2. Use a network analyzer like Wireshark for OSC traffic
3. Test with a simple OSC client like TouchOSC

## Next Steps
- [ ] Set up your PC and headset
- [ ] Test basic OSC functionality
- [ ] Try the example scenarios
- [ ] Customize the MCP for your needs
