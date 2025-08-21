# 🏁 Hannover Makers Fair Team 4 - Advanced RC Car Control System

A sophisticated dual Raspberry Pi RC car system with BMW gear lever integration, real-time camera streaming, and professional-grade control interfaces.

## 🎯 Project Overview

This project implements a cutting-edge RC car control system using two Raspberry Pi devices communicating via TCP sockets. The system features BMW F-series gear lever integration, real-time camera streaming, gamepad control, and a professional dashboard interface.

### Key Features
- **Dual Pi Architecture**: Separate controller and vehicle systems for enhanced reliability
- **BMW Gear Integration**: Authentic BMW F-series gear lever with CAN bus communication
- **Real-time Control**: 20Hz control loop with sub-50ms latency
- **Camera Streaming**: Live video feed accessible via web interface
- **Professional Dashboard**: Real-time telemetry and status monitoring
- **Safety Systems**: Comprehensive timeout protection and emergency stop capabilities

## 🏗️ System Architecture

### Controller Raspberry Pi
- **Primary Function**: Input processing and command transmission
- **Hardware Interface**: ShanWan gamepad + BMW gear lever via CAN bus
- **Communication**: TCP socket client (20Hz transmission rate)
- **Safety**: Connection monitoring and automatic reconnection

### Vehicle Raspberry Pi
- **Primary Function**: Vehicle control and sensor management
- **Hardware Interface**: PiRacer chassis with servo/ESC control
- **Communication**: TCP socket server + HTTP/UDP camera streaming
- **Safety**: Command timeout protection and emergency stop

## 📁 Project Structure

```
Hannover_Makers_Fair_Team4/
├── controller_rpi/              # Controller Pi codebase
│   ├── controller_main.py       # Main control loop with async architecture
│   ├── bmw_lever_controller.py  # BMW gear lever CAN bus interface
│   ├── data_models.py           # Data structures and serialization
│   ├── logger.py                # Professional logging system
│   ├── run_controller.sh        # Production startup script
│   └── requirements.txt         # Python dependencies
│
├── vehicle_rpi/                 # Vehicle Pi codebase
│   ├── vehicle_main.py          # Main vehicle control system
│   ├── camera_stream.py         # HTTP camera streaming server
│   ├── udp_websocket_bridge.py  # WebSocket bridge for telemetry
│   ├── speed_sensor.py          # Vehicle speed monitoring
│   ├── dashboard/               # Web dashboard interface
│   ├── run_vehicle.sh           # Production startup script
│   └── requirements.txt         # Python dependencies
│
├── README.md                    # This file (English)
├── README-KR.md                 # Korean version
└── .gitignore                   # Git ignore patterns
```

## 🔧 Hardware Requirements

### Controller Pi Setup
- **SBC**: Raspberry Pi 4B (4GB+ recommended)
- **Controller**: ShanWan wireless gamepad
- **CAN Interface**: MCP2515 CAN transceiver module
- **Gear Lever**: BMW F-series gear lever assembly
- **Storage**: MicroSD card (32GB+ Class 10)
- **Power**: 5V 3A USB-C power supply

### Vehicle Pi Setup
- **SBC**: Raspberry Pi 4B (4GB+ recommended)
- **Chassis**: PiRacer standard chassis
- **Camera**: Raspberry Pi Camera Module v2 or USB camera
- **Motors**: Standard servo + brushed ESC setup
- **Storage**: MicroSD card (32GB+ Class 10)
- **Power**: Dual power supply (Pi: 5V 3A, Motors: 7.4V LiPo)

### Network Infrastructure
- **Connectivity**: 802.11ac WiFi (5GHz recommended)
- **Topology**: Both devices on same subnet
- **Bandwidth**: Minimum 50Mbps for optimal camera streaming

## ⚙️ Installation & Setup

### 1. Environment Preparation
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-venv git can-utils
```

### 2. Controller Pi Configuration
```bash
cd /home/pi/Hannover_Makers_Fair_Team4/controller_rpi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Configure CAN interface
echo 'dtoverlay=mcp2515-can1,oscillator=16000000,interrupt=25' | sudo tee -a /boot/config.txt
echo 'dtoverlay=spi-bcm2835-overlay' | sudo tee -a /boot/config.txt

# Make startup script executable
chmod +x run_controller.sh
```

### 3. Vehicle Pi Configuration
```bash
cd /home/pi/Hannover_Makers_Fair_Team4/vehicle_rpi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Enable camera interface
sudo raspi-config
# Interface Options -> Camera -> Enable

# Make startup script executable
chmod +x run_vehicle.sh
```

### 4. Network Configuration
Edit network settings in both systems to ensure proper communication:
```bash
# Set static IPs for reliable connection
# Controller Pi: 192.168.86.50 (or auto DHCP)
# Vehicle Pi: 192.168.86.59 (as configured)
```

## 🚀 Operation Guide

### System Startup Sequence
1. **Power up both Raspberry Pi devices**
2. **Start Vehicle Pi first** (TCP server):
   ```bash
   cd /home/pi/Hannover_Makers_Fair_Team4/vehicle_rpi
   sudo ./run_vehicle.sh
   ```
3. **Verify camera streaming**: Navigate to `http://192.168.86.59:8080`
4. **Start Controller Pi** (TCP client):
   ```bash
   cd /home/pi/Hannover_Makers_Fair_Team4/controller_rpi
   sudo ./run_controller.sh
   ```

### Control Interface

#### Gamepad Controls
- **Left Analog Stick (X-axis)**: Steering control (-1.0 to 1.0)
- **Right Analog Stick (Y-axis)**: Throttle control (-1.0 to 1.0)
- **Digital Buttons**: Not used - gear changes require BMW lever

#### BMW Gear Lever (Required for Gear Changes)
- **P (Park)**: Vehicle immobilized (0% throttle response)
- **R (Reverse)**: Reverse operation with 40% speed limit
- **N (Neutral)**: No throttle response (steering only)
- **D (Drive)**: Full speed forward operation (100% throttle)
- **M1-M8**: Manual gear modes with progressive speed scaling (10%-80%)

## 📊 Monitoring & Diagnostics

### Web Interfaces
- **Camera Stream (HTTP)**: `http://[vehicle-ip]:8080/`
- **Camera Stream (UDP + WebSocket)**: `ws://[vehicle-ip]:8765` (with `--udp-streaming`)
- **System Status**: `http://[vehicle-ip]:8080/status`
- **Web Dashboard**: `http://[vehicle-ip]:8082` (React dashboard)

### Log Files
- **Controller Logs**: `controller_rpi/controller.log`
- **Vehicle Logs**: `vehicle_rpi/logs/vehicle.log`
- **System Logs**: `/var/log/syslog`

### Performance Monitoring
- **Control Latency**: <50ms typical
- **Frame Rate**: 15-30 FPS camera stream
- **Network Utilization**: ~5-10 Mbps for video
- **CPU Usage**: 30-50% average load

## 🛡️ Safety & Security Features

### Automatic Safety Systems
- **Connection Timeout**: Vehicle stops if no commands received for 1 second
- **Emergency Stop**: Immediate halt on communication failure
- **Speed Limiting**: Gear-based maximum speed enforcement
- **Input Validation**: Comprehensive command sanitization

### Operational Safety
- **Pre-flight Checks**: Automated system verification before operation
- **Status Monitoring**: Real-time system health indicators
- **Graceful Shutdown**: Proper resource cleanup on termination

## 🔧 Advanced Configuration

### Performance Tuning
```python
# Controller Pi optimization
CONTROL_FREQUENCY = 20  # Hz
NETWORK_TIMEOUT = 1.0   # seconds
RETRY_ATTEMPTS = 3

# Vehicle Pi optimization
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAMERATE = 30
JPEG_QUALITY = 80
```

### Custom Integrations
The system supports additional sensors and actuators through modular design:
- Additional cameras
- Telemetry sensors
- Custom control interfaces
- External data logging

## 🐛 Troubleshooting

### Common Issues

#### Network Connectivity
```bash
# Test basic connectivity
ping [target-ip]

# Check port availability
telnet [target-ip] 8888

# Monitor network traffic
tcpdump -i wlan0 port 8888
```

#### CAN Bus Issues
```bash
# Check CAN interface status
ip link show can0

# Monitor CAN traffic
candump can0

# Reset CAN interface
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 500000
```

#### Camera Problems
```bash
# List available cameras
ls /dev/video*

# Test camera functionality
raspistill -o test.jpg

# Check camera interface
vcgencmd get_camera
```

### Performance Optimization
- Use 5GHz WiFi for reduced latency
- Minimize network hops between devices
- Adjust camera resolution for bandwidth
- Monitor system temperature under load

## 📈 Technical Specifications

### Communication Protocols
- **Control Data**: TCP sockets (port 8888) for reliability
- **Video Streaming**: HTTP (port 8080) or UDP+WebSocket (ports 9999+8765)
- **Data Format**: JSON for human-readable debugging
- **Update Rate**: 20Hz control, 30-60Hz video
- **Latency**: <50ms control, <100ms video

### Control System
- **Architecture**: Event-driven async processing
- **Threading**: Multi-threaded for concurrent operations
- **Error Handling**: Comprehensive exception management
- **Logging**: Professional-grade system logging

### Performance Metrics
- **CPU Usage**: 30-50% average load per Pi
- **Memory Usage**: <1GB typical
- **Network Bandwidth**: 5-10 Mbps for video streaming
- **Power Consumption**: ~15W total system

## 🤝 Contributing

This project is part of the Hannover Makers Fair Team 4 competition entry. The codebase demonstrates advanced embedded systems programming, real-time control, and professional software engineering practices.

### Development Guidelines
- Follow PEP 8 Python coding standards
- Implement comprehensive error handling
- Add logging for debugging and monitoring
- Test thoroughly on actual hardware
- Document all configuration changes

## 📝 License & Credits

Developed by Hannover Makers Fair Team 4 for educational and competitive purposes.

**Key Technologies:**
- Python 3.11+ async/await programming
- TCP socket programming
- CAN bus communication protocols
- Computer vision and streaming
- Real-time embedded control systems

---

*For Korean documentation, see [README-KR.md](README-KR.md)*