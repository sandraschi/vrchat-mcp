# Avatar Control Guide - VRChat-MCP

## OSC Avatar Parameter Control

### Parameter Types

**Bool Parameters (Toggle)**:
```python
# Enable/disable features
set_parameter("Wings", True)  # Show wings
set_parameter("Hat", False)   # Hide hat
set_parameter("Glow", True)   # Enable glow effect
```

**Float Parameters (Continuous)**:
```python
# Adjust continuous values (0.0 to 1.0)
set_parameter("EarRotate", 0.5)    # 50% rotation
set_parameter("TailWag", 1.0)      # Maximum wag speed
set_parameter("Smile", 0.75)       # 75% smile intensity
```

**Int Parameters (Selection)**:
```python
# Select from multiple options
set_parameter("OutfitSelect", 2)   # Outfit #2
set_parameter("HatType", 0)        # Hat style 0
set_parameter("Accessory", 3)      # Accessory slot 3
```

### Expression System
```
VRM Standard Expressions:
- Joy (happy, smiling)
- Angry (mad, frustrated)
- Sorrow (sad, crying)
- Fun (excited, enthusiastic)
- Surprise (shocked, amazed)
- Neutral (resting)
- Blink / Blink_L / Blink_R

Trigger via OSC:
set_parameter("Expression_Joy", 1.0)
set_parameter("Expression_Angry", 0.0)
```

### Gesture Control
```python
# Left and right hand gestures
set_gesture_left(1)   # Fist
set_gesture_right(7)  # Thumbs up

# Gesture combinations for animations
set_gesture_left(2)   # Open hand (wave)
set_gesture_right(3)  # Point
```

---

## Avatar Automation Workflows

### Expression Sequences
```python
# Animated expression sequence
async def expression_sequence():
    await set_parameter("Expression_Neutral", 1.0)
    await asyncio.sleep(1)
    await set_parameter("Expression_Joy", 1.0)
    await asyncio.sleep(2)
    await set_parameter("Expression_Neutral", 1.0)

# Creates: Neutral → Happy → Neutral flow
```

### Avatar State Presets
```python
# Save current state
save_avatar_state(name="Default")

# Preset: Casual outfit
load_preset("Casual", {
    "Jacket": True,
    "Hat": False,
    "Glasses": True,
    "OutfitSelect": 0
})

# Preset: Formal outfit
load_preset("Formal", {
    "Jacket": False,
    "Tie": True,
    "Hat": True,
    "OutfitSelect": 1
})
```

### Performance Choreography
```python
# Synchronized dance routine
async def dance_routine():
    # Wave hello
    await set_gesture_both(2)  # Open hands
    await asyncio.sleep(1)
    
    # Point forward
    await set_gesture_both(3)
    await asyncio.sleep(1)
    
    # Peace signs
    await set_gesture_both(4)
    await asyncio.sleep(2)
    
    # Back to neutral
    await set_gesture_both(0)
```

---

## Parameter Discovery

### Finding Avatar Parameters
```python
# List all available parameters
params = get_available_parameters()

Returns:
- Parameter names
- Parameter types (bool, float, int)
- Current values
- Default values
```

### Testing Parameters
```python
# Test parameter (safely)
test_parameter(
    name="NewFeature",
    type="bool",
    test_value=True,
    duration=5  # Test for 5 seconds, then revert
)
```

---

## Best Practices

**Parameter Naming** (for avatar creators):
- Clear, descriptive names
- CamelCase convention
- Group related params (Ear_Left, Ear_Right)
- Avoid special characters

**Control Timing**:
- Don't spam (allow time between changes)
- Smooth transitions for floats
- Respect animation durations
- Consider network latency

**Social Awareness**:
- Appropriate expressions for context
- Don't be distracting in serious moments
- Respect personal space
- VRChat etiquette matters

---

**Austrian Precision**: Smooth, synchronized, socially aware avatar control! 🇦🇹👤

