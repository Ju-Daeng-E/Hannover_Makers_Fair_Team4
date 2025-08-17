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
    
    def __init__(self, port: int = 8080):
        self.port = port
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
                
                # Use the shell script wrapper that uses system Python
                self.process = subprocess.Popen([
                    'bash', camera_script,
                    '--port', str(self.port)
                ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Give it time to start and check if it's running
                time.sleep(3)
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
                # Try direct system python call
                camera_py = os.path.join(script_dir, "camera_stream.py")
                if os.path.exists(camera_py):
                    self.process = subprocess.Popen([
                        '/usr/bin/python3', camera_py,
                        '--port', str(self.port)
                    ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    # Give it time to start and check if it's running
                    time.sleep(3)
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
                
                # 데이터 유효성 확인
                data_age = speed_data.get('age_seconds', 999)
                is_fresh = data_age < 5.0  # 5초 이내 데이터만 신뢰
                print(f"🔍 API Debug - data_age: {data_age}, is_fresh: {is_fresh}")
                
                if is_fresh:
                    # 신선한 실제 센서 데이터
                    data = {
                        'rpmValue': int(speed_data.get('rpm', 0)),
                        'speedValue': float(speed_data.get('speed_kmh', 0.0)),
                        'gear': self.vehicle_system.current_control.gear,
                        'fuelLevel': 75 + random.randint(-2, 2),  # 시뮬레이션
                        'engineTemp': 90 + random.randint(-2, 2),  # 시뮬레이션
                        'batteryLevel': 85 + random.randint(-2, 2),  # 시뮬레이션
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
                        'fuelLevel': 75,
                        'engineTemp': 90,
                        'batteryLevel': 85,
                        'connectionStatus': self.vehicle_system.connection_status,
                        'sensorStatus': 'stale',
                        'dataAge': round(data_age, 1)
                    }
            else:
                # 센서 없거나 시스템 없음
                data = {
                    'rpmValue': 0,
                    'speedValue': 0.0,
                    'gear': 'N',
                    'fuelLevel': 75,
                    'engineTemp': 90,
                    'batteryLevel': 85,
                    'connectionStatus': 'Disconnected',
                    'sensorStatus': 'unavailable',
                    'dataAge': 999
                }
            return jsonify(data)
        
        @self.app.route('/video_feed')
        def video_feed():
            """카메라 피드 (프록시)"""
            try:
                import requests
                # Proxy camera stream from camera server
                camera_url = f'http://localhost:{self.vehicle_system.camera_port}/video_feed'
                
                def generate():
                    try:
                        response = requests.get(camera_url, stream=True, timeout=5)
                        if response.status_code == 200:
                            for chunk in response.iter_content(chunk_size=1024):
                                if chunk:
                                    yield chunk
                        else:
                            # Return error frame
                            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                            yield self.get_error_frame()
                            yield b'\r\n'
                    except Exception as e:
                        print(f"Camera proxy error: {e}")
                        # Return error frame
                        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                        yield self.get_error_frame()
                        yield b'\r\n'
                
                return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
                
            except ImportError:
                # If requests is not available, redirect to camera port
                from flask import redirect
                return redirect(f'http://localhost:{self.vehicle_system.camera_port}/video_feed')
            except Exception as e:
                print(f"Video feed error: {e}")
                return f"Camera feed unavailable: {e}", 503
        
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
    
    def get_error_frame(self):
        """Generate error frame for camera feed"""
        try:
            import cv2
            import numpy as np
            
            # Create a simple error frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame.fill(30)  # Dark gray background
            
            # Add error message
            cv2.putText(frame, "Camera Unavailable", (150, 220), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (128, 128, 128), 2)
            cv2.putText(frame, "Checking connection...", (180, 260), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (128, 128, 128), 1)
            
            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                return buffer.tobytes()
        except Exception:
            pass
        
        # Fallback: return minimal JPEG header
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x01\xe0\x02\x80\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xff\xd9'
    
    def start(self):
        """Start web server in separate thread"""
        if not FLASK_AVAILABLE or not self.app:
            print("⚠️ Web server unavailable - Flask not installed")
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
    
    def __init__(self, listen_port: int = 8888, camera_port: int = 8080, web_port: int = 8082):
        self.listen_port = listen_port
        self.camera_port = camera_port
        self.web_port = web_port
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
        self.camera_streamer = CameraStreamer(camera_port)
        
        # Initialize dashboard
        self.dashboard = Dashboard()
        
        # Initialize web server for React dashboard
        self.web_server = WebServer(self.web_port, self)
        
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
        """Update speed sensor data in separate thread"""
        while self.running:
            try:
                if self.speed_sensor:
                    self.current_speed_data = self.speed_sensor.get_speed_data()
                time.sleep(0.01)  # 10Hz update rate
            except Exception as e:
                self.logger.error(f"❌ Speed sensor update error: {e}")
                time.sleep(1)  # Wait before retry

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
        
        # Start web server for React dashboard
        if self.web_server:
            self.web_server.start()
        
        # Start speed sensor
        if self.speed_sensor:
            if self.speed_sensor.start():
                self.logger.info("✅ Speed sensor started")
            else:
                self.logger.warning("⚠️ Speed sensor failed to start")
        
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
    print("🚗 RC Car Vehicle System")
    print("=" * 40)
    
    # Configuration
    LISTEN_PORT = 8888      # Port to listen for controller (changed to avoid conflict)
    CAMERA_PORT = 8080      # Port for camera streaming (changed to avoid conflict)
    WEB_PORT = 8082         # Port for web dashboard (changed to avoid conflict)
    
    vehicle = VehicleSystem(LISTEN_PORT, CAMERA_PORT, WEB_PORT)
    vehicle.run()

if __name__ == "__main__":
    main()