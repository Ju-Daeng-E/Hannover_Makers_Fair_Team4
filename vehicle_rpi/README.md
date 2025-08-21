# 🚗 Vehicle Raspberry Pi - RC Car Vehicle System

Advanced vehicle control and sensor management system with real-time camera streaming, web dashboard, and professional-grade safety features.

## 🎯 Overview

The Vehicle Raspberry Pi serves as the autonomous vehicle control unit, receiving commands from the controller Pi via TCP sockets, managing PiRacer hardware, providing live camera streaming, and offering comprehensive telemetry through a web dashboard interface.

## 🏗️ System Architecture

### Core Components
- **Vehicle Control System**: Real-time servo and ESC control with PiRacer integration
- **Camera Streaming Server**: Hybrid HTTP/UDP streaming with WebSocket bridge
- **TCP Command Receiver**: Robust socket server with timeout protection and error recovery
- **Web Dashboard**: Real-time telemetry display with responsive design
- **Safety Subsystem**: Comprehensive timeout protection and emergency stop capabilities
- **Telemetry Bridge**: WebSocket and UDP communication for advanced monitoring

### Key Technologies
- **Flask Web Framework**: Professional web server with RESTful API endpoints
- **OpenCV Computer Vision**: Camera capture and image processing pipeline
- **PiRacer Hardware Interface**: Native servo/ESC control with calibrated PWM signals
- **Multi-threading**: Concurrent camera streaming, vehicle control, and web services
- **WebSocket Communication**: Real-time bidirectional telemetry transmission

## 📁 File Structure

```
vehicle_rpi/
├── vehicle_main.py          # Main vehicle control system
├── camera_stream.py         # HTTP camera streaming server
├── udp_websocket_bridge.py  # WebSocket bridge for telemetry
├── speed_sensor.py          # Vehicle speed monitoring (optional)
├── dashboard/               # Web dashboard interface
│   └── dist/               # Built dashboard assets
├── logs/                   # System log files
│   └── vehicle.log         # Vehicle operation logs
├── run_vehicle.sh          # Production startup script
├── requirements.txt        # Python dependencies
└── venv/                   # Virtual environment
```

## 🔧 Hardware Integration

### PiRacer Chassis Integration
- **Servo Control**: 16-bit PWM control (1000-2000μs pulse width)
- **ESC Interface**: Electronic Speed Controller with forward/reverse/brake
- **Power Management**: Dual power supply (Pi: 5V, Motors: 7.4V LiPo)
- **Hardware Specifications**:
  - Servo: 20kg-cm torque for steering
  - ESC: 60A brushed motor controller
  - Chassis: Aluminum frame with suspension

### Camera System
- **Primary**: Raspberry Pi Camera Module v2 (8MP, 1080p30)
- **Alternative**: USB webcam with V4L2 support
- **Features**:
  - Real-time MJPEG streaming at 15-30 FPS
  - Adjustable resolution (320x240 to 1920x1080)
  - Hardware-accelerated H.264 encoding (when available)
  - Auto-exposure and white balance

### Optional Sensors
- **Speed Sensor**: Hall effect sensor with magnetic wheel encoding
- **IMU Integration**: 9-DOF inertial measurement unit
- **GPS Module**: GNSS positioning for telemetry
- **Temperature Monitoring**: System thermal management

## 💻 Software Components

### vehicle_main.py
```python
# Main vehicle control system with safety features
class VehicleSystem:
    - Real-time command processing (20Hz)
    - PiRacer hardware interface
    - Safety timeout monitoring (1s)
    - Gear-based speed limiting
    - Emergency stop capabilities
    - Status telemetry generation
```

**Key Features:**
- **Safety-First Design**: Multiple layers of timeout protection
- **Performance Optimization**: Dedicated threads for I/O and control
- **Hardware Abstraction**: Mock classes for development without hardware
- **Telemetry Integration**: Real-time status broadcasting
- **Error Recovery**: Graceful handling of hardware failures

### camera_stream.py
```python
# High-performance camera streaming server
class CameraStreamer:
    - MJPEG streaming with Flask
    - Multi-client support
    - Bandwidth optimization
    - Hardware acceleration
    - Web interface with controls
```

**Technical Specifications:**
- **Stream Format**: Motion JPEG over HTTP
- **Resolution Options**: 320x240, 640x480, 1280x720, 1920x1080
- **Frame Rate**: 15-30 FPS (configurable)
- **Compression**: JPEG quality 70-95% (adjustable)
- **Latency**: <200ms typical end-to-end

### udp_websocket_bridge.py
```python
# Real-time telemetry communication bridge
class TelemetryBridge:
    - WebSocket server for real-time data
    - UDP client for high-frequency updates
    - Data aggregation and filtering
    - Client connection management
    - Protocol conversion and routing
```

**Communication Protocols:**
- **WebSocket**: Bidirectional real-time communication
- **UDP**: High-frequency telemetry updates
- **HTTP REST API**: Configuration and status queries
- **JSON Messaging**: Human-readable data exchange

### Dashboard Web Interface
```html
<!-- Real-time vehicle telemetry dashboard -->
Features:
- Live camera stream integration
- Real-time control data visualization
- System health monitoring
- Network status indicators
- Mobile-responsive design
- Touch-friendly controls
```

**Dashboard Components:**
- **Live Video Feed**: Embedded camera stream with controls
- **Telemetry Gauges**: Speed, steering angle, throttle position
- **System Status**: CPU, memory, temperature, network
- **Control Interface**: Emergency stop, camera controls
- **Data Logging**: Historical data charts and export

## 🚀 Installation & Configuration

### Hardware Setup
1. **PiRacer Assembly**:
   ```bash
   # Install PiRacer library
   git clone https://github.com/SEA-ME-COSS/PiRacer.git
   cd PiRacer
   sudo ./install.sh
   
   # Test servo and ESC
   python3 -c "
   from piracer.vehicles import PiRacerStandard
   piracer = PiRacerStandard()
   piracer.set_steering_percent(0.0)
   piracer.set_throttle_percent(0.0)
   "
   ```

2. **Camera Configuration**:
   ```bash
   # Enable camera interface
   sudo raspi-config
   # Interface Options -> Camera -> Enable
   
   # Test camera functionality
   raspistill -o test.jpg -t 1000
   
   # Verify V4L2 devices
   ls /dev/video*
   ```

3. **Network Configuration**:
   ```bash
   # Set static IP for reliable communication
   sudo nano /etc/dhcpcd.conf
   # Add:
   # interface wlan0
   # static ip_address=192.168.86.59/24
   # static routers=192.168.86.1
   # static domain_name_servers=192.168.86.1
   ```

### Software Installation
```bash
# Navigate to vehicle directory
cd /home/pi/Hannover_Makers_Fair_Team4/vehicle_rpi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make startup script executable
chmod +x run_vehicle.sh

# Create log directory
mkdir -p logs
```

### Dependencies (requirements.txt)
```
flask>=2.3.3
opencv-python>=4.8.0.76
numpy>=1.24.3
pygame>=2.5.2
websocket-server>=0.6.1
pyyaml>=6.0.1
psutil>=5.9.5
picamera>=1.13
RPi.GPIO>=0.7.1
piracer>=0.1.0
```

## 🔄 Operation Modes

### Standard Vehicle Mode
```bash
# Start complete vehicle system
sudo ./run_vehicle.sh

# Manual start with logging
python3 vehicle_main.py
```

### Camera-Only Mode
```bash
# Start camera streaming only
python3 camera_stream.py

# HTTP mode (default)
python3 camera_stream.py --port 8080 --width 800 --height 600 --fps 30

# UDP mode (high performance) - requires WebSocket bridge for browser access
python3 camera_stream.py --udp --udp-port 9999

# Start WebSocket bridge separately for UDP mode
./run_websocket_bridge.sh 9999 8765
```

### UDP Streaming with WebSocket Bridge
```bash
# Complete UDP streaming setup
# Terminal 1: Start vehicle with UDP streaming
python3 vehicle_main.py --udp-streaming --udp-port 9999 --websocket-port 8765

# WebSocket bridge starts automatically, or manually:
./run_websocket_bridge.sh 9999 8765

# Browser access: ws://[vehicle-ip]:8765 for video stream
# Dashboard access: http://[vehicle-ip]:8082
```

### Development Mode
```bash
# Enable mock hardware for testing
export PIRACER_MOCK=1
export CAMERA_MOCK=1
python3 vehicle_main.py

# Test UDP streaming components separately
python3 udp_client.py --host localhost --port 9999  # Test UDP reception
python3 test_websockets.py  # Test WebSocket connections
./quick_websocket_test.sh   # Quick WebSocket bridge test
```

## 📊 Performance Specifications

### Real-time Performance
- **Command Processing**: 20Hz vehicle control loop (50ms period)
- **Camera Streaming**: 30-60 FPS HTTP/UDP modes at 800x600 resolution
- **Network Latency**: <50ms command response time
- **Safety Response**: <100ms emergency stop activation

### Resource Utilization
- **CPU Usage**: 40-60% average on Pi 4B
- **Memory Usage**: ~400MB typical operation
- **Network Bandwidth**: 2-8 Mbps camera streaming
- **Storage**: ~100MB logs per hour of operation

### Safety Parameters
```python
# Critical safety timeouts and limits
COMMAND_TIMEOUT = 1.0          # seconds - no commands received
EMERGENCY_STOP_TIME = 0.1      # seconds - stop response time
GEAR_SPEED_LIMITS = {
    'P': 0.0,    # Park - no movement
    'N': 0.0,    # Neutral - no movement  
    'R': 0.4,    # Reverse - 40% max speed
    'D': 1.0,    # Drive - 100% max speed
    'M1': 0.3, 'M2': 0.4, 'M3': 0.5, 'M4': 0.6,
    'M5': 0.5, 'M6': 0.6, 'M7': 0.7, 'M8': 0.8
}
```

## 🛡️ Safety & Security Features

### Multi-Layer Safety System
```python
# Comprehensive safety implementation
class SafetySystem:
    - Command timeout monitoring (1 second)
    - Hardware failure detection
    - Emergency stop protocols
    - Speed limiting by gear position
    - Graceful shutdown procedures
    - System health monitoring
```

### Network Security
```python
# Secure communication practices
class NetworkSecurity:
    - Input validation and sanitization
    - Connection rate limiting
    - Access control by IP address
    - Encrypted configuration storage
    - Audit logging of all commands
```

### Hardware Protection
- **Thermal Management**: CPU temperature monitoring and throttling
- **Power Monitoring**: Battery voltage and current sensing
- **Mechanical Limits**: Software-enforced servo angle limits
- **Fault Detection**: Hardware failure detection and reporting

## 🌐 Web Interface & API

### REST API Endpoints
```python
# Vehicle control and monitoring API (from camera_stream.py)
GET  /                    # Dashboard web interface (port 8080)
GET  /video_feed         # MJPEG camera stream
GET  /video_stream_sse   # Server-sent events stream
GET  /status             # System status JSON
# Web dashboard API (port 8082)
GET  /dashboard          # React dashboard interface
```

### WebSocket Real-time API
```javascript
// Real-time telemetry over WebSocket
{
    "type": "telemetry",
    "data": {
        "throttle": 0.0,
        "steering": 0.0,
        "speed": 0.0,
        "gear": "N",
        "cpu_usage": 45.2,
        "temperature": 52.1,
        "timestamp": 1234567890.123
    }
}
```

### Dashboard Features
- **Live Video Stream**: Embedded camera feed with zoom and pan
- **Real-time Charts**: Throttle, steering, and speed visualization  
- **System Metrics**: CPU, memory, network, and temperature gauges
- **Control Panel**: Emergency stop, camera settings, system controls
- **Mobile Responsive**: Touch-optimized interface for tablets/phones

## 🔧 Advanced Configuration

### Performance Tuning
```python
# Optimized configuration for Pi 4B
CAMERA_RESOLUTION = (640, 480)    # Balance of quality and performance
CAMERA_FRAMERATE = 30             # Maximum supported frame rate
JPEG_QUALITY = 80                 # Compression vs quality tradeoff
CONTROL_FREQUENCY = 20            # Hz - vehicle command processing
TELEMETRY_RATE = 10              # Hz - status broadcast frequency
```

### Camera Settings
```python
# Advanced camera configuration
CAMERA_CONFIG = {
    'resolution': (640, 480),
    'framerate': 30,
    'iso': 0,                     # Auto ISO
    'exposure_mode': 'auto',      # Auto exposure
    'awb_mode': 'auto',          # Auto white balance
    'shutter_speed': 0,          # Auto shutter
    'brightness': 50,            # 0-100
    'contrast': 0,               # -100 to 100
    'saturation': 0              # -100 to 100
}
```

### Network Optimization
```python
# TCP socket configuration
SOCKET_CONFIG = {
    'host': '0.0.0.0',           # Listen on all interfaces
    'port': 8888,                # Control command port
    'timeout': 1.0,              # Command timeout
    'buffer_size': 4096,         # Receive buffer size
    'keepalive': True,           # TCP keepalive
    'nodelay': True              # Disable Nagle's algorithm
}
```

## 🐛 Troubleshooting Guide

### Common Issues

#### Camera Stream Not Working
```bash
# Check camera detection
ls /dev/video*
vcgencmd get_camera

# Test camera module
raspistill -o test.jpg

# Check camera permissions
sudo usermod -a -G video pi

# Restart camera service
sudo systemctl restart camera-stream
```

#### PiRacer Control Issues
```bash
# Test PiRacer hardware
python3 -c "
from piracer.vehicles import PiRacerStandard
try:
    piracer = PiRacerStandard()
    print('PiRacer initialized successfully')
except Exception as e:
    print(f'Error: {e}')
"

# Check I2C interface
i2cdetect -y 1

# Verify servo connections
sudo dmesg | grep -i servo
```

#### Network Connectivity
```bash
# Test controller Pi connection
telnet 192.168.86.50 8888

# Check port binding
netstat -tuln | grep 8888

# Monitor network traffic
tcpdump -i wlan0 port 8888

# Test web interface
curl http://localhost:8080/status
```

#### Performance Issues
```bash
# Monitor system resources
htop
iostat 1
iftop

# Check thermal throttling
vcgencmd measure_temp
vcgencmd get_throttled

# Memory usage analysis
free -h
sudo iotop
```

### System Optimization

#### Reduce Latency
```bash
# Real-time kernel (optional)
sudo apt install linux-image-rt-raspi

# CPU governor optimization
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Network stack tuning
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
```

#### Memory Management
```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable cups

# GPU memory split optimization
sudo raspi-config
# Advanced Options -> Memory Split -> 128
```

## 📈 Monitoring & Diagnostics

### Real-time Monitoring
```bash
# System resource monitoring
watch -n 1 'cat /proc/loadavg && free -h && vcgencmd measure_temp'

# Network connection monitoring
ss -tuln | grep -E '(8888|8080)'

# Log file monitoring
tail -f logs/vehicle.log

# Camera stream monitoring
curl -s http://localhost:8080/status | jq '.camera'
```

### Performance Metrics Dashboard
```python
# Built-in performance tracking
class PerformanceMonitor:
    - Real-time FPS measurement
    - Network latency tracking
    - CPU and memory usage
    - Temperature monitoring
    - Command response times
    - Error rate statistics
```

### Health Check System
```bash
# Automated system health verification
./health_check.sh

# Components checked:
# - Camera functionality
# - PiRacer hardware response
# - Network connectivity
# - System resources
# - Log file integrity
```

## 🔮 Future Enhancements

### Planned Features
- [ ] **Autonomous Navigation**: GPS waypoint following with obstacle avoidance
- [ ] **Multi-Camera Support**: Stereo vision and 360-degree viewing
- [ ] **Advanced Telemetry**: IMU integration, speed sensors, GPS tracking
- [ ] **Machine Learning**: Object detection and autonomous behavior
- [ ] **Cloud Integration**: Remote monitoring and control capabilities

### Technical Improvements
- [ ] **Hardware Acceleration**: GPU-accelerated computer vision
- [ ] **Real-time Communication**: Ultra-low latency control protocols
- [ ] **Redundant Systems**: Multiple sensor fusion and backup systems
- [ ] **Advanced Dashboard**: 3D visualization and augmented reality

### Integration Possibilities
- [ ] **ROS2 Integration**: Robot Operating System compatibility
- [ ] **MQTT Telemetry**: IoT platform integration
- [ ] **Mobile Applications**: Native iOS/Android control apps
- [ ] **Voice Control**: Speech recognition and synthesis

---

*For Korean documentation, see [README-KR.md](README-KR.md)*  
*For controller Pi documentation, see [../controller_rpi/README.md](../controller_rpi/README.md)*