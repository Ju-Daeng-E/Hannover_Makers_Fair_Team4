#!/usr/bin/env python3
"""
RC Car Vehicle - Raspberry Pi Vehicle System
차량용 라즈베리파이: 소켓으로 제어 데이터를 받아 차량을 제어하고 카메라 스트리밍
"""

import os
import sys
import time
import json
import socket
import threading
import logging
import subprocess
import random
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any
from multiprocessing import Process, Value, Array

# Flask for web server
try:
    from flask import Flask, send_from_directory, jsonify, Response
    FLASK_AVAILABLE = True
except ImportError:
    print("⚠️ Flask not available - web dashboard disabled")
    FLASK_AVAILABLE = False

# Add piracer library path to sys.path
PIRACER_PATHS = [
    "/home/pi/piracer_test/venv/lib/python3.11/site-packages",
    "/home/pi/SEA-ME-RCcarCluster/piracer_team4/venv/lib/python3.11/site-packages"
]

for path in PIRACER_PATHS:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

try:
    from piracer.vehicles import PiRacerStandard
    PIRACER_AVAILABLE = True
    print("✅ PiRacer library loaded from venv path")
except ImportError:
    print("⚠️ PiRacer library not available - using mock vehicle")
    PIRACER_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    print("⚠️ Pygame not available - dashboard disabled")
    PYGAME_AVAILABLE = False

# Import speed sensor
from speed_sensor import SpeedSensor

# Battery monitoring using INA219
try:
    import smbus
    INA219_AVAILABLE = True
except ImportError:
    print("⚠️ smbus not available - battery monitoring disabled")
    INA219_AVAILABLE = False

class BatteryMonitor:
    """INA219 기반 배터리 모니터링"""
    
    def __init__(self, address=0x41, shunt_ohms=0.1):
        self.bus = None
        self.address = address
        self.shunt_ohms = shunt_ohms
        self.connected = False
        self.last_measurement = None
        self.last_update = 0
        
        if INA219_AVAILABLE:
            self.setup()
    
    def setup(self):
        """INA219 초기화"""
        try:
            self.bus = smbus.SMBus(1)
            
            # Reset
            self.bus.write_word_data(self.address, 0x00, 0x8000)
            time.sleep(0.1)
            
            # Configuration
            config = 0x1F9F  # 16V bus, 320mV shunt, 12-bit ADC
            self.bus.write_word_data(self.address, 0x00, config)
            time.sleep(0.1)
            
            # Test read
            test_data = self.get_measurements()
            print(f"🔍 INA219 테스트 데이터 (0x{self.address:02X}): {test_data}")
            
            if test_data and test_data['bus_voltage'] > 0.1:  # 매우 관대한 범위 (0.1V 이상이면 작동)
                self.connected = True
                print(f"✅ INA219 배터리 모니터 초기화 완료 (주소: 0x{self.address:02X}, 전압: {test_data['bus_voltage']:.3f}V)")
                return True
            else:
                print(f"⚠️ INA219 데이터 범위 이상 또는 측정 실패: {test_data}")
                return False
                
        except Exception as e:
            print(f"⚠️ INA219 초기화 실패: {e}")
            self.connected = False
            return False
    
    def read_raw(self, register):
        """레지스터에서 원시 데이터 읽기"""
        try:
            if not self.bus:
                return None
            data = self.bus.read_word_data(self.address, register)
            # Swap bytes (I2C MSB first)
            return ((data & 0xFF) << 8) | ((data & 0xFF00) >> 8)
        except Exception as e:
            print(f"❌ Read error on register 0x{register:02X}: {e}")
            return None
    
    def get_measurements(self):
        """전압, 전류, 전력 측정"""
        bus_raw = self.read_raw(0x02)  # Bus voltage register
        shunt_raw = self.read_raw(0x01)  # Shunt voltage register
        
        if bus_raw is None or shunt_raw is None:
            return None
            
        # Convert shunt to signed
        if shunt_raw > 32767:
            shunt_raw -= 65536
        
        # Calculate actual values
        bus_voltage = (bus_raw >> 3) * 0.004  # 4mV per LSB
        shunt_voltage_uv = shunt_raw * 10  # 10µV per LSB
        current_ma = shunt_voltage_uv / (self.shunt_ohms * 1000)
        power_w = bus_voltage * current_ma / 1000
        
        return {
            'bus_voltage': bus_voltage,
            'current_ma': current_ma,
            'power_w': power_w
        }
    
    def get_battery_percentage(self):
        """배터리 잔량을 0-100% 범위로 반환"""
        measurements = self.get_measurements()
        if not measurements:
            return None
        
        voltage = measurements['bus_voltage']
        
        # 다양한 전압 범위 지원
        if voltage > 20:  # 고전압 (24V 시스템 등)
            # 24V 시스템 기준 (20V ~ 28V)
            min_voltage = 20.0
            max_voltage = 28.0
            percentage = ((voltage - min_voltage) / (max_voltage - min_voltage)) * 100
        elif voltage > 8:  # 12V 시스템
            # 12V 배터리 기준 (10V ~ 14V)
            min_voltage = 10.0
            max_voltage = 14.0
            percentage = ((voltage - min_voltage) / (max_voltage - min_voltage)) * 100
        elif voltage > 4.5:  # 5V USB 전원
            # USB 전원 - 항상 100%
            percentage = 100
        else:  # 3.3V ~ 4.2V 리튬 배터리
            # 리튬 배터리 기준
            min_voltage = 3.2
            max_voltage = 4.1
            percentage = ((voltage - min_voltage) / (max_voltage - min_voltage)) * 100
        
        # 0-100% 범위로 제한
        final_percentage = max(0, min(100, int(percentage)))
        return final_percentage
    
    def update_battery_data(self):
        """배터리 데이터 업데이트 (3초마다)"""
        current_time = time.time()
        
        # 3초마다 업데이트
        if current_time - self.last_update < 3.0:
            return self.last_measurement
        
        try:
            percentage = self.get_battery_percentage()
            measurements = self.get_measurements()
            
            if percentage is not None and measurements:
                self.last_measurement = {
                    'battery_percentage': percentage,
                    'battery_voltage': measurements['bus_voltage'],
                    'battery_current': measurements['current_ma'],
                    'battery_power': measurements['power_w'],
                    'battery_status': 'ok',
                    'timestamp': current_time
                }
            else:
                self.last_measurement = {
                    'battery_percentage': 0,
                    'battery_voltage': 0,
                    'battery_current': 0,
                    'battery_power': 0,
                    'battery_status': 'error',
                    'timestamp': current_time
                }
            
            self.last_update = current_time
            return self.last_measurement
            
        except Exception as e:
            print(f"❌ 배터리 데이터 업데이트 오류: {e}")
            self.last_measurement = {
                'battery_percentage': 0,
                'battery_voltage': 0,
                'battery_current': 0,
                'battery_power': 0,
                'battery_status': 'error',
                'timestamp': current_time
            }
            self.last_update = current_time
            return self.last_measurement

@dataclass
class ControlData:
    """Control data structure for receiving"""
    throttle: float = 0.0
    steering: float = 0.0
    gear: str = 'N'
    manual_gear: int = 1
    timestamp: float = 0.0
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ControlData':
        try:
            data = json.loads(json_str)
            return cls(**data)
        except Exception:
            return cls()  # Return default values on error

class MockVehicle:
    """Mock vehicle for testing without hardware"""
    def __init__(self):
        self.throttle = 0.0
        self.steering = 0.0
        
    def set_throttle_percent(self, throttle: float):
        self.throttle = throttle
        
    def set_steering_percent(self, steering: float):
        self.steering = steering

class CameraStreamer:
    """Camera streaming handler with proper integration"""
    
    def __init__(self, port: int = 8080, udp_mode: bool = False, udp_port: int = 9999):
        self.port = port
        self.udp_mode = udp_mode
        self.udp_port = udp_port
        self.streaming = False
        self.process = None
        
    def start_streaming(self):
        """Start camera streaming using the corrected camera_stream.py"""
        try:
            # Get current script directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Set environment for camera streaming
            env = os.environ.copy()
            
            # Force system packages to avoid numpy conflicts
            env['PYTHONPATH'] = '/usr/lib/python3/dist-packages:' + env.get('PYTHONPATH', '')
            env['PYTHONNOUSERSITE'] = '1'
            
            # If running as root, we need to handle permissions properly
            if os.geteuid() == 0:
                # Try to get pi user info for environment
                try:
                    import pwd
                    pi_user = pwd.getpwnam('pi')
                    env['HOME'] = pi_user.pw_dir
                    env['USER'] = 'pi'
                    print("🔧 Running camera stream as root with pi user environment")
                except:
                    print("⚠️ Running camera stream as root")
            
            # Use the camera stream script with shell wrapper
            camera_script = os.path.join(script_dir, "run_camera_stream.sh")
            
            if os.path.exists(camera_script):
                # Make script executable
                os.chmod(camera_script, 0o755)
                
                # Build command arguments
                args = ['bash', camera_script]
                if self.udp_mode:
                    args.extend(['--udp', '--udp-port', str(self.udp_port)])
                else:
                    args.extend(['--port', str(self.port)])
                
                # Use the shell script wrapper
                self.process = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Give it time to start and check if it's running
                time.sleep(1)  # Reduced startup delay
                if self.process.poll() is None:  # Process is still running
                    self.streaming = True
                    print(f"✅ Camera streaming started on port {self.port}")
                else:
                    # Get error output
                    stdout, stderr = self.process.communicate()
                    print(f"❌ Camera streaming failed (exit: {self.process.returncode})")
                    if stderr:
                        print(f"Error: {stderr.decode()}")
                    self.streaming = False
            else:
                # Try direct system python call with LOW PRIORITY
                camera_py = os.path.join(script_dir, "camera_stream.py")
                if os.path.exists(camera_py):
                    # Build command arguments
                    args = ['/usr/bin/python3', camera_py]
                    if self.udp_mode:
                        args.extend(['--udp', '--udp-port', str(self.udp_port)])
                    else:
                        args.extend(['--port', str(self.port)])
                    
                    self.process = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    # Give it time to start and check if it's running
                    time.sleep(1)  # Reduced startup delay
                    if self.process.poll() is None:  # Process is still running
                        self.streaming = True
                        print(f"✅ Camera streaming started with system Python on port {self.port}")
                    else:
                        # Get error output
                        stdout, stderr = self.process.communicate()
                        print(f"❌ Camera streaming failed (exit: {self.process.returncode})")
                        if stderr:
                            print(f"Error: {stderr.decode()}")
                        self.streaming = False
                else:
                    print("❌ Camera stream script not found")
                    self.streaming = False
                
        except Exception as e:
            print(f"⚠️ Camera streaming failed: {e}")
            self.streaming = False
    
    def stop_streaming(self):
        """Stop camera streaming"""
        if self.process:
            self.process.terminate()
            self.streaming = False
            print("🛑 Camera streaming stopped")

class Dashboard:
    """Simple pygame dashboard"""
    
    def __init__(self):
        if not PYGAME_AVAILABLE:
            return
            
        pygame.init()
        self.screen = pygame.display.set_mode((400, 300))
        pygame.display.set_caption("RC Car Vehicle Dashboard")
        self.font = pygame.font.Font(None, 36)
        self.clock = pygame.time.Clock()
        
    def update(self, control_data: ControlData, connection_status: str, speed_data: Dict = None):
        """Update dashboard display"""
        if not PYGAME_AVAILABLE:
            return
            
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
            
            # Clear screen
            self.screen.fill((0, 0, 0))
            
            # Status display
            status_color = (0,255, 0) if connection_status == "Connected" else (255, 0, 0)
            status_text = self.font.render(f"Status: {connection_status}", True, status_color)
            self.screen.blit(status_text, (10, 10))
            
            # Control data display
            throttle_text = self.font.render(f"Throttle: {control_data.throttle:.2f}", True, (255, 255, 255))
            steering_text = self.font.render(f"Steering: {control_data.steering:.2f}", True, (255, 255, 255))
            gear_text = self.font.render(f"Gear: {control_data.gear}", True, (255, 255, 0))
            
            self.screen.blit(throttle_text, (10, 50))
            self.screen.blit(steering_text, (10, 90))
            self.screen.blit(gear_text, (10, 130))
            
            # Speed sensor data display
            if speed_data:
                speed_text = self.font.render(f"Speed: {speed_data['speed_kmh']:.1f} km/h", True, (0, 255, 255))
                rpm_text = self.font.render(f"RPM: {speed_data['rpm']}", True, (0, 255, 255))
                self.screen.blit(speed_text, (10, 170))
                self.screen.blit(rpm_text, (10, 210))
            
            # Timestamp
            time_text = self.font.render(f"Last Update: {datetime.now().strftime('%H:%M:%S')}", True, (128, 128, 128))
            self.screen.blit(time_text, (10, 250))
            
            pygame.display.flip()
            self.clock.tick(30)  # 30 FPS
            return True
            
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
            return False
    
    def cleanup(self):
        """Cleanup pygame"""
        if PYGAME_AVAILABLE:
            pygame.quit()

class WebServer:
    """Flask web server for React dashboard"""
    
    def __init__(self, port: int = 8080, vehicle_system=None):
        self.port = port
        self.vehicle_system = vehicle_system
        self.app = None
        self.server_thread = None
        
        if FLASK_AVAILABLE:
            self.setup_flask()
    
    def setup_flask(self):
        """Setup Flask application"""
        self.app = Flask(__name__)
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development
        
        # React Dashboard 경로
        dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard', 'dist')
        
        @self.app.route('/')
        def index():
            """React 대시보드 메인 페이지"""
            return send_from_directory(dashboard_path, 'index.html')
        
        @self.app.route('/assets/<path:filename>')
        def assets(filename):
            """React 빌드 자산 파일들"""
            return send_from_directory(os.path.join(dashboard_path, 'assets'), filename)
        
        @self.app.route('/api/vehicle-data')
        def vehicle_data():
            """차량 데이터 API - 실제 GPIO 센서 데이터 사용"""
            print(f"🔍 API Debug - vehicle_system exists: {self.vehicle_system is not None}")
            print(f"🔍 API Debug - speed_sensor exists: {self.vehicle_system.speed_sensor is not None if self.vehicle_system else False}")
            
            if self.vehicle_system and self.vehicle_system.speed_sensor:
                # 실제 센서 데이터 가져오기
                speed_data = self.vehicle_system.current_speed_data
                print(f"🔍 API Debug - Raw speed_data: {speed_data}")
                
                # 데이터 유효성 확인 (더 빠른 응답을 위해 기준 완화)
                data_age = speed_data.get('age_seconds', 999)
                is_fresh = data_age < 0.5  # 0.5초 이내 데이터만 신뢰 (더 빠른 실시간성)
                print(f"🔍 API Debug - data_age: {data_age}, is_fresh: {is_fresh}")
                
                # 배터리 데이터 가져오기
                battery_data = {'battery_percentage': 0, 'battery_status': 'unavailable'}
                if self.vehicle_system.battery_monitor:
                    battery_info = self.vehicle_system.battery_monitor.update_battery_data()
                    print(f"🔍 Battery Debug - battery_info: {battery_info}")
                    if battery_info:
                        battery_data = {
                            'battery_percentage': battery_info.get('battery_percentage', 0),
                            'battery_status': battery_info.get('battery_status', 'error'),
                            'battery_voltage': battery_info.get('battery_voltage', 0),
                            'battery_current': battery_info.get('battery_current', 0)
                        }
                        print(f"🔍 Battery Debug - processed battery_data: {battery_data}")
                else:
                    print("🔍 Battery Debug - no battery monitor available")
                
                if is_fresh:
                    # 신선한 실제 센서 데이터
                    data = {
                        'rpmValue': int(speed_data.get('rpm', 0)),
                        'speedValue': float(speed_data.get('speed_kmh', 0.0)),
                        'gear': self.vehicle_system.current_control.gear,
                        'batteryLevel': battery_data['battery_percentage'],
                        'batteryStatus': battery_data['battery_status'],
                        'batteryVoltage': battery_data.get('battery_voltage', 0),
                        'batteryCurrent': battery_data.get('battery_current', 0),
                        'connectionStatus': self.vehicle_system.connection_status,
                        'sensorStatus': 'active',
                        'dataAge': round(data_age, 1)
                    }
                else:
                    # 오래된 센서 데이터 - 0으로 표시
                    data = {
                        'rpmValue': 0,
                        'speedValue': 0.0,
                        'gear': self.vehicle_system.current_control.gear,
                        'batteryLevel': battery_data['battery_percentage'],
                        'batteryStatus': battery_data['battery_status'],
                        'batteryVoltage': battery_data.get('battery_voltage', 0),
                        'batteryCurrent': battery_data.get('battery_current', 0),
                        'connectionStatus': self.vehicle_system.connection_status,
                        'sensorStatus': 'stale',
                        'dataAge': round(data_age, 1)
                    }
            else:
                # 센서 없거나 시스템 없음 - 배터리만 독립적으로 확인
                battery_data = {'battery_percentage': 0, 'battery_status': 'unavailable'}
                if self.vehicle_system and self.vehicle_system.battery_monitor:
                    battery_info = self.vehicle_system.battery_monitor.update_battery_data()
                    if battery_info:
                        battery_data = {
                            'battery_percentage': battery_info.get('battery_percentage', 0),
                            'battery_status': battery_info.get('battery_status', 'error')
                        }
                
                data = {
                    'rpmValue': 0,
                    'speedValue': 0.0,
                    'gear': 'N',
                    'batteryLevel': battery_data['battery_percentage'],
                    'batteryStatus': battery_data['battery_status'],
                    'connectionStatus': 'Disconnected',
                    'sensorStatus': 'unavailable',
                    'dataAge': 999
                }
            return jsonify(data)
        
        # Video feed now handled directly via SSE on port 8080
        # Proxy removed to eliminate latency
        
        @self.app.route('/status')
        def status():
            """상태 확인 API"""
            return jsonify({
                'status': 'ready',
                'camera': 'enabled' if self.vehicle_system and self.vehicle_system.camera_streamer.streaming else 'disabled',
                'controller': self.vehicle_system.connection_status if self.vehicle_system else 'disconnected',
                'port': self.port,
                'dashboard': 'react'
            })
    
    # get_error_frame method removed - no longer needed with direct SSE connection
    
    def start(self):
        """Start web server in separate thread"""
        if not FLASK_AVAILABLE:
            print("⚠️ Web server unavailable - Flask not installed")
            return False
        
        if not self.app:
            print("⚠️ Web server unavailable - Flask app not initialized")
            return False
        
        try:
            self.server_thread = threading.Thread(
                target=lambda: self.app.run(
                    host='0.0.0.0', 
                    port=self.port, 
                    debug=False, 
                    threaded=True,
                    use_reloader=False
                ),
                daemon=True
            )
            self.server_thread.start()
            print(f"✅ Web server started on port {self.port}")
            print(f"🌐 Access React dashboard at: http://localhost:{self.port}")
            return True
        except Exception as e:
            print(f"❌ Web server failed to start: {e}")
            return False
    
    def stop(self):
        """Stop web server"""
        # Flask development server doesn't have a clean shutdown method
        # In production, you'd use a proper WSGI server like Gunicorn
        pass

class VehicleSystem:
    """Main vehicle system"""
    
    def __init__(self, listen_port: int = 8888, camera_port: int = 8080, web_port: int = 8082, 
                 udp_streaming: bool = False, udp_port: int = 9999, websocket_port: int = 8765):
        self.listen_port = listen_port
        self.camera_port = camera_port
        self.web_port = web_port
        self.udp_streaming = udp_streaming
        self.udp_port = udp_port
        self.websocket_port = websocket_port
        self.server_socket = None
        self.client_socket = None
        self.running = False
        
        # Setup logging with proper permissions
        log_file = os.path.join(os.path.dirname(__file__), 'logs', 'vehicle.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Ensure log file has proper permissions
        if os.geteuid() == 0:  # Running as root
            # Create log file with pi user ownership
            try:
                import pwd
                pi_uid = pwd.getpwnam('pi').pw_uid
                pi_gid = pwd.getpwnam('pi').pw_gid
                
                # Create log file if it doesn't exist
                if not os.path.exists(log_file):
                    with open(log_file, 'a'):
                        pass
                
                # Change ownership to pi user
                os.chown(log_file, pi_uid, pi_gid)
                os.chown(os.path.dirname(log_file), pi_uid, pi_gid)
                
            except Exception as e:
                print(f"Warning: Could not set log file ownership: {e}")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize vehicle
        if PIRACER_AVAILABLE:
            try:
                self.vehicle = PiRacerStandard()
                self.logger.info("✅ PiRacer vehicle initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ PiRacer error, using mock: {e}")
                self.vehicle = MockVehicle()
        else:
            self.vehicle = MockVehicle()
        
        # Initialize camera streaming 
        self.camera_streamer = CameraStreamer(
            port=camera_port, 
            udp_mode=udp_streaming, 
            udp_port=udp_port
        )
        
        # Initialize WebSocket bridge for UDP streaming
        self.websocket_bridge = None
        if udp_streaming:
            self.setup_websocket_bridge()
        
        # Initialize dashboard
        self.dashboard = Dashboard()
        
        # Initialize web server for React dashboard
        if FLASK_AVAILABLE:
            self.web_server = WebServer(self.web_port, self)
            self.logger.info(f"🌐 Web server initialized for port {self.web_port}")
        else:
            self.web_server = None
            self.logger.warning("⚠️ Flask not available - web server disabled")
        
        # Initialize speed sensor
        try:
            self.speed_sensor = SpeedSensor(
                gpio_pin=16,          # GPIO pin for speed sensor
                pulses_per_turn=40,   # Encoder pulses per revolution
                wheel_diameter_mm=64, # Wheel diameter in mm
                simulation_mode=False  # Always use real GPIO sensor
            )
            self.current_speed_data = {'rpm': 0, 'speed_kmh': 0.0, 'speed_ms': 0.0}
            self.logger.info("✅ Speed sensor initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Speed sensor initialization failed: {e}")
            self.speed_sensor = None
            self.current_speed_data = {'rpm': 0, 'speed_kmh': 0.0, 'speed_ms': 0.0}
        
        # Initialize battery monitor - PiRacer 내장 INA219 사용 (0x41)
        self.battery_monitor = None
        try:
            self.battery_monitor = BatteryMonitor(address=0x41)
            if self.battery_monitor.connected:
                self.logger.info(f"✅ Battery monitor initialized at 0x41 (PiRacer built-in)")
            else:
                self.logger.warning(f"⚠️ Battery monitor failed at 0x41")
        except Exception as e:
            self.logger.warning(f"⚠️ Battery monitor initialization failed at 0x41: {e}")
        
        if not self.battery_monitor:
            self.logger.warning("⚠️ No working battery monitor found")
        
        # Control state
        self.current_control = ControlData()
        self.last_received = 0
        self.timeout_threshold = 1.0  # 1 second timeout
        self.connection_status = "Disconnected"
        
        # Speed limiting based on gear
        self.gear_speed_limits = {
            'P': 0.0,    # Park - no movement
            'N': 0.0,    # Neutral - no movement  
            'R': 0.4,    # Reverse - 40% max
            'D': 1.0,    # Drive - 100% max
            'M1': 0.1,  # Manual 1 - 25% max
            'M2': 0.2,   # Manual 2 - 50% max
            'M3': 0.3,  # Manual 3 - 75% max
            'M4': 0.4,   # Manual 4 - 100% max
            'M5': 0.5,   # Manual 5 - 100% max
            'M6': 0.6,   # Manual 6 - 100% max
            'M7': 0.7,   # Manual 7 - 100% max
            'M8': 0.8,   # Manual 8 - 100% max
        }
    
    def setup_websocket_bridge(self):
        """WebSocket 브릿지 설정 (UDP 모드에서만)"""
        try:
            import sys
            import os
            
            # 현재 디렉토리를 sys.path에 추가
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            from udp_websocket_bridge import UDPWebSocketBridge
            self.websocket_bridge = UDPWebSocketBridge(
                udp_port=self.udp_port,
                websocket_port=self.websocket_port
            )
            self.logger.info(f"✅ WebSocket 브릿지 준비: UDP {self.udp_port} → WebSocket {self.websocket_port}")
        except ImportError as e:
            self.logger.warning(f"⚠️ udp_websocket_bridge 모듈을 찾을 수 없습니다: {e}")
            self.logger.info(f"🔧 수동 실행: ./run_websocket_bridge.sh {self.udp_port} {self.websocket_port}")
            self.websocket_bridge = None
        except Exception as e:
            self.logger.error(f"❌ WebSocket 브릿지 설정 오류: {e}")
            self.websocket_bridge = None
    
    def setup_server(self) -> bool:
        """Setup server socket to listen for controller"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # If running as root, drop privileges after binding if needed
            if os.geteuid() == 0:
                # Bind to all interfaces with root privileges
                self.server_socket.bind(('0.0.0.0', self.listen_port))
                self.logger.info(f"✅ Server bound to port {self.listen_port} with root privileges (for GPIO access)")
            else:
                # Normal user binding
                self.server_socket.bind(('0.0.0.0', self.listen_port))
                self.logger.info(f"✅ Server bound to port {self.listen_port}")
            
            self.server_socket.listen(1)
            
            # Show network information
            import subprocess
            try:
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                ips = result.stdout.strip().split()
                for ip in ips:
                    if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                        self.logger.info(f"🌐 Access vehicle at: http://{ip}:{self.camera_port}")
                        self.logger.info(f"🎮 Control port: {self.listen_port}")
            except Exception as e:
                self.logger.warning(f"Could not get network info: {e}")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ Server setup failed: {e}")
            return False
    
    def wait_for_controller(self) -> bool:
        """Wait for controller connection"""
        try:
            self.logger.info("🔄 Waiting for controller connection...")
            self.client_socket, client_address = self.server_socket.accept()
            self.client_socket.settimeout(0.1)  # Non-blocking receive
            self.connection_status = "Connected"
            self.logger.info(f"✅ Controller connected from {client_address}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Connection failed: {e}")
            return False
    
    def receive_control_data(self) -> bool:
        """Receive control data from controller"""
        try:
            if not self.client_socket:
                return False
            
            # Receive data with timeout
            data = self.client_socket.recv(1024)
            if not data:
                return False
            
            # Parse JSON data - handle line-by-line
            try:
                # Decode and handle potential line endings
                raw_data = data.decode('utf-8', errors='ignore').strip()
                
                # Split by lines in case multiple messages arrived
                lines = raw_data.split('\n')
                
                # Use the last complete JSON line
                for line in reversed(lines):
                    line = line.strip()
                    if line and line.startswith('{') and line.endswith('}'):
                        self.current_control = ControlData.from_json(line)
                        self.last_received = time.time()
                        break
                
            except (json.JSONDecodeError, ValueError) as e:
                # Log the raw data for debugging
                self.logger.warning(f"⚠️ JSON decode error: {e}, raw data: {data[:50]}")
                return True  # Continue without updating control data
            
            return True
            
        except socket.timeout:
            return True  # Timeout is okay, just no new data
        except Exception as e:
            self.logger.warning(f"⚠️ Receive error: {e}")
            return False
    
    def apply_vehicle_control(self):
        """Apply control data to vehicle with safety checks"""
        try:
            # Check for timeout - stop vehicle if no recent data
            if time.time() - self.last_received > self.timeout_threshold:
                self.vehicle.set_throttle_percent(0.0)
                self.vehicle.set_steering_percent(0.0)
                self.connection_status = "Timeout"
                return
            
            self.connection_status = "Connected"
            
            # Get speed limit based on gear
            gear = self.current_control.gear
            speed_limit = self.gear_speed_limits.get(gear, 0.0)
            
            # Apply gear-based logic
            throttle = self.current_control.throttle
            steering = self.current_control.steering
            
            # POWER MANAGEMENT: Limit max output to prevent undervoltage reboot
            MAX_THROTTLE_LIMIT = 0.75  # 75% max to prevent power issues
            MAX_STEERING_LIMIT = 0.8   # 80% max for steering
            
            if gear == 'P' or gear == 'N':
                # Park or Neutral - no movement
                throttle = 0.0
            elif gear == 'R':
                # Reverse - invert throttle direction
                if throttle > 0:  # Forward input in reverse gear should go backward
                    throttle = 0.0 # Make it go backwards
                elif throttle < 0:
                    throttle = throttle
                # elif throttle < 0:  # Backward input in reverse gear should go forward
                #     throttle = 0.0  # Invert to go forward
            elif gear == 'D' or gear.startswith('M'):
                # Drive or Manual - normal operation
                if throttle < 0:  # Backward input in forward gear
                    throttle = 0.0  # Don't allow backward in forward
                # Forward input (positive) is allowed
            
            # Apply speed limit
            throttle = max(-speed_limit, min(speed_limit, throttle))
            
            # CRITICAL: Apply power limits to prevent reboot
            throttle = max(-MAX_THROTTLE_LIMIT, min(MAX_THROTTLE_LIMIT, throttle))
            steering = max(-MAX_STEERING_LIMIT, min(MAX_STEERING_LIMIT, steering))
            
            # Apply to vehicle (invert steering direction)
            self.vehicle.set_throttle_percent(throttle)
            self.vehicle.set_steering_percent(steering)
            
        except Exception as e:
            self.logger.error(f"❌ Control application error: {e}")
            # Safety: stop vehicle on error
            self.vehicle.set_throttle_percent(0.0)
            self.vehicle.set_steering_percent(0.0)
    
    def update_speed_data(self):
        """Update speed sensor data in separate HIGH PRIORITY thread"""
        # Skip priority changes for system stability
        
        self.logger.info("🔄 Speed data update thread started")
        while self.running:
            try:
                if self.speed_sensor:
                    new_data = self.speed_sensor.get_speed_data()
                    self.current_speed_data = new_data
                    # Debug log every 5 seconds
                    if int(time.time()) % 5 == 0:
                        self.logger.info(f"🔄 Speed data updated: RPM={new_data.get('rpm', 0)}, Speed={new_data.get('speed_kmh', 0.0):.1f}km/h")
                time.sleep(0.01)  # 100Hz update rate (더 빠른 센서 업데이트)
            except Exception as e:
                self.logger.error(f"❌ Speed sensor update error: {e}")
                time.sleep(1)  # Wait before retry
        self.logger.info("🛑 Speed data update thread stopped")
    
    def start_websocket_bridge_with_delay(self):
        """UDP 서버 준비 후 WebSocket 브릿지 시작"""
        # UDP 서버가 완전히 시작될 때까지 대기
        self.logger.info("⏳ UDP 서버 시작 대기 중...")
        time.sleep(3)  # 3초 대기
        
        # UDP 서버 연결 상태 확인 (최대 10회 시도)
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                import socket
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_socket.settimeout(1.0)
                
                # UDP 서버에 테스트 연결
                test_socket.sendto(b'PING', ('localhost', self.udp_port))
                test_socket.close()
                
                self.logger.info(f"✅ UDP 서버 준비 완료 (시도 {attempt + 1}/{max_attempts})")
                break
                
            except Exception as e:
                if attempt < max_attempts - 1:
                    self.logger.info(f"⏳ UDP 서버 대기 중... (시도 {attempt + 1}/{max_attempts})")
                    time.sleep(2)
                else:
                    self.logger.warning(f"⚠️ UDP 서버 확인 실패, 브릿지를 시작합니다: {e}")
                    break
        
        # WebSocket 브릿지 시작
        self.start_websocket_bridge_async()
    
    def start_websocket_bridge_async(self):
        """WebSocket 브릿지를 비동기로 시작"""
        import asyncio
        
        try:
            self.logger.info(f"🚀 WebSocket 브릿지 시작: ws://[ip]:{self.websocket_port}")
            
            # 새로운 이벤트 루프 생성 (스레드에서 실행)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # WebSocket 브릿지 시작
            loop.run_until_complete(
                self.websocket_bridge.start_bridge('localhost')
            )
        except ImportError as e:
            self.logger.error(f"❌ WebSocket 브릿지 모듈 오류: {e}")
            self.logger.info(f"🔧 websockets 라이브러리 설치: pip install websockets")
            self.logger.info(f"🔧 수동 실행: ./run_websocket_bridge.sh {self.udp_port} {self.websocket_port}")
        except Exception as e:
            self.logger.error(f"❌ WebSocket 브릿지 오류: {e}")
            self.logger.info(f"🔧 수동 실행 시도: ./run_websocket_bridge.sh {self.udp_port} {self.websocket_port}")
        finally:
            try:
                loop.close()
            except:
                pass

    def run_dashboard(self):
        """Run dashboard in separate thread"""
        if not PYGAME_AVAILABLE:
            return
            
        try:
            while self.running:
                if not self.dashboard.update(self.current_control, self.connection_status, self.current_speed_data):
                    break
                time.sleep(0.033)  # ~30 FPS
        except Exception as e:
            self.logger.error(f"❌ Dashboard error: {e}")
    
    def run(self):
        """Main vehicle loop"""
        self.logger.info("🚀 Vehicle system starting...")
        
        # Setup server
        if not self.setup_server():
            return
        
        # Start camera streaming
        self.camera_streamer.start_streaming()
        
        # Start WebSocket bridge for UDP streaming (비동기 실행)
        if self.udp_streaming and self.websocket_bridge:
            bridge_thread = threading.Thread(
                target=self.start_websocket_bridge_with_delay, 
                daemon=True
            )
            bridge_thread.start()
            self.logger.info(f"🌉 WebSocket 브릿지가 UDP 서버 준비를 기다리는 중...")
            self.logger.info(f"📡 브라우저 접속: http://[ip]:{self.web_port} (브릿지 준비 후 비디오 시작)")
        else:
            if self.udp_streaming and not self.websocket_bridge:
                self.logger.warning("⚠️ WebSocket 브릿지를 초기화할 수 없습니다")
                self.logger.info(f"🔧 수동 실행: ./run_websocket_bridge.sh {self.udp_port} {self.websocket_port}")
        
        # Start web server for React dashboard
        if self.web_server:
            self.logger.info("🌐 Starting web server for React dashboard...")
            if self.web_server.start():
                self.logger.info(f"✅ Web server ready on http://0.0.0.0:{self.web_port}")
            else:
                self.logger.error("❌ Web server failed to start")
        
        # Start speed sensor
        if self.speed_sensor:
            self.logger.info("🚀 Starting speed sensor...")
            if self.speed_sensor.start():
                self.logger.info("✅ Speed sensor started successfully")
                # Test initial speed data
                initial_data = self.speed_sensor.get_speed_data()
                self.logger.info(f"📊 Initial speed data: {initial_data}")
            else:
                self.logger.warning("⚠️ Speed sensor failed to start")
        else:
            self.logger.warning("⚠️ Speed sensor not initialized")
        
        # Start dashboard thread
        if PYGAME_AVAILABLE:
            dashboard_thread = threading.Thread(target=self.run_dashboard, daemon=True)
            dashboard_thread.start()
        
        # Start speed data update thread
        speed_thread = threading.Thread(target=self.update_speed_data, daemon=True)
        speed_thread.start()
        
        self.running = True
        
        try:
            while self.running:
                # Wait for controller connection
                if not self.wait_for_controller():
                    continue
                
                self.logger.info("🎮 Control loop started")
                
                # Control loop while connected
                while self.running:
                    # Receive control data
                    if not self.receive_control_data():
                        self.logger.warning("⚠️ Controller disconnected")
                        self.connection_status = "Disconnected"
                        if self.client_socket:
                            self.client_socket.close()
                            self.client_socket = None
                        break
                    
                    # Apply control to vehicle
                    self.apply_vehicle_control()
                    
                    # Status logging (every 2 seconds)
                    if int(time.time()) % 2 == 0:
                        speed_info = f" | Speed: {self.current_speed_data['speed_kmh']:.1f}km/h RPM:{self.current_speed_data['rpm']}" if self.speed_sensor else ""
                        self.logger.info(f"📊 T:{self.current_control.throttle:.2f} S:{self.current_control.steering:.2f} G:{self.current_control.gear}{speed_info}")
                    
                    time.sleep(0.05)  # 20Hz update rate
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 Stopping vehicle...")
        except Exception as e:
            self.logger.error(f"❌ Runtime error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        
        # Stop vehicle
        try:
            self.vehicle.set_throttle_percent(0.0)
            self.vehicle.set_steering_percent(0.0)
        except:
            pass
        
        # Close sockets
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        
        # Stop camera streaming
        self.camera_streamer.stop_streaming()
        
        # Stop WebSocket bridge
        if self.websocket_bridge:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.websocket_bridge.stop_bridge())
                loop.close()
                self.logger.info("🛑 WebSocket 브릿지 중지")
            except Exception as e:
                self.logger.warning(f"⚠️ WebSocket 브릿지 중지 오류: {e}")
        
        # Stop web server
        if self.web_server:
            self.web_server.stop()
        
        # Stop speed sensor
        if self.speed_sensor:
            self.speed_sensor.stop()
        
        # Cleanup dashboard
        self.dashboard.cleanup()
        
        self.logger.info("🧹 Vehicle cleanup completed")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RC Car Vehicle System')
    parser.add_argument('--listen-port', type=int, default=8888, help='Controller listen port (default: 8888)')
    parser.add_argument('--camera-port', type=int, default=8080, help='HTTP camera port (default: 8080)')
    parser.add_argument('--web-port', type=int, default=8082, help='Web dashboard port (default: 8082)')
    parser.add_argument('--udp-streaming', action='store_true', help='Use UDP video streaming')
    parser.add_argument('--udp-port', type=int, default=9999, help='UDP streaming port (default: 9999)')
    parser.add_argument('--websocket-port', type=int, default=8765, help='WebSocket bridge port (default: 8765)')
    
    args = parser.parse_args()
    
    print("🚗 RC Car Vehicle System")
    print("=" * 40)
    print(f"🎮 Controller port: {args.listen_port}")
    print(f"🌐 Web dashboard: {args.web_port}")
    
    if args.udp_streaming:
        print(f"🚀 UDP video streaming: {args.udp_port}")
        print(f"🌐 WebSocket bridge: {args.websocket_port}")
        print("📡 브라우저 접속:")
        print(f"  http://[vehicle-ip]:{args.web_port} (UDP 스트림 통합)")
        print("🔧 Direct UDP 클라이언트:")
        print(f"  python3 udp_client.py --host [vehicle-ip] --port {args.udp_port}")
    else:
        print(f"📹 HTTP video streaming: {args.camera_port}")
        print(f"🌐 브라우저 접속: http://[vehicle-ip]:{args.camera_port}")
    
    print("=" * 40)
    
    vehicle = VehicleSystem(
        listen_port=args.listen_port,
        camera_port=args.camera_port, 
        web_port=args.web_port,
        udp_streaming=args.udp_streaming,
        udp_port=args.udp_port,
        websocket_port=args.websocket_port
    )
    vehicle.run()

if __name__ == "__main__":
    main()