#!/usr/bin/env python3
"""
Simple test for vehicle system with camera integration
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from vehicle_main import VehicleSystem

def main():
    print("🚗 Testing RC Car Vehicle System with Camera")
    print("=" * 50)
    
    # Use different ports to avoid conflicts
    LISTEN_PORT = 8889      # Different port for controller
    CAMERA_PORT = 8081      # Different port for camera
    
    print(f"📡 Controller port: {LISTEN_PORT}")
    print(f"📹 Camera stream port: {CAMERA_PORT}")
    print("=" * 50)
    
    vehicle = VehicleSystem(LISTEN_PORT, CAMERA_PORT)
    
    try:
        vehicle.run()
    except KeyboardInterrupt:
        print("\n🛑 Stopping test...")
        vehicle.cleanup()

if __name__ == "__main__":
    main()