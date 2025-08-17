#!/usr/bin/env python3
"""
BMW CAN 모니터링 디버그 스크립트
BMW CAN monitoring debug script
"""

import sys
import os
import can
import time
import threading

# Add current directory to path
sys.path.append('/home/pi/controller_rpi')

from bmw_lever_controller import BMWLeverController
from data_models import BMWState
from logger import Logger

print("🔍 BMW CAN Monitoring Debug")
print("=" * 50)

# Initialize components
logger = Logger('debug', level='INFO')
bmw_controller = BMWLeverController(logger)
bmw_state = BMWState()

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

print("\n🔧 Starting BMW monitoring with detailed logging...")
print("Monitoring for 30 seconds...")
print("Move the BMW gear lever to see messages!")
print("=" * 50)

running = True

def bmw_monitor():
    """BMW gear monitoring with detailed debug"""
    global running
    message_count = 0
    bmw_messages = 0
    
    try:
        while running:
            try:
                msg = bus.recv(timeout=1.0)
                if msg:
                    message_count += 1
                    
                    # Log all messages for first 20 seconds
                    if time.time() - start_time < 20:
                        print(f"📨 CAN Message #{message_count}: ID=0x{msg.arbitration_id:03X}, Data={msg.data.hex().upper()}")
                    
                    # Process BMW lever messages
                    if msg.arbitration_id == 0x197:
                        bmw_messages += 1
                        print(f"🎛️ BMW LEVER MESSAGE #{bmw_messages}:")
                        print(f"   ID: 0x{msg.arbitration_id:03X}")
                        print(f"   Data: {msg.data.hex().upper()}")
                        print(f"   Raw bytes: {[hex(b) for b in msg.data]}")
                        
                        # Decode the message
                        if len(msg.data) >= 4:
                            crc = msg.data[0]
                            counter = msg.data[1] 
                            lever_pos = msg.data[2]
                            park_btn = msg.data[3]
                            
                            print(f"   CRC: 0x{crc:02X}")
                            print(f"   Counter: 0x{counter:02X}")
                            print(f"   Lever Position: 0x{lever_pos:02X}")
                            print(f"   Park/Unlock Buttons: 0x{park_btn:02X}")
                            
                            # Try to decode with controller
                            old_gear = bmw_state.current_gear
                            if bmw_controller.decode_lever_message(msg, bmw_state):
                                print(f"   ✅ Decoded successfully!")
                                print(f"   Gear: {old_gear} → {bmw_state.current_gear}")
                                print(f"   Lever: {bmw_state.lever_position}")
                                print(f"   Park Button: {bmw_state.park_button}")
                                print(f"   Unlock Button: {bmw_state.unlock_button}")
                                
                                # Send LED update
                                try:
                                    bmw_controller.send_gear_led(bus, bmw_state.current_gear)
                                    print(f"   💡 LED update sent for gear: {bmw_state.current_gear}")
                                except Exception as led_error:
                                    print(f"   ❌ LED update failed: {led_error}")
                            else:
                                print(f"   ❌ Decode failed!")
                        else:
                            print(f"   ❌ Invalid message length: {len(msg.data)}")
                        
                        print("-" * 30)
                    
                    # Send heartbeat every 100 messages
                    if message_count % 100 == 0:
                        print(f"📊 Total messages: {message_count}, BMW messages: {bmw_messages}")
                        
            except can.CanError as e:
                if "timeout" not in str(e).lower():
                    print(f"⚠️ CAN error: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Monitor error: {e}")
    finally:
        print(f"\n🏁 Monitoring stopped")
        print(f"📊 Final stats: {message_count} total messages, {bmw_messages} BMW lever messages")

# Start monitoring in separate thread
start_time = time.time()
monitor_thread = threading.Thread(target=bmw_monitor, daemon=True)
monitor_thread.start()

# Let it run for 30 seconds
try:
    time.sleep(30)
except KeyboardInterrupt:
    print("\n🛑 Interrupted by user")

running = False
monitor_thread.join(timeout=2)

bus.shutdown()
print("✅ Debug session completed")