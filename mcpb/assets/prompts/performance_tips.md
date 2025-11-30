# Performance Tips - VRChat-MCP

## OSC Performance Optimization

### Message Rate Limiting
```
Best practices:
- Max 60 messages/second (typical)
- Bundle related parameters
- Use delta compression (only send changes)
- Batch operations when possible

Avoid:
- Sending same value repeatedly
- High-frequency polling
- Unnecessary parameter updates
```

### Parameter Efficiency
```python
# Efficient: Single batch update
batch_update_parameters({
    "Smile": 1.0,
    "Eyes_Happy": True,
    "Blush": True
})

# Inefficient: Multiple separate calls
set_parameter("Smile", 1.0)
set_parameter("Eyes_Happy", True)
set_parameter("Blush", True)
```

### Network Optimization
```
Tips:
- Local OSC (localhost) - lowest latency
- Wired connection preferred
- Reduce other network activity
- Monitor packet loss
- Use UDP efficiently
```

---

## Avatar Performance

### Parameter Count
```
VRChat limits:
- 128 synced parameters (transmitted to others)
- 16 bools (1-bit each)
- 16 ints (8-bit each)
- 16 floats (8-bit each)

Optimize:
- Use bool for simple toggles
- Use int for multiple states (not multiple bools)
- Float only when continuous needed
```

### Animator Optimization
```
Animator controller:
- Minimize layers
- Use write defaults off (recommended)
- Combine parameters where possible
- Remove unused states
- Optimize transition conditions
```

---

**Austrian Performance**: Efficient, smooth, lag-free! 🇦🇹⚡

