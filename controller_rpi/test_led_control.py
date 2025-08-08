#!/usr/bin/env python3
"""
BMW LED 제어 테스트 스크립트
BMW LED control test script
"""

import sys
import os
import can
import time

# Add current directory to path
sys.path.append('/home/pi/controller_rpi')

print("🔍 BMW LED Control Test")
print("=" * 50)

# Setup CAN interface
print("🔧 Setting up CAN interface...")
os.system("sudo ip link set can1 down 2>/dev/null")
result = os.system("sudo ip link set can1 up type can bitrate 500000 2>/dev/null")

if result != 0:
    print("❌ CAN interface setup failed")
    sys.exit(1)

print("✅ CAN interface setup successful")

# Connect to CAN bus
try:
    bus = can.interface.Bus(channel='can1', interface='socketcan')
    print("✅ CAN bus connected")
except Exception as e:
    print(f"❌ CAN bus connection failed: {e}")
    sys.exit(1)

def send_led_message(gear_code, flash=False):
    """Send BMW LED message with proper formatting"""
    try:
        # BMW LED message format for 3FD
        # Byte 0: CRC (calculated later)
        # Byte 1: Counter (0x01-0x0F cycling)
        # Byte 2: Gear LED code
        # Byte 3: Additional flags
        
        counter = 0x01  # Simple counter for test
        flags = 0x00
        
        # Create payload without CRC first
        payload_without_crc = [counter, gear_code, flags, 0x00]
        
        # Simple CRC calculation (BMW 3FD style)
        # This is a simplified version - you might need to adjust
        crc = 0
        for byte in payload_without_crc:
            crc ^= byte
        
        # Final payload
        payload = [crc] + payload_without_crc
        
        message = can.Message(
            arbitration_id=0x3FD,
            data=payload,
            is_extended_id=False
        )
        
        bus.send(message)
        print(f"💡 LED message sent: ID=0x3FD, Data={bytes(payload).hex().upper()}")
        print(f"   Gear Code: 0x{gear_code:02X}, Counter: 0x{counter:02X}")
        return True
        
    except Exception as e:
        print(f"❌ LED send error: {e}")
        return False

def send_heartbeat():
    """Send heartbeat message to keep system alive"""
    try:
        # BMW heartbeat message 0x55E
        payload = [0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x5E]
        
        message = can.Message(
            arbitration_id=0x55E,
            data=payload,
            is_extended_id=False
        )
        
        bus.send(message)
        print(f"💓 Heartbeat sent: ID=0x55E, Data={bytes(payload).hex().upper()}")
        return True
        
    except Exception as e:
        print(f"❌ Heartbeat send error: {e}")
        return False

# Test different gear codes
gear_codes = {
    'P': 0x20,    # Park
    'R': 0x40,    # Reverse  
    'N': 0x60,    # Neutral
    'D': 0x80,    # Drive
    'S': 0x81,    # Sport/Manual
}

print("\n🧪 Testing BMW LED Control...")
print("This will cycle through different gear LEDs")
print("Watch the BMW gear lever for LED changes!")
print("=" * 50)

try:
    for round_num in range(3):  # 3 rounds of testing
        print(f"\n🔄 Round {round_num + 1}/3")
        
        for gear_name, gear_code in gear_codes.items():
            print(f"\n🎯 Setting gear LED to: {gear_name}")
            
            # Send heartbeat first
            send_heartbeat()
            time.sleep(0.1)
            
            # Send LED message multiple times for reliability
            for i in range(5):
                success = send_led_message(gear_code)
                if success:
                    print(f"   ✅ LED message {i+1}/5 sent successfully")
                else:
                    print(f"   ❌ LED message {i+1}/5 failed")
                time.sleep(0.2)
            
            print(f"   ⏳ Waiting 2 seconds for LED to activate...")
            time.sleep(2)
        
        print(f"\n✅ Round {round_num + 1} completed")
        time.sleep(1)

    print("\n🎯 Testing rapid LED changes...")
    # Test rapid changes to see if timing is the issue
    for i in range(10):
        gear_code = [0x20, 0x40, 0x60, 0x80, 0x81][i % 5]
        gear_name = ['P', 'R', 'N', 'D', 'S'][i % 5]
        
        send_led_message(gear_code)
        print(f"⚡ Rapid test {i+1}/10: {gear_name}")
        time.sleep(0.5)

    print("\n🎯 Testing continuous LED updates...")
    # Test continuous updates (like a real system)
    for i in range(20):
        send_led_message(0x60)  # Keep sending Neutral
        if i % 5 == 0:
            send_heartbeat()
            print(f"🔄 Continuous update {i+1}/20")
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n🛑 Test interrupted by user")

except Exception as e:
    print(f"\n❌ Test error: {e}")

finally:
    bus.shutdown()
    print("\n✅ LED control test completed")
    print("\n🔍 If LEDs still don't work, the issue might be:")
    print("   1. Hardware connection problem")
    print("   2. BMW gear lever power/initialization issue") 
    print("   3. CAN message format not matching expected protocol")
    print("   4. Missing additional initialization messages")