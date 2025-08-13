# VRChat MCP Debug Interface

The VRChat MCP Debug Interface is a web-based tool for monitoring and interacting with the VRChat MCP server in real-time. It provides a user-friendly interface to visualize OSC messages, inspect avatar states, and send test commands.

## Features

- **Real-time OSC Monitoring**: View incoming and outgoing OSC messages with timestamps and direction indicators.
- **Message Filtering**: Filter messages by address patterns, direction, and value ranges.
- **Parameter Visualization**: See the current state of avatar parameters and their values.
- **Interactive Testing**: Send test OSC messages directly from the interface.
- **Connection Statistics**: Monitor message rates, bandwidth usage, and connection status.
- **Responsive Design**: Works on both desktop and mobile devices.

## Getting Started

### Prerequisites

- VRChat MCP server running
- Python 3.8+
- Modern web browser (Chrome, Firefox, Edge, or Safari)

### Installation

The debug interface is included with the VRChat MCP package. No additional installation is required.

### Starting the Debug Interface

1. Ensure the VRChat MCP server is running with the debug UI enabled (enabled by default).
2. Open a web browser and navigate to:
   ```
   http://localhost:8765
   ```
3. The debug interface should load automatically.

## User Guide

### Interface Overview

1. **Connection Status**: Shows whether the debug interface is connected to the MCP server.
2. **Message List**: Displays a table of OSC messages with timestamps, direction, address, and arguments.
3. **Filter Controls**: Filter messages by address pattern and direction.
4. **Status Panel**: Shows connection statistics and message counts.
5. **Send Message Panel**: Send test OSC messages to the MCP server.

### Filtering Messages

1. In the "Address Filter" field, enter a pattern to match message addresses (supports wildcards).
2. Use the "Direction" dropdown to filter by message direction (Incoming, Outgoing, or All).
3. Click "Apply Filters" to update the message list.

### Sending Test Messages

1. Enter an OSC address in the "Address" field (e.g., "/avatar/parameters/Example").
2. Enter a value in the "Value" field (supports numbers, booleans, and strings).
3. Click "Send Message" to send the OSC message.

### Keyboard Shortcuts

- `Ctrl + F` or `Cmd + F`: Focus the address filter field
- `Ctrl + P` or `Cmd + P`: Pause/resume message updates
- `Ctrl + L` or `Cmd + L`: Clear all messages
- `Esc`: Clear the current selection/filter

## Troubleshooting

### Debug Interface Won't Start

1. Ensure the MCP server is running with debug UI enabled.
2. Check that port 8765 is not in use by another application.
3. Verify that your firewall allows incoming connections on port 8765.

### No Messages Appearing

1. Check that the MCP server is receiving/sending OSC messages.
2. Verify that the filters aren't hiding all messages.
3. Ensure the MCP server is configured with the correct OSC ports.

### High CPU Usage

If the debug interface is using too much CPU:
1. Pause message updates when not needed.
2. Use more specific filters to reduce the number of messages displayed.
3. Increase the "Max Messages" limit to reduce UI updates.

## Development

### Building the Frontend

The debug interface frontend is built with vanilla JavaScript, HTML, and CSS. To make changes:

1. Edit the files in `src/vrchat_mcp/web/`.
2. The changes will be automatically picked up when the MCP server is restarted.

### Adding New Features

1. Add new WebSocket message handlers in `debug_ui.py`.
2. Update the frontend JavaScript to handle the new messages.
3. Add any necessary UI components to the HTML and style them with CSS.

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
