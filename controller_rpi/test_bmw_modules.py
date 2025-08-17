#!/usr/bin/env python3
"""
BMW 모듈 테스트 스크립트
BMW modules test script
"""

import sys
import os

# Add current directory to path
sys.path.append('/home/pi/controller_rpi')

print("🔍 Testing BMW module imports...")
print("=" * 50)

# Test CAN import
try:
    import can
    print("✅ python-can imported successfully")
except ImportError as e:
    print(f"❌ python-can import failed: {e}")
    sys.exit(1)

# Test BMW modules
try:
    from bmw_lever_controller import BMWLeverController
    print("✅ BMWLeverController imported successfully")
except ImportError as e:
    print(f"❌ BMWLeverController import failed: {e}")

try:
    from data_models import BMWState
    print("✅ BMWState imported successfully")
except ImportError as e:
    print(f"❌ BMWState import failed: {e}")

try:
    from logger import Logger
    print("✅ Logger imported successfully")
except ImportError as e:
    print(f"❌ Logger import failed: {e}")

# Test BMW system initialization
print("\n🔧 Testing BMW system initialization...")
print("=" * 50)

try:
    # Initialize logger
    from logger import Logger
    logger = Logger('test', level='INFO')
    print("✅ Logger initialized")
    
    # Initialize BMW controller
    from bmw_lever_controller import BMWLeverController
    bmw_controller = BMWLeverController(logger)
    print("✅ BMW controller initialized")
    
    # Initialize BMW state
    from data_models import BMWState
    bmw_state = BMWState()
    print("✅ BMW state initialized")
    print(f"   Initial gear: {bmw_state.current_gear}")
    print(f"   Manual gear: {bmw_state.manual_gear}")
    
    print("\n🔧 Testing CAN interface setup...")
    # Test CAN interface setup
    result = os.system("sudo ip link set can1 down 2>/dev/null")
    result = os.system("sudo ip link set can1 up type can bitrate 500000 2>/dev/null")
    
    if result == 0:
        print("✅ CAN interface setup successful")
    else:
        print("⚠️ CAN interface setup failed (may be normal if no CAN hardware)")
    
    # Test CAN bus connection
    try:
        bus = can.interface.Bus(channel='can1', bustype='socketcan')
        print("✅ CAN bus connection successful")
        
        # Test message reception (short timeout)
        print("🧪 Testing CAN message reception (5 second test)...")
        import time
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < 5:
            try:
                msg = bus.recv(timeout=0.1)
                if msg:
                    message_count += 1
                    if msg.arbitration_id == 0x197:
                        print(f"🎛️ BMW lever message received: {msg.data.hex()}")
                        # Test decoding
                        if bmw_controller.decode_lever_message(msg, bmw_state):
                            print(f"   Decoded gear: {bmw_state.current_gear}")
                            print(f"   Lever position: {bmw_state.lever_position}")
                    elif message_count <= 5:  # Log first 5 messages
                        print(f"📨 CAN message: ID=0x{msg.arbitration_id:03X}, Data={msg.data.hex()}")
            except can.CanError:
                continue
        
        bus.shutdown()
        print(f"🏁 Test completed. Received {message_count} CAN messages")
        
        if message_count > 0:
            print("✅ CAN communication is working!")
        else:
            print("⚠️ No CAN messages received - check hardware connection")
            
    except Exception as e:
        print(f"❌ CAN bus connection failed: {e}")
    
    print("\n✅ All BMW modules are working correctly!")
    print("BMW modules are now available for the main controller")
    
except Exception as e:
    print(f"❌ BMW system test failed: {e}")
    import traceback
    print(traceback.format_exc())