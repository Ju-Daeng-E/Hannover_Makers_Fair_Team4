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
import asyncio
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Add current directory path for BMW modules
sys.path.append('/home/pi/controller_rpi')

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
    print("✅ BMW modules successfully imported")
except ImportError as e:
    print(f"⚠️ BMW modules not available: {e}")
    print("⚠️ Gear will be controlled by gamepad only")
    BMW_AVAILABLE = False
except Exception as e:
    print(f"❌ BMW modules import error: {e}")
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
    
    def __init__(self, vehicle_ip: str = "192.168.86.59", vehicle_port: int = 8888):
        self.vehicle_ip = vehicle_ip
        self.vehicle_port = vehicle_port
        self.socket = None
        self.running = False
        self.connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/home/pi/controller_rpi/controller.log'),
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
        
        # Control state (initialize before BMW system)
        self.control_data = ControlData()
        self.last_gear_change = 0
        self.gear_change_timeout = 0.3  # 300ms cooldown
        
        # Initialize BMW gear system
        self.bmw_state = None
        self.bmw_controller = None
        self.bmw_bus = None
        
        if BMW_AVAILABLE:
            self.setup_bmw_system()
        
    def setup_bmw_system(self):
        """Setup BMW gear lever system"""
        try:
            # Initialize CAN interface
            self.logger.info("🔧 Setting up CAN interface...")
            os.system("sudo ip link set can1 down 2>/dev/null")
            result = os.system("sudo ip link set can1 up type can bitrate 500000 2>/dev/null")
            
            if result != 0:
                raise Exception("Failed to setup CAN interface")
            
            # Initialize BMW components
            self.logger.info("🔧 Initializing BMW components...")
            bmw_logger = BMWLogger('controller', level='INFO')
            self.bmw_controller = BMWLeverController(bmw_logger)
            self.bmw_state = BMWState()
            
            # Setup CAN bus
            self.logger.info("🔧 Connecting to CAN bus...")
            self.bmw_bus = can.interface.Bus(channel='can1', interface='socketcan')
            
            # Test CAN bus
            self.logger.info("🧪 Testing CAN bus connection...")
            
            # Send initialization messages
            self.bmw_controller.send_initialization_messages(self.bmw_bus)
            time.sleep(0.5)  # Wait for initialization
            
            # 초기 기어 LED 즉시 설정 (기본값 N)
            initial_gear = self.control_data.gear  # 기본값은 'N'
            self.bmw_controller.send_gear_led(self.bmw_bus, initial_gear)
            self.bmw_controller.send_backlight_control(self.bmw_bus, 0xFF)
            self.logger.info(f"💡 Initial gear LED set to: {initial_gear}")
            
            self.logger.info("✅ BMW gear system initialized successfully")
            
        except Exception as e:
            self.logger.warning(f"⚠️ BMW system setup failed: {e}")
            self.logger.warning(f"   Error type: {type(e).__name__}")
            self.bmw_state = None
            self.bmw_controller = None
            self.bmw_bus = None
    
    def monitor_bmw_gear(self):
        """Monitor BMW gear lever in separate thread"""
        if not self.bmw_bus or not self.bmw_controller:
            self.logger.warning("🚫 BMW monitoring cancelled - missing bus or controller")
            return
            
        self.logger.info("🔧 BMW gear monitoring started")
        message_count = 0
        
        try:
            while True:  # Always run, but check self.running inside the loop
                try:
                    if not self.running:
                        break
                        
                    msg = self.bmw_bus.recv(timeout=1.0)  # 1초 타임아웃
                    if msg:
                        message_count += 1
                        
                        # 모든 메시지를 로그 (디버깅용)
                        if message_count % 100 == 0:  # 100개마다 로깅
                            self.logger.info(f"📊 CAN messages received: {message_count}")
                        
                        # BMW lever message 처리
                        if msg.arbitration_id == 0x197:  # BMW lever message
                            self.logger.debug(f"🎛️ BMW lever message: ID=0x{msg.arbitration_id:03X}, Data={msg.data.hex()}")
                            
                            if self.bmw_controller.decode_lever_message(msg, self.bmw_state):
                                # Update control data with BMW gear
                                self.control_data.gear = self.bmw_state.current_gear
                                if self.bmw_state.current_gear.startswith('M'):
                                    self.control_data.manual_gear = self.bmw_state.manual_gear
                                    
                                #self.logger.info(f"🎛️ Gear updated: {self.bmw_state.current_gear}")
                        else:
                            # 다른 메시지들도 로깅 (처음 몇 개만)
                            if message_count <= 10:
                                self.logger.debug(f"📨 CAN message: ID=0x{msg.arbitration_id:03X}, Data={msg.data.hex()}")
                            
                except can.CanError as e:
                    if "timeout" not in str(e).lower():
                        self.logger.warning(f"⚠️ CAN error: {e}")
                    continue
                except can.CanOperationError as e:
                    self.logger.error(f"❌ CAN operation error: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"❌ BMW monitoring error: {e}")
            self.logger.error(f"   Error type: {type(e).__name__}")
        
        self.logger.info(f"🔴 BMW monitoring stopped (processed {message_count} messages)")
    
    def update_gear_led(self):
        """Update gear LED periodically"""
        if not self.bmw_bus or not self.bmw_controller:
            self.logger.warning("🚫 LED update cancelled - missing bus or controller")
            return
            
        self.logger.info("🔧 Gear LED update started")
        last_gear = None
        update_counter = 0
        
        # 초기 LED 설정 - 시작할 때 바로 현재 기어 상태로 LED 켜기
        try:
            initial_gear = self.control_data.gear
            self.bmw_controller.send_gear_led(self.bmw_bus, initial_gear)
            self.bmw_controller.send_backlight_control(self.bmw_bus, 0xFF)
            self.logger.info(f"💡 Initial LED set to: {initial_gear}")
            last_gear = initial_gear
        except Exception as e:
            self.logger.error(f"❌ Initial LED setup error: {e}")
        
        try:
            while True:  # Always run, but check self.running inside the loop
                try:
                    if not self.running:
                        break
                        
                    current_gear = self.control_data.gear
                    update_counter += 1
                    
                    # LED 업데이트를 매초 실행하여 상시 유지
                    should_update = True  # 매초마다 LED 상태 유지
                    
                    if should_update:
                        # 기어 LED와 백라이트를 매초마다 지속적으로 전송하여 상시 유지
                        self.bmw_controller.send_gear_led(self.bmw_bus, current_gear)
                        self.bmw_controller.send_backlight_control(self.bmw_bus, 0xFF)
                        
                        if current_gear != last_gear:
                            self.logger.info(f"💡 LED updated to: {current_gear}")
                            last_gear = current_gear
                    
                    time.sleep(0.2)  # Update every 0.5 seconds for more stable LED
                    
                except Exception as e:
                    self.logger.error(f"❌ LED update error: {e}")
                    time.sleep(5)  # Wait before retry
                    
        except Exception as e:
            self.logger.error(f"❌ LED thread error: {e}")
        
        self.logger.info("🔴 LED update stopped")
    
    def connect_to_vehicle(self) -> bool:
        """Connect to vehicle Raspberry Pi with improved error handling"""
        try:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)  # 10초 연결 타임아웃
            self.socket.connect((self.vehicle_ip, self.vehicle_port))
            
            # TCP keepalive 설정
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            self.connected = True
            self.connection_attempts = 0
            self.logger.info(f"✅ Connected to vehicle at {self.vehicle_ip}:{self.vehicle_port}")
            return True
            
        except socket.timeout:
            self.logger.error(f"❌ Connection timeout to {self.vehicle_ip}:{self.vehicle_port}")
            self.connected = False
            return False
        except ConnectionRefusedError:
            self.logger.error(f"❌ Connection refused by {self.vehicle_ip}:{self.vehicle_port}")
            self.connected = False
            return False
        except Exception as e:
            self.logger.error(f"❌ Connection failed: {e}")
            self.connected = False
            return False
    
    async def async_connect_to_vehicle(self) -> bool:
        """Asynchronous version of connect_to_vehicle"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.connect_to_vehicle)
    
    async def read_gamepad_input(self):
        """Read and process gamepad input asynchronously"""
        try:
            # Run gamepad read in executor to avoid blocking
            loop = asyncio.get_event_loop()
            gamepad_input = await loop.run_in_executor(None, self.gamepad.read_data)
            
            # Read analog sticks - Using right joystick Y-axis for throttle control
            self.control_data.throttle = gamepad_input.analog_stick_right.y
            
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
    
    async def send_control_data(self) -> bool:
        """Send control data to vehicle with improved error handling"""
        if not self.socket or not self.connected:
            return False
            
        try:
            data_json = self.control_data.to_json()
            message = data_json.encode('utf-8') + b'\n'
            
            # 비동기 소켓 전송 (논블로킹)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_data_sync, message)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Send error: {e}")
            self.connected = False
            return False
    
    def _send_data_sync(self, message: bytes):
        """Synchronous send helper for executor"""
        try:
            self.socket.settimeout(1.0)  # 1초 전송 타임아웃
            bytes_sent = self.socket.send(message)
            
            if bytes_sent == 0:
                raise ConnectionError("Socket connection broken (0 bytes sent)")
                
        except socket.timeout:
            raise TimeoutError("Send timeout - connection may be slow")
        except ConnectionResetError:
            raise ConnectionError("Connection reset by vehicle")
        except BrokenPipeError:
            raise ConnectionError("Broken pipe - vehicle disconnected")
        except socket.error as e:
            raise ConnectionError(f"Socket error: {e}")
    
    async def gamepad_loop(self):
        """독립적인 게임패드 입력 처리 루프"""
        self.logger.info("🎮 Gamepad loop started")
        
        try:
            while self.running:
                try:
                    await self.read_gamepad_input()
                except Exception as e:
                    self.logger.warning(f"⚠️ Gamepad read error: {e}")
                await asyncio.sleep(0.02)  # 50Hz 게임패드 입력
                
        except Exception as e:
            self.logger.error(f"❌ Gamepad loop error: {e}")
    
    async def socket_loop(self):
        """독립적인 소켓 통신 루프"""
        self.logger.info("🔌 Socket loop started")
        
        # Connect to vehicle with exponential backoff
        retry_delay = 1
        while not await self.async_connect_to_vehicle():
            self.connection_attempts += 1
            if self.connection_attempts >= self.max_connection_attempts:
                retry_delay = min(retry_delay * 1.5, 30)  # 최대 30초
                self.connection_attempts = 0
            
            self.logger.info(f"🔄 Retrying connection in {retry_delay:.1f} seconds... (attempt {self.connection_attempts})")
            await asyncio.sleep(retry_delay)
        
        try:
            last_status_log = 0
            while self.running:
                # Send to vehicle
                if not await self.send_control_data():
                    self.logger.warning("⚠️ Failed to send data, attempting reconnection...")
                    
                    # 재연결 시도
                    retry_count = 0
                    while not await self.async_connect_to_vehicle() and retry_count < 3:
                        retry_count += 1
                        self.logger.info(f"🔄 Reconnection attempt {retry_count}/3")
                        await asyncio.sleep(min(retry_count * 2, 10))  # 2, 4, 6초 대기
                    
                    if not self.connected:
                        self.logger.error("❌ Failed to reconnect after 3 attempts, continuing...")
                        await asyncio.sleep(5)
                        continue
                
                # Status logging (every 2 seconds)
                current_time = int(time.time())
                if current_time != last_status_log:
                    if current_time % 2 == 0:
                        connection_status = "✅" if self.connected else "❌"
                        self.logger.info(f"📊 {connection_status} T:{self.control_data.throttle:.2f} S:{self.control_data.steering:.2f} G:{self.control_data.gear}")
                    last_status_log = current_time
                
                await asyncio.sleep(0.05)  # 20Hz 소켓 전송
                
        except Exception as e:
            self.logger.error(f"❌ Socket loop error: {e}")
    
    async def run_async(self):
        """비동기 메인 실행 함수"""
        self.logger.info("🚀 Controller system starting...")
        
        # Start BMW threads first (independent of vehicle connection)
        self.running = True
        if BMW_AVAILABLE and self.bmw_bus and self.bmw_controller:
            # Start BMW monitoring thread
            self.bmw_thread = threading.Thread(target=self.monitor_bmw_gear, daemon=True)
            self.bmw_thread.start()
            
            # Start LED update thread (independent of vehicle connection)
            self.led_thread = threading.Thread(target=self.update_gear_led, daemon=True)
            self.led_thread.start()
            
            self.logger.info("🔧 BMW threads started (LED will stay on)")
        
        try:
            # 게임패드와 소켓을 독립적으로 실행
            await asyncio.gather(
                self.gamepad_loop(),
                self.socket_loop()
            )
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Stopping controller...")
        except Exception as e:
            self.logger.error(f"❌ Runtime error: {e}")
        finally:
            self.cleanup()
    
    def run(self):
        """메인 실행 함수 (asyncio 진입점)"""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            self.logger.info("🛑 Controller interrupted")
        except Exception as e:
            self.logger.error(f"❌ Async runtime error: {e}")
    
    def is_connected(self) -> bool:
        """Check if socket is still connected"""
        if not self.socket or not self.connected:
            return False
        
        try:
            # 빠른 연결 상태 확인 (non-blocking)
            self.socket.settimeout(0.1)
            ready = self.socket.recv(1, socket.MSG_PEEK)
            return True
        except socket.timeout:
            return True  # 타임아웃은 연결되어 있음을 의미
        except:
            self.connected = False
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        if self.bmw_bus:
            self.bmw_bus.shutdown()
        self.logger.info("🧹 Controller cleanup completed")

def main():
    """Main entry point"""
    print("🎮 RC Car Controller System")
    print("=" * 40)
    
    # Configuration (you can modify these)
    VEHICLE_IP = "192.168.86.59"  # Change to your vehicle Pi's IP
    VEHICLE_PORT = 8888
    
    controller = ControllerSystem(VEHICLE_IP, VEHICLE_PORT)
    controller.run()

if __name__ == "__main__":
    main()