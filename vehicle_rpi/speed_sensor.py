#!/usr/bin/env python3
"""
Speed Sensor Module for RC Car Vehicle
Reads encoder pulses from GPIO 16 and calculates RPM and speed
"""

import time
import threading
import logging
from datetime import datetime

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("⚠️ RPi.GPIO not available - speed sensor disabled")
    GPIO_AVAILABLE = False

class SpeedSensor:
    """Speed sensor handler using rotary encoder"""
    
    def __init__(self, gpio_pin: int = 16, pulses_per_turn: int = 40, wheel_diameter_mm: int = 64, 
                 simulation_mode: bool = False):
        self.gpio_pin = gpio_pin
        self.pulses_per_turn = pulses_per_turn
        self.wheel_diameter_mm = wheel_diameter_mm
        self.simulation_mode = simulation_mode
        
        # Speed calculation variables
        self.counter = 0
        self.previous_time = 0
        self.debounce_time = 500  # microseconds (0.5ms) - reduced for better responsiveness
        self.calculation_interval = 0.2  # seconds - 5x faster updates
        
        # Current values
        self.current_rpm = 0
        self.current_speed_kmh = 0.0
        self.last_update = time.time()
        
        # Threading
        self.running = False
        self.calculation_thread = None
        self.simulation_thread = None
        self.lock = threading.Lock()
        
        # Simulation variables
        self.sim_speed_kmh = 0.0
        self.sim_direction = 1
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize GPIO (only if not in simulation mode)
        if not self.simulation_mode:
            self.setup_gpio()
        else:
            self.logger.info("🎮 Speed sensor in simulation mode")
    
    def setup_gpio(self):
        """Setup GPIO for encoder input (polling mode)"""
        if not GPIO_AVAILABLE:
            self.logger.error("❌ GPIO not available")
            return False
        
        try:
            # Cleanup any existing GPIO setup
            try:
                GPIO.cleanup()
            except:
                pass
            
            # Setup GPIO mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Initialize state for polling
            self.last_state = GPIO.input(self.gpio_pin)
            
            self.logger.info(f"✅ Speed sensor initialized on GPIO {self.gpio_pin} (polling mode)")
            self.logger.info(f"🔍 Initial GPIO{self.gpio_pin} state: {self.last_state}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ GPIO setup failed: {e}")
            return False
    
    def count_pulses_polling(self):
        """Polling method to count encoder pulses with debouncing"""
        if not hasattr(self, 'last_state'):
            return
            
        current_state = GPIO.input(self.gpio_pin)
        current_time = time.time() * 1000000  # Convert to microseconds
        
        # Edge detection (state change)
        if current_state != self.last_state:
            # Software debouncing
            if current_time - self.previous_time >= self.debounce_time:
                with self.lock:
                    self.counter += 1
                self.previous_time = current_time
                # Debug logging for pulse detection
                if self.counter % 10 == 0:  # Log every 10 pulses
                    self.logger.info(f"[PULSE] Count: {self.counter}")
        
        # Update state
        self.last_state = current_state
    
    def calculate_speed(self):
        """Calculate RPM and speed from pulse count - HIGH PRIORITY THREAD"""
        # Skip priority changes for system stability
            
        while self.running:
            time.sleep(self.calculation_interval)
            
            if self.simulation_mode:
                # Simulation logic - create varying speed
                with self.lock:
                    # Simulate speed changes (0-30 km/h oscillating)
                    self.sim_speed_kmh += self.sim_direction * 2.0
                    if self.sim_speed_kmh >= 30.0:
                        self.sim_direction = -1
                    elif self.sim_speed_kmh <= 0.0:
                        self.sim_direction = 1
                    
                    # Calculate corresponding RPM
                    wheel_circumference_m = 3.14159 * (self.wheel_diameter_mm / 1000.0)
                    rpm_calculated = (self.sim_speed_kmh * 1000) / (wheel_circumference_m * 60)
                    
                    self.current_rpm = int(rpm_calculated)
                    self.current_speed_kmh = self.sim_speed_kmh
                    self.last_update = time.time()
                
                # Log simulated values
                self.logger.info(f"[SIM] RPM: {self.current_rpm}, Speed: {self.current_speed_kmh:.2f} km/h")
            else:
                # Real sensor logic - HIGH FREQUENCY polling for real-time response
                # Poll for pulses during the calculation interval with high frequency
                polling_frequency = int(1000 * self.calculation_interval)  # 1000Hz * interval
                for _ in range(polling_frequency):
                    if not self.running:
                        break
                    self.count_pulses_polling()
                    time.sleep(0.001)  # 1ms polling interval for maximum responsiveness
                
                with self.lock:
                    # Get current counter and reset
                    pulse_count = self.counter
                    self.counter = 0
                
                # Calculate RPM
                # RPM = (60 seconds * pulse_count) / pulses_per_turn
                rpm = (60 * pulse_count) / self.pulses_per_turn
                
                # Calculate speed in km/h
                # Wheel circumference in meters
                wheel_circumference_m = 3.14159 * (self.wheel_diameter_mm / 1000.0)
                
                # Speed = RPM * wheel_circumference * 60 (minutes/hour) / 1000 (m to km)
                speed_kmh = (rpm * wheel_circumference_m * 60) / 1000.0
                
                # Update current values
                with self.lock:
                    self.current_rpm = int(rpm)
                    self.current_speed_kmh = speed_kmh
                    self.last_update = time.time()
                
                # Log the values (changed to INFO level for debugging)
                if pulse_count > 0:
                    self.logger.info(f"[SPEED] Pulses: {pulse_count}, RPM: {self.current_rpm}, Speed: {self.current_speed_kmh:.2f} km/h")
                else:
                    # Log no pulse detection every 5 seconds for debugging
                    if int(time.time()) % 5 == 0:
                        self.logger.info(f"[SPEED] No pulses detected - GPIO{self.gpio_pin} state check")
    
    def get_speed_data(self):
        """Get current speed data as dictionary"""
        with self.lock:
            return {
                'rpm': self.current_rpm,
                'speed_kmh': round(self.current_speed_kmh, 2),
                'speed_ms': round(self.current_speed_kmh / 3.6, 2),  # Convert to m/s
                'last_update': self.last_update,
                'age_seconds': time.time() - self.last_update
            }
    
    def get_rpm(self):
        """Get current RPM"""
        with self.lock:
            return self.current_rpm
    
    def get_speed_kmh(self):
        """Get current speed in km/h"""
        with self.lock:
            return round(self.current_speed_kmh, 2)
    
    def get_speed_ms(self):
        """Get current speed in m/s"""
        with self.lock:
            return round(self.current_speed_kmh / 3.6, 2)
    
    def is_data_fresh(self, max_age_seconds: float = 2.0):
        """Check if speed data is fresh (recently updated)"""
        return (time.time() - self.last_update) <= max_age_seconds
    
    def start(self):
        """Start speed sensor monitoring"""
        if not self.simulation_mode and not GPIO_AVAILABLE:
            self.logger.error("❌ Cannot start speed sensor - GPIO not available")
            return False
        
        self.running = True
        
        # Start calculation thread
        self.calculation_thread = threading.Thread(target=self.calculate_speed, daemon=True)
        self.calculation_thread.start()
        
        mode_text = "simulation" if self.simulation_mode else "real sensor"
        self.logger.info(f"🚀 Speed sensor monitoring started ({mode_text})")
        return True
    
    def stop(self):
        """Stop speed sensor monitoring"""
        self.running = False
        
        if not self.simulation_mode and GPIO_AVAILABLE:
            try:
                GPIO.cleanup(self.gpio_pin)
            except Exception as e:
                self.logger.warning(f"⚠️ GPIO cleanup warning: {e}")
        
        self.logger.info("🛑 Speed sensor monitoring stopped (polling mode)")
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.stop()

def main():
    """Test the speed sensor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RC Car Speed Sensor Test')
    parser.add_argument('--gpio', type=int, default=16, help='GPIO pin number (default: 16)')
    parser.add_argument('--ppr', type=int, default=40, help='Pulses per revolution (default: 40)')
    parser.add_argument('--diameter', type=int, default=64, help='Wheel diameter in mm (default: 64)')
    
    args = parser.parse_args()
    
    print("🏎️ RC Car Speed Sensor Test")
    print("=" * 40)
    print(f"📍 GPIO Pin: {args.gpio}")
    print(f"🔄 Pulses per turn: {args.ppr}")
    print(f"⚙️ Wheel diameter: {args.diameter}mm")
    print("=" * 40)
    
    sensor = SpeedSensor(args.gpio, args.ppr, args.diameter)
    
    if not sensor.start():
        print("❌ Failed to start speed sensor")
        return
    
    try:
        print("📊 Monitoring speed (Ctrl+C to stop)...")
        while True:
            data = sensor.get_speed_data()
            
            # Display current values
            print(f"\r🏎️ RPM: {data['rpm']:4d} | "
                  f"Speed: {data['speed_kmh']:6.2f} km/h | "
                  f"{data['speed_ms']:5.2f} m/s | "
                  f"Age: {data['age_seconds']:.1f}s", end="", flush=True)
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping speed sensor...")
        sensor.stop()

if __name__ == "__main__":
    main()