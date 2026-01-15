# Debug Flags Documentation

## Overview

The AI Storybook Generator includes toggleable debug flags to control expensive/time-consuming features during development and testing.

## Location

Debug flags are defined at the top of `services/generator.py`:

```python
# ============================================
# DEBUG FLAGS - Toggle features on/off
# ============================================
ENABLE_AUDIO = False      # Set to True to generate audio narration (adds ~30-60s)
ENABLE_IMAGES = False     # Set to True to generate story images (adds ~2-3 min)
# ============================================
```