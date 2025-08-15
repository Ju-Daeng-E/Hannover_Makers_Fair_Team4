#!/usr/bin/env python3
"""
Speed Sensor Test Script
Tests GPIO 16 for pulse detection and speed calculation
"""

import time
import signal
import sys
from speed_sensor import SpeedSensor

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n🛑 Stopping speed sensor test...')
    if 'sensor' in globals():
        sensor.stop()
    sys.exit(0)

def main():
    """Test speed sensor functionality"""
    print("🧪 Speed Sensor Test")
    print("=" * 40)
    print("📍 GPIO Pin: 16")
    print("🔄 Pulses per turn: 40")
    print("⚙️ Wheel diameter: 64mm")
    print("⏱️ Update interval: 1 second")
    print("=" * 40)
    print("🎯 Move the wheel to test pulse detection")
    print("📊 Press Ctrl+C to stop")
    print()
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create sensor
    global sensor
    sensor = SpeedSensor(gpio_pin=16, pulses_per_turn=40, wheel_diameter_mm=64)
    
    # Start sensor
    if not sensor.start():
        print("❌ Failed to start speed sensor")
        return
    
    print("✅ Speed sensor started - monitoring...")
    print()
    
    # Monitor loop
    last_counter = 0
    start_time = time.time()
    
    try:
        while True:
            # Get current data
            data = sensor.get_speed_data()
            
            # Check pulse counter directly
            with sensor.lock:
                current_counter = sensor.counter
            
            # Calculate pulse rate
            elapsed = time.time() - start_time
            total_pulses = current_counter + (data['rpm'] * sensor.pulses_per_turn * elapsed / 60)
            
            # Display status
            print(f"\r📊 Raw Pulses: {current_counter:4d} | "
                  f"RPM: {data['rpm']:4d} | "
                  f"Speed: {data['speed_kmh']:6.2f} km/h | "
                  f"Age: {data['age_seconds']:.1f}s | "
                  f"Fresh: {'✅' if data['age_seconds'] <= 2.0 else '❌'}", 
                  end="", flush=True)
            
            # Check for new pulses
            if current_counter != last_counter:
                print(f"\n🔔 Pulse detected! Count: {current_counter}")
                last_counter = current_counter
            
            time.sleep(0.1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sensor.stop()

if __name__ == "__main__":
    main()