#!/usr/bin/env python3
"""
RC Car Controller - Raspberry Pi Controller System
컨트롤러용 라즈베리파이: 게임패드 + BMW 기어봉 입력을 소켓으로 전송
"""

import os
import sys
import time
import json
import socket
import threading
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Add BMW modular path for gear control
sys.path.append('/home/pi/SEA-ME-RCcarCluster/BMW_GWS/modular_version')

try:
    from piracer.gamepads import ShanWanGamepad
    GAMEPAD_AVAILABLE = True
except ImportError:
    print("⚠️ PiRacer gamepad not available - using mock gamepad")
    GAMEPAD_AVAILABLE = False

try:
    import can
    from bmw_lever_controller import BMWLeverController
    from data_models import BMWState
    from logger import Logger as BMWLogger
    BMW_AVAILABLE = True
except ImportError:
    print("⚠️ BMW modules not available - gear will be controlled by gamepad only")
    BMW_AVAILABLE = False

@dataclass
class ControlData:
    """Control data structure for transmission"""
    throttle: float = 0.0
    steering: float = 0.0
    gear: str = 'N'
    manual_gear: int = 1
    timestamp: float = 0.0
    
    def to_json(self) -> str:
        return json.dumps({
            'throttle': self.throttle,
            'steering': self.steering,
            'gear': self.gear,
            'manual_gear': self.manual_gear,
            'timestamp': self.timestamp
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ControlData':
        data = json.loads(json_str)
        return cls(**data)

class MockGamepad:
    """Mock gamepad for testing without hardware"""
    def __init__(self):
        self.analog_stick_left = type('stick', (), {'x': 0.0, 'y': 0.0})()
        self.analog_stick_right = type('stick', (), {'x': 0.0, 'y': 0.0})()
        self.button_a = False
        self.button_b = False
        self.button_x = False
        self.button_y = False
        self.button_l2 = False
        self.button_r2 = False
    
    def read_data(self):
        return self

class ControllerSystem:
    """Main controller system"""
    
    def __init__(self, vehicle_ip: str = "192.168.1.100", vehicle_port: int = 8888):
        self.vehicle_ip = vehicle_ip
        self.vehicle_port = vehicle_port
        self.socket = None
        self.running = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/home/pi/Hannover_Makers_Fair_Team4/controller_rpi/controller.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize gamepad
        if GAMEPAD_AVAILABLE:
            try:
                self.gamepad = ShanWanGamepad()
                self.logger.info("✅ ShanWan Gamepad initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Gamepad error, using mock: {e}")
                self.gamepad = MockGamepad()
        else:
            self.gamepad = MockGamepad()
        
        # Initialize BMW gear system
        self.bmw_state = None
        self.bmw_controller = None
        self.bmw_bus = None
        
        if BMW_AVAILABLE:
            self.setup_bmw_system()
        
        # Control state
        self.control_data = ControlData()
        self.last_gear_change = 0
        self.gear_change_timeout = 0.3  # 300ms cooldown
        
    def setup_bmw_system(self):
        """Setup BMW gear lever system"""
        try:
            # Initialize CAN interface
            os.system("sudo ip link set can0 up type can bitrate 500000")
            
            # Initialize BMW components
            bmw_logger = BMWLogger('controller', level='INFO')
            self.bmw_controller = BMWLeverController(bmw_logger)
            self.bmw_state = BMWState()
            
            # Setup CAN bus
            self.bmw_bus = can.interface.Bus(channel='can0', bustype='socketcan')
            
            # Start BMW monitoring thread
            self.bmw_thread = threading.Thread(target=self.monitor_bmw_gear, daemon=True)
            self.bmw_thread.start()
            
            self.logger.info("✅ BMW gear system initialized")
            
        except Exception as e:
            self.logger.warning(f"⚠️ BMW system setup failed: {e}")
            self.bmw_state = None
            self.bmw_controller = None
    
    def monitor_bmw_gear(self):
        """Monitor BMW gear lever in separate thread"""
        if not self.bmw_bus or not self.bmw_controller:
            return
            
        self.logger.info("🔧 BMW gear monitoring started")
        
        try:
            while self.running:
                try:
                    msg = self.bmw_bus.recv(timeout=0.1)
                    if msg and msg.arbitration_id == 0x197:  # BMW lever message
                        self.bmw_controller.decode_lever_message(msg, self.bmw_state)
                        # Update control data with BMW gear
                        self.control_data.gear = self.bmw_state.current_gear
                        if self.bmw_state.current_gear.startswith('M'):
                            self.control_data.manual_gear = self.bmw_state.manual_gear
                            
                except can.CanError:
                    continue  # Timeout or error, continue monitoring
                    
        except Exception as e:
            self.logger.error(f"❌ BMW monitoring error: {e}")
    
    def connect_to_vehicle(self) -> bool:
        """Connect to vehicle Raspberry Pi"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.vehicle_ip, self.vehicle_port))
            self.logger.info(f"✅ Connected to vehicle at {self.vehicle_ip}:{self.vehicle_port}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Connection failed: {e}")
            return False
    
    def read_gamepad_input(self):
        """Read and process gamepad input"""
        try:
            gamepad_input = self.gamepad.read_data()
            
            # Read analog sticks
            self.control_data.throttle = -gamepad_input.analog_stick_right.y  # Invert Y axis
            self.control_data.steering = -gamepad_input.analog_stick_left.x   # Invert X axis
            
            # If BMW system not available, use gamepad for gear control
            if not BMW_AVAILABLE:
                current_time = time.time()
                if current_time - self.last_gear_change > self.gear_change_timeout:
                    if gamepad_input.button_b:
                        self.control_data.gear = 'D'
                        self.last_gear_change = current_time
                        self.logger.info("🎮 Gamepad: Gear → D")
                    elif gamepad_input.button_a:
                        self.control_data.gear = 'N'
                        self.last_gear_change = current_time
                        self.logger.info("🎮 Gamepad: Gear → N")
                    elif gamepad_input.button_x:
                        self.control_data.gear = 'R'
                        self.last_gear_change = current_time
                        self.logger.info("🎮 Gamepad: Gear → R")
                    elif gamepad_input.button_y:
                        self.control_data.gear = 'P'
                        self.last_gear_change = current_time
                        self.logger.info("🎮 Gamepad: Gear → P")
            
            self.control_data.timestamp = time.time()
            
        except Exception as e:
            self.logger.error(f"❌ Gamepad input error: {e}")
    
    def send_control_data(self) -> bool:
        """Send control data to vehicle"""
        try:
            if not self.socket:
                return False
                
            data_json = self.control_data.to_json()
            # Ensure clean JSON with newline terminator
            message = data_json.encode('utf-8') + b'\n'
            
            # Send with proper error handling
            self.socket.sendall(message)
            return True
            
        except (BrokenPipeError, ConnectionResetError) as e:
            self.logger.warning(f"⚠️ Connection lost: {e}")
            self.socket = None
            return False
        except Exception as e:
            self.logger.error(f"❌ Send error: {e}")
            return False
    
    def run(self):
        """Main control loop"""
        self.logger.info("🚀 Controller system starting...")
        
        # Connect to vehicle
        while not self.connect_to_vehicle():
            self.logger.info("🔄 Retrying connection in 2 seconds...")
            time.sleep(2)
        
        self.running = True
        
        try:
            while self.running:
                # Read inputs
                self.read_gamepad_input()
                
                # Send to vehicle
                if not self.send_control_data():
                    self.logger.warning("⚠️ Failed to send data, attempting reconnection...")
                    if not self.connect_to_vehicle():
                        time.sleep(1)
                        continue
                
                # Status logging (every 2 seconds)
                if int(time.time()) % 2 == 0:
                    self.logger.info(f"📊 T:{self.control_data.throttle:.2f} S:{self.control_data.steering:.2f} G:{self.control_data.gear}")
                
                time.sleep(0.05)  # 20Hz update rate
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Stopping controller...")
        except Exception as e:
            self.logger.error(f"❌ Runtime error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.bmw_bus:
            self.bmw_bus.shutdown()
        self.logger.info("🧹 Controller cleanup completed")

def main():
    """Main entry point"""
    print("🎮 RC Car Controller System")
    print("=" * 40)
    
    # Configuration (you can modify these)
    VEHICLE_IP = "192.168.1.100"  # Change to your vehicle Pi's IP
    VEHICLE_PORT = 8888
    
    controller = ControllerSystem(VEHICLE_IP, VEHICLE_PORT)
    controller.run()

if __name__ == "__main__":
    main()