#!/usr/bin/env python3
"""
Quick test to check websockets import
"""

import sys
print("Python version:", sys.version)
print("Python path:", sys.path)

try:
    import websockets
    print("✅ websockets import successful")
    print("websockets version:", websockets.__version__)
    print("websockets location:", websockets.__file__)
except ImportError as e:
    print("❌ websockets import failed:", e)
    sys.exit(1)

# Test basic functionality
import asyncio
print("✅ asyncio available")

print("🎉 All tests passed!")