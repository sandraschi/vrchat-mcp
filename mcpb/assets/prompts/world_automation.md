# World Automation - VRChat-MCP

## World OSC Integration

### World Triggers
```python
# Activate world object via OSC
send_world_trigger(
    address="/world/trigger/DoorOpen",
    value=True
)

Common world interactions:
- Doors, elevators
- Game mechanics
- Music/video players
- Lighting systems
- Particle effects
```

### Game Mechanics
```
World games via OSC:
- Score updates
- Game state changes
- Player actions
- Round triggers
- Reset commands
```

### Environmental Control
```python
# Control world lighting
set_world_parameter("/world/lighting/intensity", 0.8)

# Trigger effects
trigger_world_event("/world/effects/fireworks", True)

# Music control
set_world_parameter("/world/music/volume", 0.5)
```

---

## World-Specific Automation

**Event Worlds**: Join events, trigger interactions  
**Game Worlds**: Automate game actions  
**Performance Worlds**: Choreograph shows  
**Social Worlds**: Automated greetings, activities

---

**Austrian World Control**: Precise, timely, engaging! 🇦🇹🌍

