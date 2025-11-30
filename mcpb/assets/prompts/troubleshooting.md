# Troubleshooting - VRChat-MCP

## OSC Connection Issues

### Problem: Parameters Not Changing

**Checklist:**
1. ✅ VRChat is running
2. ✅ OSC enabled (Settings → OSC)
3. ✅ Avatar has the parameter (case-sensitive!)
4. ✅ Parameter type correct (bool vs float vs int)
5. ✅ Port 9000 not blocked by firewall
6. ✅ Correct parameter value range

### Problem: Avatar Change Not Detected

**Solutions:**
- Listen for `/avatar/change` OSC message
- Re-query parameters after avatar change
- Reset parameter cache
- Verify OSC receive port (9001) open

---

## Parameter Issues

### Problem: Parameter Name Not Working

**Common causes:**
- Case sensitivity (Smile ≠ smile)
- Typo in parameter name
- Parameter doesn't exist on current avatar
- Parameter name changed in avatar update

**Debug:**
```python
# List all available parameters
params = list_avatar_parameters()
# Check exact spelling
```

### Problem: Value Not Updating

**Causes:**
- Parameter type mismatch (sending bool to float)
- Value out of range (float > 1.0)
- Animator not responding (Unity issue)
- Network latency

**Solutions:**
- Verify parameter type
- Check value range (0.0-1.0 for floats)
- Test in VRChat avatar menu first
- Add delay between changes

---

## VRChat-Specific Issues

### Problem: OSC Resets on World Change

**Expected behavior:**
- VRChat resets OSC on world/avatar change
- Need to re-establish parameters
- Cache parameter values and restore

### Problem: Parameters Work Locally, Not for Others

**Synced vs Local:**
- Only synced parameters visible to others
- Check parameter marked as "Synced" in Unity
- Local-only parameters for personal features
- Network smoothing may delay updates

---

## Troubleshooting Tools

### OSC Debugging
```python
# Enable OSC debug logging
enable_osc_debug(verbose=True)

# Monitor OSC traffic
monitor_osc_messages(duration=30)  # 30 seconds

# Test OSC connection
test_osc_connection(port=9000)
```

### Parameter Testing
```python
# Test parameter exists and works
test_parameter_response(
    param="TestFeature",
    value=True,
    timeout=2
)
```

---

**Austrian Troubleshooting**: Systematic, methodical, solution-focused! 🇦🇹🔧

