# 🚗 차량 라즈베리파이 - RC카 차량 시스템

실시간 카메라 스트리밍, 웹 대시보드, 전문급 안전 기능을 갖춘 고급 차량 제어 및 센서 관리 시스템입니다.

## 🎯 개요

차량 라즈베리파이는 자율 차량 제어 장치 역할을 하며, TCP 소켓을 통해 컨트롤러 파이로부터 명령을 수신하고, PiRacer 하드웨어를 관리하며, 라이브 카메라 스트리밍을 제공하고, 웹 대시보드 인터페이스를 통해 포괄적인 텔레메트리를 제공합니다.

## 🏗️ 시스템 아키텍처

### 핵심 구성요소
- **차량 제어 시스템**: PiRacer 통합을 통한 실시간 서보 및 ESC 제어
- **카메라 스트리밍 서버**: 웹 인터페이스가 있는 고성능 MJPEG 스트리밍
- **TCP 명령 수신기**: 타임아웃 보호 및 오류 복구가 있는 견고한 소켓 서버
- **웹 대시보드**: 반응형 디자인의 실시간 텔레메트리 디스플레이
- **안전 하위시스템**: 포괄적인 타임아웃 보호 및 비상 정지 기능
- **텔레메트리 브리지**: 고급 모니터링을 위한 WebSocket 및 UDP 통신

### 주요 기술
- **Flask 웹 프레임워크**: RESTful API 엔드포인트가 있는 전문 웹 서버
- **OpenCV 컴퓨터 비전**: 카메라 캡처 및 이미지 처리 파이프라인
- **PiRacer 하드웨어 인터페이스**: 보정된 PWM 신호를 통한 네이티브 서보/ESC 제어
- **멀티스레딩**: 동시 카메라 스트리밍, 차량 제어 및 웹 서비스
- **WebSocket 통신**: 실시간 양방향 텔레메트리 전송

## 📁 파일 구조

```
vehicle_rpi/
├── vehicle_main.py          # 메인 차량 제어 시스템
├── camera_stream.py         # HTTP 카메라 스트리밍 서버
├── udp_websocket_bridge.py  # 텔레메트리용 WebSocket 브리지
├── speed_sensor.py          # 차량 속도 모니터링 (옵션)
├── dashboard/               # 웹 대시보드 인터페이스
│   └── dist/               # 빌드된 대시보드 에셋
├── logs/                   # 시스템 로그 파일
│   └── vehicle.log         # 차량 작동 로그
├── run_vehicle.sh          # 프로덕션 시작 스크립트
├── requirements.txt        # Python 의존성
└── venv/                   # 가상 환경
```

## 🔧 하드웨어 통합

### PiRacer 섀시 통합
- **서보 제어**: 16비트 PWM 제어 (1000-2000μs 펄스 폭)
- **ESC 인터페이스**: 전진/후진/브레이크가 있는 전자 속도 컨트롤러
- **전원 관리**: 듀얼 전원 공급장치 (파이: 5V, 모터: 7.4V LiPo)
- **하드웨어 사양**:
  - 서보: 조향용 20kg-cm 토크
  - ESC: 60A 브러시 모터 컨트롤러
  - 섀시: 서스펜션이 있는 알루미늄 프레임

### 카메라 시스템
- **기본**: 라즈베리파이 카메라 모듈 v2 (8MP, 1080p30)
- **대안**: V4L2 지원 USB 웹캠
- **기능**:
  - 15-30 FPS의 실시간 MJPEG 스트리밍
  - 조정 가능한 해상도 (320x240 ~ 1920x1080)
  - 하드웨어 가속 H.264 인코딩 (사용 가능시)
  - 자동 노출 및 화이트 밸런스

### 옵션 센서
- **속도 센서**: 자석 휠 인코딩이 있는 홀 효과 센서
- **IMU 통합**: 9-DOF 관성 측정 장치
- **GPS 모듈**: 텔레메트리용 GNSS 위치 확인
- **온도 모니터링**: 시스템 열 관리

## 💻 소프트웨어 구성요소

### vehicle_main.py
```python
# 안전 기능이 있는 메인 차량 제어 시스템
class VehicleSystem:
    - 실시간 명령 처리 (20Hz)
    - PiRacer 하드웨어 인터페이스
    - 안전 타임아웃 모니터링 (1s)
    - 기어 기반 속도 제한
    - 비상 정지 기능
    - 상태 텔레메트리 생성
```

**주요 기능:**
- **안전 우선 설계**: 다중 레이어 타임아웃 보호
- **성능 최적화**: I/O 및 제어용 전용 스레드
- **하드웨어 추상화**: 하드웨어 없이 개발을 위한 모의 클래스
- **텔레메트리 통합**: 실시간 상태 브로드캐스팅
- **오류 복구**: 하드웨어 장애의 우아한 처리

### camera_stream.py
```python
# 고성능 카메라 스트리밍 서버
class CameraStreamer:
    - Flask를 사용한 MJPEG 스트리밍
    - 다중 클라이언트 지원
    - 대역폭 최적화
    - 하드웨어 가속
    - 컨트롤이 있는 웹 인터페이스
```

**기술적 사양:**
- **스트림 형식**: HTTP를 통한 Motion JPEG
- **해상도 옵션**: 320x240, 640x480, 1280x720, 1920x1080
- **프레임 레이트**: 15-30 FPS (구성 가능)
- **압축**: JPEG 품질 70-95% (조정 가능)
- **지연시간**: 일반적으로 종단 간 200ms 미만

### udp_websocket_bridge.py
```python
# 실시간 텔레메트리 통신 브리지
class TelemetryBridge:
    - 실시간 데이터용 WebSocket 서버
    - 고주파수 업데이트용 UDP 클라이언트
    - 데이터 집계 및 필터링
    - 클라이언트 연결 관리
    - 프로토콜 변환 및 라우팅
```

**통신 프로토콜:**
- **WebSocket**: 양방향 실시간 통신
- **UDP**: 고주파수 텔레메트리 업데이트
- **HTTP REST API**: 구성 및 상태 쿼리
- **JSON 메시징**: 사람이 읽을 수 있는 데이터 교환

### 대시보드 웹 인터페이스
```html
<!-- 실시간 차량 텔레메트리 대시보드 -->
기능:
- 라이브 카메라 스트림 통합
- 실시간 제어 데이터 시각화
- 시스템 상태 모니터링
- 네트워크 상태 표시기
- 모바일 반응형 디자인
- 터치 친화적 컨트롤
```

**대시보드 구성요소:**
- **라이브 비디오 피드**: 컨트롤이 있는 임베디드 카메라 스트림
- **텔레메트리 게이지**: 속도, 조향각, 스로틀 위치
- **시스템 상태**: CPU, 메모리, 온도, 네트워크
- **제어 인터페이스**: 비상 정지, 카메라 컨트롤
- **데이터 로깅**: 기록 데이터 차트 및 내보내기

## 🚀 설치 및 구성

### 하드웨어 설정
1. **PiRacer 조립**:
   ```bash
   # PiRacer 라이브러리 설치
   git clone https://github.com/SEA-ME-COSS/PiRacer.git
   cd PiRacer
   sudo ./install.sh
   
   # 서보 및 ESC 테스트
   python3 -c "
   from piracer.vehicles import PiRacerStandard
   piracer = PiRacerStandard()
   piracer.set_steering_percent(0.0)
   piracer.set_throttle_percent(0.0)
   "
   ```

2. **카메라 구성**:
   ```bash
   # 카메라 인터페이스 활성화
   sudo raspi-config
   # Interface Options -> Camera -> Enable
   
   # 카메라 기능 테스트
   raspistill -o test.jpg -t 1000
   
   # V4L2 장치 확인
   ls /dev/video*
   ```

3. **네트워크 구성**:
   ```bash
   # 안정적인 통신을 위한 고정 IP 설정
   sudo nano /etc/dhcpcd.conf
   # 추가:
   # interface wlan0
   # static ip_address=192.168.1.100/24
   # static routers=192.168.1.1
   # static domain_name_servers=192.168.1.1
   ```

### 소프트웨어 설치
```bash
# 차량 디렉토리로 이동
cd /home/pi/Hannover_Makers_Fair_Team4/vehicle_rpi

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 시작 스크립트 실행 권한 부여
chmod +x run_vehicle.sh

# 로그 디렉토리 생성
mkdir -p logs
```

### 의존성 (requirements.txt)
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

## 🔄 작동 모드

### 표준 차량 모드
```bash
# 완전한 차량 시스템 시작
sudo ./run_vehicle.sh

# 로깅이 있는 수동 시작
python3 vehicle_main.py
```

### 카메라 전용 모드
```bash
# 카메라 스트리밍만 시작
python3 camera_stream.py

# 사용자 정의 구성
python3 camera_stream.py --resolution 1280x720 --fps 30 --quality 85
```

### 개발 모드
```bash
# 테스트용 모의 하드웨어 활성화
export PIRACER_MOCK=1
export CAMERA_MOCK=1
python3 vehicle_main.py
```

## 📊 성능 사양

### 실시간 성능
- **명령 처리**: 20Hz 차량 제어 루프
- **카메라 스트리밍**: 640x480 해상도에서 15-30 FPS
- **네트워크 지연시간**: 명령 응답 시간 50ms 미만
- **안전 응답**: 비상 정지 활성화 100ms 미만

### 리소스 사용률
- **CPU 사용량**: Pi 4B에서 평균 40-60%
- **메모리 사용량**: 일반 작동 시 ~400MB
- **네트워크 대역폭**: 카메라 스트리밍 2-8 Mbps
- **저장소**: 작동 시간당 ~100MB 로그

### 안전 매개변수
```python
# 중요한 안전 타임아웃 및 제한
COMMAND_TIMEOUT = 1.0          # 초 - 명령 수신 안됨
EMERGENCY_STOP_TIME = 0.1      # 초 - 정지 응답 시간
GEAR_SPEED_LIMITS = {
    'P': 0.0,    # 주차 - 움직임 없음
    'N': 0.0,    # 중립 - 움직임 없음  
    'R': 0.4,    # 후진 - 최대 속도 40%
    'D': 1.0,    # 전진 - 최대 속도 100%
    'M1': 0.3, 'M2': 0.4, 'M3': 0.5, 'M4': 0.6,
    'M5': 0.7, 'M6': 0.8, 'M7': 0.9, 'M8': 1.0
}
```

## 🛡️ 안전 및 보안 기능

### 다중 레이어 안전 시스템
```python
# 포괄적인 안전 구현
class SafetySystem:
    - 명령 타임아웃 모니터링 (1초)
    - 하드웨어 장애 감지
    - 비상 정지 프로토콜
    - 기어 위치별 속도 제한
    - 우아한 종료 절차
    - 시스템 상태 모니터링
```

### 네트워크 보안
```python
# 보안 통신 관행
class NetworkSecurity:
    - 입력 검증 및 살균
    - 연결 속도 제한
    - IP 주소별 액세스 제어
    - 암호화된 구성 저장
    - 모든 명령의 감사 로깅
```

### 하드웨어 보호
- **열 관리**: CPU 온도 모니터링 및 스로틀링
- **전력 모니터링**: 배터리 전압 및 전류 감지
- **기계적 제한**: 소프트웨어가 강제하는 서보 각도 제한
- **장애 감지**: 하드웨어 장애 감지 및 보고

## 🌐 웹 인터페이스 및 API

### REST API 엔드포인트
```python
# 차량 제어 및 모니터링 API
GET  /                    # 대시보드 웹 인터페이스
GET  /video_feed         # MJPEG 카메라 스트림
GET  /status             # 시스템 상태 JSON
POST /emergency_stop     # 즉시 차량 정지
GET  /logs               # 시스템 로그 액세스
POST /config             # 구성 업데이트
```

### WebSocket 실시간 API
```javascript
// WebSocket을 통한 실시간 텔레메트리
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

### 대시보드 기능
- **라이브 비디오 스트림**: 줌 및 팬이 가능한 임베디드 카메라 피드
- **실시간 차트**: 스로틀, 조향 및 속도 시각화  
- **시스템 메트릭**: CPU, 메모리, 네트워크 및 온도 게이지
- **제어 패널**: 비상 정지, 카메라 설정, 시스템 컨트롤
- **모바일 반응형**: 태블릿/폰용 터치 최적화 인터페이스

## 🔧 고급 구성

### 성능 튜닝
```python
# Pi 4B를 위한 최적화된 구성
CAMERA_RESOLUTION = (640, 480)    # 품질과 성능의 균형
CAMERA_FRAMERATE = 30             # 지원되는 최대 프레임 레이트
JPEG_QUALITY = 80                 # 압축 대 품질 절충
CONTROL_FREQUENCY = 20            # Hz - 차량 명령 처리
TELEMETRY_RATE = 10              # Hz - 상태 브로드캐스트 빈도
```

### 카메라 설정
```python
# 고급 카메라 구성
CAMERA_CONFIG = {
    'resolution': (640, 480),
    'framerate': 30,
    'iso': 0,                     # 자동 ISO
    'exposure_mode': 'auto',      # 자동 노출
    'awb_mode': 'auto',          # 자동 화이트 밸런스
    'shutter_speed': 0,          # 자동 셔터
    'brightness': 50,            # 0-100
    'contrast': 0,               # -100 ~ 100
    'saturation': 0              # -100 ~ 100
}
```

### 네트워크 최적화
```python
# TCP 소켓 구성
SOCKET_CONFIG = {
    'host': '0.0.0.0',           # 모든 인터페이스에서 수신
    'port': 8888,                # 제어 명령 포트
    'timeout': 1.0,              # 명령 타임아웃
    'buffer_size': 4096,         # 수신 버퍼 크기
    'keepalive': True,           # TCP keepalive
    'nodelay': True              # Nagle 알고리즘 비활성화
}
```

## 🐛 문제 해결 가이드

### 일반적인 문제

#### 카메라 스트림 작동 안함
```bash
# 카메라 감지 확인
ls /dev/video*
vcgencmd get_camera

# 카메라 모듈 테스트
raspistill -o test.jpg

# 카메라 권한 확인
sudo usermod -a -G video pi

# 카메라 서비스 재시작
sudo systemctl restart camera-stream
```

#### PiRacer 제어 문제
```bash
# PiRacer 하드웨어 테스트
python3 -c "
from piracer.vehicles import PiRacerStandard
try:
    piracer = PiRacerStandard()
    print('PiRacer 초기화 성공')
except Exception as e:
    print(f'오류: {e}')
"

# I2C 인터페이스 확인
i2cdetect -y 1

# 서보 연결 확인
sudo dmesg | grep -i servo
```

#### 네트워크 연결
```bash
# 컨트롤러 파이 연결 테스트
telnet 192.168.1.50 8888

# 포트 바인딩 확인
netstat -tuln | grep 8888

# 네트워크 트래픽 모니터링
tcpdump -i wlan0 port 8888

# 웹 인터페이스 테스트
curl http://localhost:8080/status
```

#### 성능 문제
```bash
# 시스템 리소스 모니터링
htop
iostat 1
iftop

# 열 스로틀링 확인
vcgencmd measure_temp
vcgencmd get_throttled

# 메모리 사용량 분석
free -h
sudo iotop
```

### 시스템 최적화

#### 지연시간 감소
```bash
# 실시간 커널 (옵션)
sudo apt install linux-image-rt-raspi

# CPU 가버너 최적화
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 네트워크 스택 튜닝
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
```

#### 메모리 관리
```bash
# 불필요한 서비스 비활성화
sudo systemctl disable bluetooth
sudo systemctl disable cups

# GPU 메모리 분할 최적화
sudo raspi-config
# Advanced Options -> Memory Split -> 128
```

## 📈 모니터링 및 진단

### 실시간 모니터링
```bash
# 시스템 리소스 모니터링
watch -n 1 'cat /proc/loadavg && free -h && vcgencmd measure_temp'

# 네트워크 연결 모니터링
ss -tuln | grep -E '(8888|8080)'

# 로그 파일 모니터링
tail -f logs/vehicle.log

# 카메라 스트림 모니터링
curl -s http://localhost:8080/status | jq '.camera'
```

### 성능 메트릭 대시보드
```python
# 내장 성능 추적
class PerformanceMonitor:
    - 실시간 FPS 측정
    - 네트워크 지연시간 추적
    - CPU 및 메모리 사용량
    - 온도 모니터링
    - 명령 응답 시간
    - 오류율 통계
```

### 상태 검사 시스템
```bash
# 자동화된 시스템 상태 확인
./health_check.sh

# 확인되는 구성요소:
# - 카메라 기능
# - PiRacer 하드웨어 응답
# - 네트워크 연결
# - 시스템 리소스
# - 로그 파일 무결성
```

## 🔮 향후 개선사항

### 계획된 기능
- [ ] **자율 내비게이션**: 장애물 회피가 있는 GPS 웨이포인트 추적
- [ ] **다중 카메라 지원**: 스테레오 비전 및 360도 보기
- [ ] **고급 텔레메트리**: IMU 통합, 속도 센서, GPS 추적
- [ ] **머신러닝**: 객체 감지 및 자율 행동
- [ ] **클라우드 통합**: 원격 모니터링 및 제어 기능

### 기술적 개선사항
- [ ] **하드웨어 가속**: GPU 가속 컴퓨터 비전
- [ ] **실시간 통신**: 초저지연 제어 프로토콜
- [ ] **중복 시스템**: 다중 센서 융합 및 백업 시스템
- [ ] **고급 대시보드**: 3D 시각화 및 증강 현실

### 통합 가능성
- [ ] **ROS2 통합**: 로봇 운영 체제 호환성
- [ ] **MQTT 텔레메트리**: IoT 플랫폼 통합
- [ ] **모바일 애플리케이션**: 네이티브 iOS/Android 제어 앱
- [ ] **음성 제어**: 음성 인식 및 합성

---

*영어 문서는 [README.md](README.md)를 참조하세요*  
*컨트롤러 파이 문서는 [../controller_rpi/README.md](../controller_rpi/README.md)를 참조하세요*