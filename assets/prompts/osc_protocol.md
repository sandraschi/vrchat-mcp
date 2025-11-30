# OSC Protocol Reference - VRChat-MCP

## OSC Basics

### VRChat OSC Setup
```
Enable OSC in VRChat:
1. Launch VRChat
2. Settings → OSC
3. Enable OSC
4. Default ports: 9000 (send to VRChat), 9001 (receive from VRChat)
```

### OSC Message Format
```
Address: /avatar/parameters/ParameterName
Value: Type-specific (bool: 0/1, float: 0.0-1.0, int: varies)

Example:
/avatar/parameters/Smile = 1.0 (float, full smile)
/avatar/parameters/Hat = 1 (bool, hat enabled)
/avatar/parameters/OutfitSelect = 2 (int, outfit #2)
```

## VRChat OSC Address Space

### Avatar Parameters
```
/avatar/parameters/{param}
- Your custom avatar parameters
- Read/write
- Case-sensitive!

/avatar/change
- Triggered when avatar changes
- Receive only
- Indicates need to re-discover parameters
```

### Input Simulation
```
/input/Jump - Jump action
/input/Run - Toggle run
/input/MoveForward - Move forward (float 0-1)
/input/MoveBackward - Move back
/input/LookLeft - Look left
/input/ComfortTurnLeft - Snap turn left
/input/Voice - Push-to-talk (float 0-1)
```

### Tracking Data (Receive)
```
/tracking/trackers/{index}/position
/tracking/trackers/{index}/rotation
/tracking/vrsystem/Ready
```

### Chatbox
```
/chatbox/input
- message (string)
- send_immediately (bool)
- bypass_keyboard (bool, skip typing animation)
```

---

## OSC Best Practices

**Sending**:
- Don't flood (max ~60 messages/sec)
- Bundle related changes
- Use appropriate data types
- Validate parameter names

**Receiving**:
- Handle avatar changes gracefully
- Re-discover parameters on avatar change
- Log unexpected messages
- Filter noise

---

**Austrian OSC**: Precise, efficient, reliable communication! 🇦🇹📡

