#!/usr/bin/env python3
"""
게임패드 연결 및 입력 테스트 스크립트
"""

import sys
import time
import threading
from datetime import datetime

try:
    from piracer.gamepads import ShanWanGamepad
    GAMEPAD_AVAILABLE = True
    print("✅ PiRacer gamepad module imported successfully")
except ImportError as e:
    print(f"❌ PiRacer gamepad not available: {e}")
    GAMEPAD_AVAILABLE = False

def test_gamepad_connection():
    """게임패드 연결 테스트"""
    print("\n🎮 Testing gamepad connection...")
    
    if not GAMEPAD_AVAILABLE:
        print("❌ PiRacer gamepad module not available")
        return False
    
    try:
        gamepad = ShanWanGamepad()
        print("✅ ShanWan Gamepad initialized successfully")
        return gamepad
    except Exception as e:
        print(f"❌ Failed to initialize gamepad: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

def test_gamepad_input(gamepad, duration=10):
    """게임패드 입력 테스트"""
    print(f"\n🎯 Testing gamepad input for {duration} seconds...")
    print("Press buttons and move sticks to test!")
    print("=" * 60)
    
    start_time = time.time()
    last_print = 0
    input_detected = False
    
    while time.time() - start_time < duration:
        try:
            # 게임패드 데이터 읽기
            data = gamepad.read_data()
            
            current_time = time.time()
            
            # 입력 변화 감지
            left_x = data.analog_stick_left.x
            left_y = data.analog_stick_left.y
            right_x = data.analog_stick_right.x
            right_y = data.analog_stick_right.y
            
            # 버튼 상태
            buttons = {
                'A': data.button_a,
                'B': data.button_b,
                'X': data.button_x,
                'Y': data.button_y,
                'L2': data.button_l2,
                'R2': data.button_r2
            }
            
            # 입력이 있는지 확인 (임계값 적용)
            threshold = 0.1
            has_input = (abs(left_x) > threshold or abs(left_y) > threshold or 
                        abs(right_x) > threshold or abs(right_y) > threshold or
                        any(buttons.values()))
            
            if has_input:
                input_detected = True
            
            # 매초마다 또는 입력이 있을 때 출력
            if current_time - last_print >= 1.0 or has_input:
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # 스틱 상태 표시
                stick_info = f"L:({left_x:+.2f},{left_y:+.2f}) R:({right_x:+.2f},{right_y:+.2f})"
                
                # 눌린 버튼 표시
                pressed_buttons = [name for name, pressed in buttons.items() if pressed]
                button_info = f"Buttons: {','.join(pressed_buttons) if pressed_buttons else 'None'}"
                
                # 상태 표시
                status = "🔥 INPUT!" if has_input else "⚪ idle"
                
                print(f"[{timestamp}] {status} {stick_info} {button_info}")
                last_print = current_time
            
            time.sleep(0.02)  # 50Hz
            
        except Exception as e:
            print(f"❌ Error reading gamepad: {e}")
            return False
    
    return input_detected

def test_continuous_monitoring():
    """연속 모니터링 테스트"""
    print("\n🔄 Continuous monitoring test (Ctrl+C to stop)")
    print("=" * 60)
    
    gamepad = test_gamepad_connection()
    if not gamepad:
        return
    
    try:
        last_values = None
        read_count = 0
        error_count = 0
        
        while True:
            try:
                data = gamepad.read_data()
                read_count += 1
                
                current_values = {
                    'left_x': data.analog_stick_left.x,
                    'left_y': data.analog_stick_left.y,
                    'right_x': data.analog_stick_right.x,
                    'right_y': data.analog_stick_right.y,
                    'button_a': data.button_a,
                    'button_b': data.button_b,
                    'button_x': data.button_x,
                    'button_y': data.button_y,
                }
                
                # 값이 변경되었거나 100회마다 출력
                if last_values != current_values or read_count % 100 == 0:
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"[{timestamp}] Read#{read_count:5d} Errors:{error_count:3d} "
                          f"L:({current_values['left_x']:+.2f},{current_values['left_y']:+.2f}) "
                          f"R:({current_values['right_x']:+.2f},{current_values['right_y']:+.2f}) "
                          f"ABXY:{current_values['button_a']}{current_values['button_b']}{current_values['button_x']}{current_values['button_y']}")
                    last_values = current_values.copy()
                
                time.sleep(0.02)  # 50Hz
                
            except Exception as e:
                error_count += 1
                print(f"❌ Read error #{error_count}: {e}")
                time.sleep(0.1)
                
                if error_count > 10:
                    print("❌ Too many errors, stopping...")
                    break
                    
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped. Total reads: {read_count}, Errors: {error_count}")

def check_system_info():
    """시스템 정보 확인"""
    print("\n🖥️ System Information:")
    print("=" * 40)
    
    # USB 장치 확인
    try:
        import subprocess
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        print("USB Devices:")
        for line in result.stdout.strip().split('\n'):
            if 'joystick' in line.lower() or 'gamepad' in line.lower() or 'controller' in line.lower():
                print(f"  🎮 {line}")
            else:
                print(f"     {line}")
    except Exception as e:
        print(f"Could not get USB info: {e}")
    
    # 입력 장치 확인
    try:
        import os
        print(f"\nInput devices in /dev/input/:")
        input_devices = [f for f in os.listdir('/dev/input/') if f.startswith('js') or f.startswith('event')]
        for device in sorted(input_devices):
            device_path = f"/dev/input/{device}"
            if os.access(device_path, os.R_OK):
                print(f"  ✅ {device} (readable)")
            else:
                print(f"  ❌ {device} (not readable)")
    except Exception as e:
        print(f"Could not check input devices: {e}")

def main():
    print("🎮 Gamepad Connection Test")
    print("=" * 50)
    
    # 시스템 정보 확인
    check_system_info()
    
    # 게임패드 연결 테스트
    gamepad = test_gamepad_connection()
    
    if not gamepad:
        print("\n❌ Cannot proceed without gamepad")
        print("\nTroubleshooting:")
        print("1. Check if gamepad is connected via USB")
        print("2. Check if gamepad is recognized: lsusb")
        print("3. Check permissions: ls -la /dev/input/js*")
        print("4. Try running as root: sudo python3 test_gamepad.py")
        return
    
    while True:
        print(f"\n{'='*50}")
        print("Choose test option:")
        print("1. Quick input test (10 seconds)")
        print("2. Extended input test (30 seconds)")
        print("3. Continuous monitoring (Ctrl+C to stop)")
        print("4. Exit")
        
        try:
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == '1':
                input_detected = test_gamepad_input(gamepad, 10)
                if input_detected:
                    print("✅ Gamepad input detected!")
                else:
                    print("⚠️ No input detected. Try moving sticks or pressing buttons.")
                    
            elif choice == '2':
                input_detected = test_gamepad_input(gamepad, 30)
                if input_detected:
                    print("✅ Gamepad input detected!")
                else:
                    print("⚠️ No input detected. Check gamepad connection.")
                    
            elif choice == '3':
                test_continuous_monitoring()
                
            elif choice == '4':
                break
                
            else:
                print("Invalid choice. Please enter 1-4.")
                
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()