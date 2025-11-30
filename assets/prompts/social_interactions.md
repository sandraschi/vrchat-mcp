# Social Interactions - VRChat-MCP

## VRChat Social Automation

### Chatbox Automation
```python
# Send message to chatbox
send_chatbox(
    message="Hello everyone! 👋",
    sound=True,  # Typing sound
    immediate=True  # Send immediately
)

Use cases:
- Greetings on world join
- Automated announcements
- Status updates
- Responses to events
```

### Expression Reactions
```python
# React to events
async def react_to_compliment():
    # Blush and smile
    await set_parameter("Blush", True)
    await set_parameter("Expression_Joy", 1.0)
    await asyncio.sleep(3)
    await set_parameter("Blush", False)
    await set_parameter("Expression_Neutral", 1.0)
```

### Gesture Automation
```python
# Wave sequence
async def wave_hello():
    await set_gesture_right(2)  # Open hand
    for _ in range(3):
        await asyncio.sleep(0.5)
        # Wave animation via avatar
    await set_gesture_right(0)  # Neutral
```

---

## Social VR Etiquette

**Do**:
- ✅ Use appropriate expressions for context
- ✅ Respect personal boundaries
- ✅ Ask before demonstrating features
- ✅ Mute when not speaking
- ✅ Use gestures to communicate

**Don't**:
- ❌ Spam expressions or gestures
- ❌ Be disruptive with animations
- ❌ Use automation for trolling
- ❌ Ignore social cues
- ❌ Be obnoxious

---

**Austrian Social VR**: Friendly, respectful, considerate! 🇦🇹🤝

