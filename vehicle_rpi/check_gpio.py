#!/usr/bin/env python3
"""
GPIO Test Script - Check GPIO 16 status and manual pulse detection
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("❌ RPi.GPIO not available")
    sys.exit(1)

def test_gpio_manual():
    """Manual GPIO testing"""
    print("🧪 GPIO 16 Manual Test")
    print("=" * 30)
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print("📊 Reading GPIO 16 state (Ctrl+C to stop)")
    print("💡 Try manually connecting/disconnecting GPIO 16 to GND")
    print()
    
    last_state = None
    pulse_count = 0
    
    try:
        while True:
            current_state = GPIO.input(16)
            
            if current_state != last_state:
                if last_state is not None:
                    pulse_count += 1
                    print(f"🔔 State change: {last_state} → {current_state} (Pulse #{pulse_count})")
                
                last_state = current_state
            
            print(f"\rGPIO 16 State: {current_state} | Pulses: {pulse_count}", end="", flush=True)
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print(f"\n\n✅ Test completed. Total pulses detected: {pulse_count}")
        GPIO.cleanup()

def test_gpio_interrupt():
    """Test GPIO interrupt capability"""
    print("🧪 GPIO 16 Interrupt Test")
    print("=" * 30)
    
    pulse_count = 0
    
    def pulse_callback(channel):
        nonlocal pulse_count
        pulse_count += 1
        print(f"🔔 Interrupt! Pulse #{pulse_count} on GPIO {channel}")
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    try:
        # Try different edge detection methods
        print("📍 Testing RISING edge detection...")
        GPIO.add_event_detect(16, GPIO.RISING, callback=pulse_callback, bouncetime=50)
        
        print("⏳ Waiting for pulses... (10 seconds)")
        time.sleep(10)
        
        GPIO.remove_event_detect(16)
        print(f"✅ RISING test completed. Pulses: {pulse_count}")
        
        # Reset counter
        pulse_count = 0
        
        print("\n📍 Testing BOTH edge detection...")
        GPIO.add_event_detect(16, GPIO.BOTH, callback=pulse_callback, bouncetime=1)
        
        print("⏳ Waiting for pulses... (10 seconds)")
        time.sleep(10)
        
        GPIO.remove_event_detect(16)
        print(f"✅ BOTH test completed. Pulses: {pulse_count}")
        
    except Exception as e:
        print(f"❌ Interrupt test failed: {e}")
    finally:
        GPIO.cleanup()

def main():
    """Main test function"""
    print("🔧 GPIO 16 Test Suite")
    print("=" * 40)
    print("1. Manual state reading")
    print("2. Interrupt detection test")
    print("=" * 40)
    
    choice = input("Select test (1 or 2): ").strip()
    
    if choice == "1":
        test_gpio_manual()
    elif choice == "2":
        test_gpio_interrupt()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()