#!/usr/bin/env python3
"""
Simple GPIO 16 Test - Direct manual reading
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("❌ RPi.GPIO not available")
    sys.exit(1)

def main():
    """Simple GPIO reading test"""
    print("🧪 Simple GPIO 16 Test")
    print("=" * 30)
    print("📍 Reading GPIO 16 state for 30 seconds")
    print("💡 Try manually moving/spinning the encoder wheel")
    print("📊 Monitoring...")
    print()
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    last_state = None
    change_count = 0
    start_time = time.time()
    
    try:
        while time.time() - start_time < 30:  # Run for 30 seconds
            current_state = GPIO.input(16)
            
            if current_state != last_state and last_state is not None:
                change_count += 1
                timestamp = time.time() - start_time
                print(f"🔔 {timestamp:.2f}s: State change #{change_count}: {last_state} → {current_state}")
            
            last_state = current_state
            time.sleep(0.001)  # 1ms polling
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    finally:
        elapsed = time.time() - start_time
        print(f"\n✅ Test completed")
        print(f"⏱️ Time: {elapsed:.1f} seconds")
        print(f"🔢 Total state changes: {change_count}")
        print(f"📊 Changes per second: {change_count/elapsed:.2f}")
        GPIO.cleanup()

if __name__ == "__main__":
    main()