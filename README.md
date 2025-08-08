# RC Car Dual Raspberry Pi System
# 듀얼 라즈베리파이 RC카 시스템

A sophisticated RC car control system using two Raspberry Pi devices communicating via TCP sockets, with BMW gear lever integration and real-time camera streaming.

두 개의 라즈베리파이가 TCP 소켓으로 통신하는 고급 RC카 제어 시스템. BMW 기어봉 연동과 실시간 카메라 스트리밍 지원.

## 🚗 System Architecture / 시스템 구조

### Controller Raspberry Pi (컨트롤러 파이)
- **Gamepad Input**: ShanWan wireless controller for throttle and steering
- **BMW Gear Lever**: Reads gear state via CAN bus (P/R/N/D/M1-M8)  
- **Socket Transmission**: Sends control data to vehicle Pi via TCP
- **Real-time Control**: 20Hz update rate for responsive control

### Vehicle Raspberry Pi (차량 파이)  
- **Socket Reception**: Receives control commands from controller Pi
- **Vehicle Control**: Controls PiRacer hardware (throttle + steering)
- **Camera Streaming**: Real-time video streaming via HTTP/Flask
- **Safety Features**: Timeout protection, gear-based speed limiting
- **Dashboard**: Real-time status display with Pygame

## 📁 Project Structure / 프로젝트 구조

```
Hannover_Makers_Fair_Team4/
├── controller_rpi/          # Controller Raspberry Pi code
│   ├── controller_main.py   # Main controller program
│   ├── run_controller.sh    # Startup script
│   └── requirements.txt     # Python dependencies
│
├── vehicle_rpi/            # Vehicle Raspberry Pi code  
│   ├── vehicle_main.py     # Main vehicle program
│   ├── camera_stream.py    # Camera streaming server
│   ├── run_vehicle.sh      # Startup script
│   └── requirements.txt    # Python dependencies
│
├── config.yaml             # System configuration
└── README.md              # This documentation
```

## 🔧 Hardware Requirements / 하드웨어 요구사항

### Controller Pi (컨트롤러 파이)
- Raspberry Pi 4B (recommended)
- ShanWan wireless gamepad controller
- BMW F-Series gear lever (optional)
- CAN transceiver module (for BMW gear)
- MicroSD card (16GB+)

### Vehicle Pi (차량 파이)
- Raspberry Pi 4B (recommended) 
- PiRacer chassis and motors
- Raspberry Pi Camera or USB camera
- MicroSD card (16GB+)
- Power supply for motors

### Network
- WiFi network or direct ethernet connection
- Both Pi devices on same network subnet

## ⚙️ Installation / 설치

### 1. Clone Repository / 저장소 복제
```bash
# Already exists in your system
cd /home/pi/Hannover_Makers_Fair_Team4
```

### 2. Controller Pi Setup / 컨트롤러 파이 설정
```bash
cd controller_rpi

# Install dependencies / 의존성 설치
sudo apt update
sudo apt install -y python3-pip can-utils
pip3 install -r requirements.txt

# Make startup script executable / 시작 스크립트 실행권한 부여
chmod +x run_controller.sh
```

### 3. Vehicle Pi Setup / 차량 파이 설정  
```bash
cd vehicle_rpi

# Install dependencies / 의존성 설치
sudo apt update
sudo apt install -y python3-pip
pip3 install -r requirements.txt

# Enable camera interface / 카메라 인터페이스 활성화
sudo raspi-config
# Advanced Options -> Camera -> Enable

# Make startup script executable / 시작 스크립트 실행권한 부여
chmod +x run_vehicle.sh
```

### 4. Configuration / 설정
Edit `config.yaml` to match your network setup:
```yaml
network:
  controller_ip: "192.168.1.50"    # Your controller Pi IP
  vehicle_ip: "192.168.1.100"      # Your vehicle Pi IP
```

## 🚀 Usage / 사용법

### Start Vehicle Pi First / 차량 파이 먼저 시작
```bash
cd /home/pi/Hannover_Makers_Fair_Team4/vehicle_rpi
sudo ./run_vehicle.sh
```

### Start Controller Pi / 컨트롤러 파이 시작
```bash
cd /home/pi/Hannover_Makers_Fair_Team4/controller_rpi  
sudo ./run_controller.sh
```

### Camera Streaming Only / 카메라 스트리밍만
```bash
cd vehicle_rpi
./run_vehicle.sh --camera-only
```

## 📹 Camera Access / 카메라 접속

- **Web Interface**: `http://[vehicle-ip]:8080`
- **Direct Stream**: `http://[vehicle-ip]:8080/video_feed`
- **Mobile Friendly**: Responsive design for phones/tablets
- **VLC/OBS Compatible**: Use video_feed URL

## 🎮 Controls / 조작법

### Gamepad Controls (게임패드 조작)
- **Left Stick X**: Steering / 조향
- **Right Stick Y**: Throttle / 스로틀  
- **Button A**: Neutral gear / 중립
- **Button B**: Drive gear / 드라이브
- **Button X**: Reverse gear / 후진
- **Button Y**: Park gear / 주차

### BMW Gear Lever (BMW 기어봉) - Optional
- **P**: Park / 주차
- **R**: Reverse / 후진  
- **N**: Neutral / 중립
- **D**: Drive / 드라이브
- **M1-M8**: Manual gears / 수동 기어

## 🛡️ Safety Features / 안전 기능

### Speed Limiting / 속도 제한
- **Park/Neutral**: 0% (no movement) / 정지
- **Reverse**: 40% max speed / 후진 최대 40%
- **Drive**: 100% max speed / 전진 최대 100%
- **Manual**: Variable by gear / 기어별 가변

### Connection Safety / 연결 안전
- **Timeout Protection**: Vehicle stops if connection lost
- **Emergency Stop**: Immediate stop on error
- **Reconnection**: Automatic retry on disconnect

## 📊 Monitoring / 모니터링

### Log Files / 로그 파일
- Controller: `controller_rpi/controller.log`
- Vehicle: `vehicle_rpi/vehicle.log`

### Status Display / 상태 표시
- Real-time dashboard on vehicle Pi
- Console logging on both systems
- Web interface status at `/status`

## 🔧 Troubleshooting / 문제해결

### Common Issues / 일반적 문제

#### Connection Failed / 연결 실패
```bash
# Check network connectivity / 네트워크 연결 확인
ping [vehicle-ip]

# Check if port is open / 포트 확인
telnet [vehicle-ip] 8888
```

#### Camera Not Working / 카메라 작동 안함
```bash
# Check camera detection / 카메라 감지 확인
ls /dev/video*

# Enable camera interface / 카메라 인터페이스 활성화  
sudo raspi-config
```

#### BMW Gear Not Responding / BMW 기어 응답 없음
```bash
# Check CAN interface / CAN 인터페이스 확인
ip link show can0

# Monitor CAN traffic / CAN 트래픽 모니터링
candump can0
```

#### Gamepad Not Detected / 게임패드 감지 안됨
```bash
# Check gamepad connection / 게임패드 연결 확인
ls /dev/input/js*

# Test gamepad input / 게임패드 입력 테스트
jstest /dev/input/js0
```

### Performance Tips / 성능 팁

#### Optimize Network / 네트워크 최적화
- Use 5GHz WiFi for better performance
- Consider direct ethernet connection
- Minimize network latency

#### Camera Performance / 카메라 성능
- Lower resolution for better framerate
- Adjust JPEG quality in config
- Use hardware acceleration when available

## 🔄 System Integration / 시스템 통합

### With Existing Code / 기존 코드와 통합
This system integrates with your existing codebase:
- Uses PiRacer library from `piracer_test/`
- Leverages BMW gear code from `SEA-ME-RCcarCluster/BMW_GWS/`
- Compatible with existing camera streaming from `Hannover_Makers_Fair_Team4/`

### Extensibility / 확장성
- Easy to add new sensors
- Modular design for additional features
- Configuration-driven behavior
- Support for multiple camera types

## 📝 Development Notes / 개발 참고사항

### Code Structure / 코드 구조
- **Object-oriented design**: Modular and maintainable
- **Error handling**: Comprehensive exception management
- **Logging**: Detailed operation logs
- **Configuration**: YAML-based settings

### Communication Protocol / 통신 프로토콜
- **JSON over TCP**: Human-readable, debuggable
- **Real-time**: 20Hz update rate
- **Robust**: Automatic reconnection and error recovery

### Future Enhancements / 향후 개선사항
- [ ] Add telemetry logging
- [ ] Implement multiple camera support  
- [ ] Add mobile app interface
- [ ] Include autonomous navigation
- [ ] Add voice control integration

## 📞 Support / 지원

For issues and questions:
- Check log files first
- Verify hardware connections
- Test network connectivity
- Review configuration settings

---

## 📋 Quick Start Checklist / 빠른 시작 체크리스트

### Pre-flight / 시작 전 확인
- [ ] Both Pi devices powered and connected to network
- [ ] Camera connected and detected
- [ ] Gamepad paired and responsive  
- [ ] BMW gear lever connected (optional)
- [ ] PiRacer hardware properly wired
- [ ] Network IPs configured correctly

### Startup Sequence / 시작 순서
1. [ ] Start vehicle Pi: `sudo ./run_vehicle.sh`
2. [ ] Verify camera stream: `http://[vehicle-ip]:8080`
3. [ ] Start controller Pi: `sudo ./run_controller.sh`
4. [ ] Test gamepad responsiveness
5. [ ] Verify gear shifting (if BMW lever connected)
6. [ ] Ready to drive! / 운전 준비 완료!

---
*Created for Hannover Makers Fair Team 4 - Advanced RC Car Control System*