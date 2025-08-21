# 🎮 컨트롤러 라즈베리파이 - RC카 제어 시스템

BMW 기어 레버 통합 및 게임패드 지원을 통한 RC카 제어를 위한 고급 입력 처리 및 명령 전송 시스템입니다.

## 🎯 개요

컨트롤러 라즈베리파이는 RC카 시스템의 주요 입력 인터페이스 역할을 하며, 게임패드 입력, CAN 버스를 통한 BMW 기어 레버 통신, TCP 소켓을 통한 차량 파이로의 실시간 명령 전송을 처리합니다.

## 🏗️ 시스템 아키텍처

### 핵심 구성요소
- **비동기 아키텍처**: 게임패드와 네트워크 통신을 위한 별도 루프가 있는 이벤트 기반 설계
- **입력 처리**: 아날로그 스틱과 버튼 매핑이 가능한 ShanWan 게임패드 통합
- **CAN 버스 인터페이스**: CRC 검증을 통한 BMW F-시리즈 기어 레버 통신
- **네트워크 통신**: 자동 재연결 및 오류 처리가 가능한 TCP 소켓 클라이언트
- **안전 시스템**: 연결 모니터링, 타임아웃 보호, 우아한 오류 복구

### 주요 기술
- **Python 3.11+ asyncio**: 고성능 비동기 프로그래밍
- **CAN 버스 프로토콜**: BMW 전용 메시지 형식의 ISO 11898 표준
- **TCP 소켓 프로그래밍**: JSON 직렬화를 통한 신뢰할 수 있는 통신
- **멀티스레딩**: 동시 BMW 기어 모니터링 및 LED 제어
- **전문 로깅**: 포괄적인 시스템 모니터링 및 디버깅

## 📁 파일 구조

```
controller_rpi/
├── controller_main.py       # 메인 애플리케이션 진입점
├── bmw_lever_controller.py  # BMW 기어 레버 CAN 버스 인터페이스
├── data_models.py           # 데이터 구조 및 직렬화
├── logger.py                # 전문 로깅 시스템
├── run_controller.sh        # 프로덕션 시작 스크립트
├── requirements.txt         # Python 의존성
└── venv/                    # 가상 환경
```

## 🔧 하드웨어 통합

### ShanWan 게임패드 컨트롤러
- **연결**: USB 무선 수신기 (2.4GHz)
- **입력 매핑**:
  - 왼쪽 아날로그 스틱 X: 조향 제어 (-1.0 ~ 1.0)
  - 오른쪽 아날로그 스틱 Y: 스로틀 제어 (-1.0 ~ 1.0)
  - 디지털 버튼: 기어 선택 (A/B/X/Y)
- **샘플링 속도**: 반응성 있는 제어를 위한 50Hz

### BMW F-시리즈 기어 레버
- **통신**: 500kbps의 CAN 버스
- **하드웨어**: MCP2515 CAN 트랜시버 + TJA1050 라인 드라이버
- **메시지 ID**:
  - `0x197`: 기어 레버 위치 메시지 (8바이트)
  - `0x1F6`: 기어 LED 제어 메시지 (8바이트)
  - `0x3FD`: 백라이트 제어 메시지 (8바이트)
- **기능**:
  - 정품 기어 위치 (P/R/N/D/M1-M8)
  - 위치 표시가 있는 LED 피드백
  - 데이터 무결성을 위한 CRC-8 검증

## 💻 소프트웨어 구성요소

### controller_main.py
```python
# 비동기 아키텍처가 있는 메인 애플리케이션
class ControllerSystem:
    - 게임패드 입력 처리 (50Hz)
    - 네트워크 통신 (20Hz)
    - BMW 기어 통합
    - 오류 처리 및 복구
    - 실시간 로깅 및 상태
```

**주요 기능:**
- **Async/Await 아키텍처**: 논블로킹 동시 작업
- **연결 관리**: 지수 백오프를 통한 자동 재연결
- **입력 검증**: 포괄적인 게임패드 및 기어 레버 검증
- **성능 모니터링**: 실시간 메트릭 및 상태 보고

### bmw_lever_controller.py
```python
# BMW 기어 레버 CAN 버스 인터페이스
class BMWLeverController:
    - CAN 메시지 인코딩/디코딩
    - CRC-8 검증 (BMW 0x1D 다항식)
    - 위치 피드백이 있는 LED 제어
    - 기어 상태 관리
    - 메시지 라우팅 및 필터링
```

**기술적 세부사항:**
- **CAN 프레임 형식**: BMW 전용 구조의 8바이트 데이터 프레임
- **위치 매핑**: 센터 리턴 로직이 있는 7개의 구별되는 레버 위치
- **CRC 계산**: 0x1D 다항식과 0x70/0x53 XOR을 사용하는 사용자 정의 BMW CRC-8
- **LED 제어**: 백라이트 제어가 있는 실시간 기어 위치 표시

### data_models.py
```python
# 데이터 구조 및 직렬화
@dataclass
class ControlData:
    - JSON 직렬화/역직렬화
    - 타입 검증 및 제약
    - 타임스탬프 관리
    - 네트워크 프로토콜 형식화
```

**데이터 구조:**
```json
{
    "throttle": 0.0,      // Float [-1.0, 1.0]
    "steering": 0.0,      // Float [-1.0, 1.0]
    "gear": "N",          // String ["P", "R", "N", "D", "M1"-"M8"]
    "manual_gear": 1,     // Integer [1-8] 수동 모드용
    "timestamp": 1234567890.123
}
```

### logger.py
```python
# 전문 로깅 시스템
class Logger:
    - 다중 레벨 로깅 (DEBUG, INFO, WARN, ERROR)
    - 파일 및 콘솔 출력
    - 로그 파일 회전
    - 성능 메트릭
    - 오류 추적 및 보고
```

## 🚀 설치 및 구성

### 하드웨어 설정
1. **ShanWan 게임패드 수신기 연결**:
   ```bash
   # 게임패드 감지 확인
   ls /dev/input/js*
   # 다음이 표시되어야 함: /dev/input/js0
   
   # 게임패드 입력 테스트
   jstest /dev/input/js0
   ```

2. **CAN 인터페이스 설정**:
   ```bash
   # /boot/config.txt에 추가
   echo 'dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25' | sudo tee -a /boot/config.txt
   echo 'dtoverlay=spi-bcm2835-overlay' | sudo tee -a /boot/config.txt
   
   # 재부팅 및 CAN 구성
   sudo reboot
   sudo ip link set can0 up type can bitrate 500000
   ```

3. **BMW 기어 레버 배선**:
   ```
   MCP2515 -> 라즈베리파이 4B
   VCC     -> 3.3V (핀 1)
   GND     -> GND (핀 6)
   CS      -> CE0 (핀 24)
   SO      -> MISO (핀 21)
   SI      -> MOSI (핀 19)
   SCK     -> SCLK (핀 23)
   INT     -> GPIO25 (핀 22)
   ```

### 소프트웨어 설치
```bash
# 컨트롤러 디렉토리로 이동
cd /home/pi/Hannover_Makers_Fair_Team4/controller_rpi

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 시작 스크립트 실행 권한 부여
chmod +x run_controller.sh
```

### 의존성 (requirements.txt)
```
asyncio>=3.4.3
python-can>=4.2.2
pygame>=2.5.2
pyyaml>=6.0.1
crccheck>=1.3.0
dataclasses>=0.6
typing_extensions>=4.7.1
```

## 🔄 작동 모드

### 표준 작동
```bash
# 컨트롤러 시스템 시작
sudo ./run_controller.sh

# 디버깅을 위한 수동 시작
python3 controller_main.py
```

### 디버그 모드
```bash
# 상세 로깅 활성화
export LOG_LEVEL=DEBUG
python3 controller_main.py

# CAN 트래픽 모니터링
candump can0

# 게임패드만 테스트
python3 -c "
import pygame
pygame.init()
js = pygame.joystick.Joystick(0)
js.init()
print(f'게임패드: {js.get_name()}')
"
```

## 📊 성능 사양

### 실시간 성능
- **제어 루프**: 20Hz (50ms 주기) 명령 전송
- **게임패드 샘플링**: 50Hz (20ms 주기) 입력 처리
- **네트워크 지연시간**: 차량 파이까지 일반적으로 10ms 미만
- **CAN 버스 지연시간**: 기어 레버 업데이트 5ms 미만

### 리소스 사용률
- **CPU 사용량**: Pi 4B에서 평균 15-25%
- **메모리 사용량**: 일반적으로 ~200MB
- **네트워크 대역폭**: 제어 데이터 ~100KB/s
- **CAN 버스 로드**: 500kbps에서 5% 미만 사용률

## 🛡️ 안전 및 오류 처리

### 연결 안전
```python
# 자동 재연결 로직
class ConnectionManager:
    - 지수 백오프 재시도 (1s → 최대 30s)
    - 연결 상태 모니터링
    - 실패 시 우아한 성능 저하
    - 중대한 오류 시 비상 정지
```

### 입력 검증
```python
# 포괄적인 입력 살균
def validate_input(self, gamepad_input):
    - 아날로그 입력에 대한 범위 확인 [-1.0, 1.0]
    - 300ms 타임아웃의 버튼 디바운싱
    - 기어 전환 검증
    - 타임스탬프 일관성 검사
```

### CAN 버스 오류 처리
```python
# 견고한 CAN 통신
def handle_can_errors(self):
    - 버스 오류 감지 및 복구
    - 메시지 타임아웃 처리 (1s)
    - CRC 검증 실패
    - 인터페이스 재설정 및 재시작
```

## 🔧 고급 구성

### 성능 튜닝
```python
# controller_main.py의 구성 매개변수
CONTROL_FREQUENCY = 20          # Hz - 명령 전송 속도
GAMEPAD_FREQUENCY = 50          # Hz - 입력 샘플링 속도
NETWORK_TIMEOUT = 1.0           # 초 - 소켓 타임아웃
GEAR_CHANGE_COOLDOWN = 0.3      # 초 - 빠른 전환 방지
MAX_RECONNECT_ATTEMPTS = 5      # 연장된 지연 전 시도 횟수
```

### CAN 버스 구성
```python
# BMW 기어 레버 전용 설정
CAN_BITRATE = 500000           # 500kbps 표준
CAN_INTERFACE = 'can0'         # Linux CAN 인터페이스 이름
BMW_GEAR_MESSAGE_ID = 0x197    # 기어 위치 메시지
BMW_LED_MESSAGE_ID = 0x1F6     # LED 제어 메시지
BMW_BACKLIGHT_ID = 0x3FD       # 백라이트 제어 메시지
```

### 네트워크 구성
```python
# TCP 소켓 설정
VEHICLE_IP = "192.168.86.59"   # 대상 차량 파이 IP
VEHICLE_PORT = 8888            # 제어 데이터 포트
SOCKET_TIMEOUT = 10.0          # 연결 타임아웃
KEEPALIVE_ENABLED = True       # TCP keepalive
```

## 🐛 문제 해결 가이드

### 일반적인 문제

#### 게임패드 감지 안됨
```bash
# USB 수신기 연결 확인
lsusb | grep -i controller

# 입력 장치 확인
ls -la /dev/input/js*

# 권한 확인
sudo chmod 666 /dev/input/js0

# 필요한 경우 추가 드라이버 설치
sudo apt install joystick jstest-gtk
```

#### CAN 인터페이스 문제
```bash
# 커널 모듈 확인
lsmod | grep mcp251x

# 장치 트리 오버레이 확인
ls /proc/device-tree/soc/spi*/spidev*/

# CAN 인터페이스 테스트
candump can0 -n 10

# 인터페이스 재설정
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 500000
```

#### 네트워크 연결
```bash
# 차량 파이 연결 테스트
ping 192.168.86.59

# 포트 접근성 확인
telnet 192.168.86.59 8888

# 네트워크 트래픽 모니터링
sudo tcpdump -i wlan0 port 8888

# DNS 해석 테스트
nslookup 192.168.86.59
```

#### BMW 기어 레버 문제
```bash
# CAN 트래픽 모니터링
candump can0 | grep 197

# 테스트 메시지 전송
cansend can0 197#0E00000000000000

# CRC 계산 확인
python3 -c "
import crccheck
crc = crccheck.crc.Crc8Base()
crc._poly = 0x1D
crc._xor_output = 0x53
print(f'CRC: {crc.calc([0x0E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]):02X}')
"
```

### 성능 최적화

#### 지연시간 감소
```bash
# 실시간 스케줄링 설정
sudo chrt -f 50 python3 controller_main.py

# 네트워크 스택 최적화
echo 'net.core.rmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' | sudo tee -a /etc/sysctl.conf

# 성능 가버너 사용
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### 메모리 최적화
```bash
# 메모리 사용량 모니터링
ps aux | grep python3

# 가상 메모리 확인
cat /proc/meminfo | grep -E 'MemTotal|MemFree|MemAvailable'

# Python 가비지 컬렉션 최적화
export PYTHONMALLOC=malloc
export PYTHONHASHSEED=0
```

## 📈 모니터링 및 진단

### 실시간 모니터링
```bash
# 시스템 리소스 사용량
htop -p $(pgrep -f controller_main.py)

# 네트워크 연결 상태
ss -tuln | grep 8888

# CAN 버스 통계
ip -s link show can0

# 로그 파일 모니터링
tail -f controller.log
```

### 성능 메트릭
```python
# 내장 성능 추적
class PerformanceMonitor:
    - 루프 타이밍 측정
    - 네트워크 지연시간 추적
    - 오류율 통계
    - 메모리 사용량 모니터링
    - CAN 버스 상태 메트릭
```

## 🔮 향후 개선사항

### 계획된 기능
- [ ] **다중 게임패드 지원**: 다양한 컨트롤러 타입 지원
- [ ] **무선 텔레메트리**: 실시간 성능 데이터 전송
- [ ] **음성 명령**: 음성 인식과의 통합
- [ ] **모바일 앱 인터페이스**: 스마트폰 제어 애플리케이션
- [ ] **머신러닝**: 예측적 입력 평활화

### 기술적 개선사항
- [ ] **하드웨어 가속**: GPU 가속 입력 처리
- [ ] **실시간 OS**: 실시간 Linux 커널로 마이그레이션
- [ ] **중복 통신**: 다중 네트워크 인터페이스
- [ ] **고급 진단**: 포괄적인 시스템 상태 모니터링

---

*영어 문서는 [README.md](README.md)를 참조하세요*  
*차량 파이 문서는 [../vehicle_rpi/README.md](../vehicle_rpi/README.md)를 참조하세요*