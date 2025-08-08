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
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any
from multiprocessing import Process, Value, Array

try:
    from piracer.vehicles import PiRacerStandard
    PIRACER_AVAILABLE = True
except ImportError:
    print("⚠️ PiRacer library not available - using mock vehicle")
    PIRACER_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    print("⚠️ Pygame not available - dashboard disabled")
    PYGAME_AVAILABLE = False

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
        
    def update(self, control_data: ControlData, connection_status: str):
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
            
            # Timestamp
            time_text = self.font.render(f"Last Update: {datetime.now().strftime('%H:%M:%S')}", True, (128, 128, 128))
            self.screen.blit(time_text, (10, 170))
            
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

class VehicleSystem:
    """Main vehicle system"""
    
    def __init__(self, listen_port: int = 8888, camera_port: int = 8080):
        self.listen_port = listen_port
        self.camera_port = camera_port
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
            'M1': 0.25,  # Manual 1 - 25% max
            'M2': 0.5,   # Manual 2 - 50% max
            'M3': 0.75,  # Manual 3 - 75% max
            'M4': 1.0,   # Manual 4 - 100% max
            'M5': 1.0,   # Manual 5 - 100% max
            'M6': 1.0,   # Manual 6 - 100% max
            'M7': 1.0,   # Manual 7 - 100% max
            'M8': 1.0,   # Manual 8 - 100% max
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
            
            if gear == 'P' or gear == 'N':
                # Park or Neutral - no movement
                throttle = 0.0
            elif gear == 'R':
                # Reverse - invert throttle direction if needed
                if throttle < 0:  # Forward input in reverse gear
                    throttle = abs(throttle)  # Make it go backwards
                elif throttle > 0:  # Backward input in reverse gear  
                    throttle = 0.0  # Don't allow forward in reverse
            elif gear == 'D' or gear.startswith('M'):
                # Drive or Manual - normal operation
                if throttle > 0:  # Backward input in forward gear
                    throttle = 0.0  # Don't allow backward in forward
                # Forward input (negative) is allowed
            
            # Apply speed limit
            throttle = max(-speed_limit, min(speed_limit, throttle))
            
            # Apply to vehicle
            self.vehicle.set_throttle_percent(throttle)
            self.vehicle.set_steering_percent(steering)
            
        except Exception as e:
            self.logger.error(f"❌ Control application error: {e}")
            # Safety: stop vehicle on error
            self.vehicle.set_throttle_percent(0.0)
            self.vehicle.set_steering_percent(0.0)
    
    def run_dashboard(self):
        """Run dashboard in separate thread"""
        if not PYGAME_AVAILABLE:
            return
            
        try:
            while self.running:
                if not self.dashboard.update(self.current_control, self.connection_status):
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
        
        # Start dashboard thread
        if PYGAME_AVAILABLE:
            dashboard_thread = threading.Thread(target=self.run_dashboard, daemon=True)
            dashboard_thread.start()
        
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
                        self.logger.info(f"📊 T:{self.current_control.throttle:.2f} S:{self.current_control.steering:.2f} G:{self.current_control.gear}")
                    
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
        
        # Cleanup dashboard
        self.dashboard.cleanup()
        
        self.logger.info("🧹 Vehicle cleanup completed")

def main():
    """Main entry point"""
    print("🚗 RC Car Vehicle System")
    print("=" * 40)
    
    # Configuration
    LISTEN_PORT = 8888      # Port to listen for controller
    CAMERA_PORT = 8080      # Port for camera streaming
    
    vehicle = VehicleSystem(LISTEN_PORT, CAMERA_PORT)
    vehicle.run()

if __name__ == "__main__":
    main()