# 🏁 하노버 메이커스 페어 팀 4 - 고급 RC카 제어 시스템

BMW 기어 레버 통합, 실시간 카메라 스트리밍, 전문급 제어 인터페이스를 갖춘 정교한 듀얼 라즈베리파이 RC카 시스템입니다.

## 🎯 프로젝트 개요

이 프로젝트는 TCP 소켓으로 통신하는 두 개의 라즈베리파이를 사용한 최첨단 RC카 제어 시스템을 구현합니다. BMW F-시리즈 기어 레버 통합, 실시간 카메라 스트리밍, 게임패드 제어, 전문 대시보드 인터페이스를 특징으로 합니다.

### 주요 기능
- **듀얼 파이 아키텍처**: 향상된 신뢰성을 위한 별도의 컨트롤러 및 차량 시스템
- **BMW 기어 통합**: CAN 버스 통신을 통한 정품 BMW F-시리즈 기어 레버
- **실시간 제어**: 50ms 이하 지연시간의 20Hz 제어 루프
- **카메라 스트리밍**: 웹 인터페이스를 통한 라이브 비디오 피드
- **전문 대시보드**: 실시간 텔레메트리 및 상태 모니터링
- **안전 시스템**: 포괄적인 타임아웃 보호 및 비상 정지 기능

## 🏗️ 시스템 아키텍처

### 컨트롤러 라즈베리파이
- **주요 기능**: 입력 처리 및 명령 전송
- **하드웨어 인터페이스**: ShanWan 게임패드 + CAN 버스를 통한 BMW 기어 레버
- **통신**: TCP 소켓 클라이언트 (20Hz 전송 속도)
- **안전**: 연결 모니터링 및 자동 재연결

### 차량 라즈베리파이
- **주요 기능**: 차량 제어 및 센서 관리
- **하드웨어 인터페이스**: 서보/ESC 제어가 가능한 PiRacer 섀시
- **통신**: TCP 소켓 서버 + HTTP 카메라 스트리밍
- **안전**: 명령 타임아웃 보호 및 비상 정지

## 📁 프로젝트 구조

```
Hannover_Makers_Fair_Team4/
├── controller_rpi/              # 컨트롤러 파이 코드베이스
│   ├── controller_main.py       # 비동기 아키텍처의 메인 제어 루프
│   ├── bmw_lever_controller.py  # BMW 기어 레버 CAN 버스 인터페이스
│   ├── data_models.py           # 데이터 구조 및 직렬화
│   ├── logger.py                # 전문 로깅 시스템
│   ├── run_controller.sh        # 프로덕션 시작 스크립트
│   └── requirements.txt         # Python 의존성
│
├── vehicle_rpi/                 # 차량 파이 코드베이스
│   ├── vehicle_main.py          # 메인 차량 제어 시스템
│   ├── camera_stream.py         # HTTP 카메라 스트리밍 서버
│   ├── udp_websocket_bridge.py  # 텔레메트리용 WebSocket 브리지
│   ├── speed_sensor.py          # 차량 속도 모니터링
│   ├── dashboard/               # 웹 대시보드 인터페이스
│   ├── run_vehicle.sh           # 프로덕션 시작 스크립트
│   └── requirements.txt         # Python 의존성
│
├── README.md                    # 영어 버전
├── README-KR.md                 # 이 파일 (한국어)
└── .gitignore                   # Git 무시 패턴
```

## 🔧 하드웨어 요구사항

### 컨트롤러 파이 설정
- **SBC**: 라즈베리파이 4B (4GB+ 권장)
- **컨트롤러**: ShanWan 무선 게임패드
- **CAN 인터페이스**: MCP2515 CAN 트랜시버 모듈
- **기어 레버**: BMW F-시리즈 기어 레버 어셈블리
- **저장소**: MicroSD 카드 (32GB+ Class 10)
- **전원**: 5V 3A USB-C 전원 공급장치

### 차량 파이 설정
- **SBC**: 라즈베리파이 4B (4GB+ 권장)
- **섀시**: PiRacer 표준 섀시
- **카메라**: 라즈베리파이 카메라 모듈 v2 또는 USB 카메라
- **모터**: 표준 서보 + 브러시 ESC 설정
- **저장소**: MicroSD 카드 (32GB+ Class 10)
- **전원**: 듀얼 전원 공급장치 (파이: 5V 3A, 모터: 7.4V LiPo)

### 네트워크 인프라
- **연결성**: 802.11ac WiFi (5GHz 권장)
- **토폴로지**: 동일한 서브넷상의 두 장치
- **대역폭**: 최적의 카메라 스트리밍을 위한 최소 50Mbps

## ⚙️ 설치 및 설정

### 1. 환경 준비
```bash
# 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# 시스템 의존성 설치
sudo apt install -y python3-pip python3-venv git can-utils
```

### 2. 컨트롤러 파이 구성
```bash
cd /home/pi/Hannover_Makers_Fair_Team4/controller_rpi

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate

# Python 의존성 설치
pip install -r requirements.txt

# CAN 인터페이스 구성
echo 'dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25' | sudo tee -a /boot/config.txt
echo 'dtoverlay=spi-bcm2835-overlay' | sudo tee -a /boot/config.txt

# 시작 스크립트 실행 권한 부여
chmod +x run_controller.sh
```

### 3. 차량 파이 구성
```bash
cd /home/pi/Hannover_Makers_Fair_Team4/vehicle_rpi

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate

# Python 의존성 설치
pip install -r requirements.txt

# 카메라 인터페이스 활성화
sudo raspi-config
# Interface Options -> Camera -> Enable

# 시작 스크립트 실행 권한 부여
chmod +x run_vehicle.sh
```

### 4. 네트워크 구성
안정적인 통신을 위해 두 시스템의 네트워크 설정을 편집하세요:
```bash
# 안정적인 연결을 위한 고정 IP 설정
# 컨트롤러 파이: 192.168.86.50 (또는 자동 DHCP)
# 차량 파이: 192.168.86.59 (설정된 대로)
```

## 🚀 운영 가이드

### 시스템 시작 순서
1. **두 라즈베리파이 장치 전원 켜기**
2. **차량 파이 먼저 시작** (TCP 서버):
   ```bash
   cd /home/pi/Hannover_Makers_Fair_Team4/vehicle_rpi
   sudo ./run_vehicle.sh
   ```
3. **카메라 스트리밍 확인**: `http://192.168.86.59:8080`으로 이동
4. **컨트롤러 파이 시작** (TCP 클라이언트):
   ```bash
   cd /home/pi/Hannover_Makers_Fair_Team4/controller_rpi
   sudo ./run_controller.sh
   ```

### 제어 인터페이스

#### 게임패드 조작
- **왼쪽 아날로그 스틱 (X축)**: 조향 제어 (-1.0 ~ 1.0)
- **오른쪽 아날로그 스틱 (Y축)**: 스로틀 제어 (-1.0 ~ 1.0)
- **버튼 A**: 중립 기어
- **버튼 B**: 전진 기어
- **버튼 X**: 후진 기어
- **버튼 Y**: 주차 기어

#### BMW 기어 레버 (옵션)
- **P (주차)**: 차량 정지
- **R (후진)**: 40% 속도 제한의 후진 조작
- **N (중립)**: 스로틀 반응 없음
- **D (전진)**: 전속 전진 조작
- **M1-M8**: 점진적 속도 스케일링의 수동 기어 모드

## 📊 모니터링 및 진단

### 웹 인터페이스
- **카메라 스트림**: `http://[vehicle-ip]:8080/`
- **시스템 상태**: `http://[vehicle-ip]:8080/status`
- **실시간 대시보드**: 웹 브라우저를 통해 액세스 가능

### 로그 파일
- **컨트롤러 로그**: `controller_rpi/controller.log`
- **차량 로그**: `vehicle_rpi/logs/vehicle.log`
- **시스템 로그**: `/var/log/syslog`

### 성능 모니터링
- **제어 지연시간**: 일반적으로 50ms 이하
- **프레임 레이트**: 15-30 FPS 카메라 스트림
- **네트워크 사용률**: 비디오용 약 5-10 Mbps
- **CPU 사용량**: 평균 30-50% 로드

## 🛡️ 안전 및 보안 기능

### 자동 안전 시스템
- **연결 타임아웃**: 1초 동안 명령이 수신되지 않으면 차량 정지
- **비상 정지**: 통신 실패 시 즉시 정지
- **속도 제한**: 기어 기반 최대 속도 강제 적용
- **입력 검증**: 포괄적인 명령 살균

### 운영 안전
- **사전 점검**: 운영 전 자동화된 시스템 검증
- **상태 모니터링**: 실시간 시스템 상태 지표
- **정상 종료**: 종료 시 적절한 리소스 정리

## 🔧 고급 구성

### 성능 튜닝
```python
# 컨트롤러 파이 최적화
CONTROL_FREQUENCY = 20  # Hz
NETWORK_TIMEOUT = 1.0   # 초
RETRY_ATTEMPTS = 3

# 차량 파이 최적화
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAMERATE = 30
JPEG_QUALITY = 80
```

### 사용자 정의 통합
시스템은 모듈식 설계를 통해 추가 센서 및 액추에이터를 지원합니다:
- 추가 카메라
- 텔레메트리 센서
- 사용자 정의 제어 인터페이스
- 외부 데이터 로깅

## 🐛 문제 해결

### 일반적인 문제

#### 네트워크 연결
```bash
# 기본 연결 테스트
ping [target-ip]

# 포트 가용성 확인
telnet [target-ip] 8888

# 네트워크 트래픽 모니터링
tcpdump -i wlan0 port 8888
```

#### CAN 버스 문제
```bash
# CAN 인터페이스 상태 확인
ip link show can0

# CAN 트래픽 모니터링
candump can0

# CAN 인터페이스 재설정
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 500000
```

#### 카메라 문제
```bash
# 사용 가능한 카메라 목록
ls /dev/video*

# 카메라 기능 테스트
raspistill -o test.jpg

# 카메라 인터페이스 확인
vcgencmd get_camera
```

### 성능 최적화
- 지연시간 감소를 위해 5GHz WiFi 사용
- 장치 간 네트워크 홉 최소화
- 대역폭에 맞춰 카메라 해상도 조정
- 부하 상황에서 시스템 온도 모니터링

## 📈 기술 사양

### 통신 프로토콜
- **전송**: 신뢰성을 위한 TCP 소켓
- **데이터 형식**: 사람이 읽을 수 있는 디버깅을 위한 JSON
- **업데이트 속도**: 반응성 있는 제어를 위한 20Hz
- **지연시간**: 일반적으로 50ms 이하의 종단 간

### 제어 시스템
- **아키텍처**: 이벤트 기반 비동기 처리
- **스레딩**: 동시 작업을 위한 멀티스레드
- **오류 처리**: 포괄적인 예외 관리
- **로깅**: 전문급 시스템 로깅

### 성능 지표
- **CPU 사용량**: 파이당 평균 30-50% 로드
- **메모리 사용량**: 일반적으로 1GB 이하
- **네트워크 대역폭**: 비디오 스트리밍용 5-10 Mbps
- **전력 소비**: 총 시스템 약 15W

## 🤝 기여

이 프로젝트는 하노버 메이커스 페어 팀 4 경쟁 출품작의 일부입니다. 코드베이스는 고급 임베디드 시스템 프로그래밍, 실시간 제어 및 전문 소프트웨어 엔지니어링 관행을 보여줍니다.

### 개발 지침
- PEP 8 Python 코딩 표준 준수
- 포괄적인 오류 처리 구현
- 디버깅 및 모니터링을 위한 로깅 추가
- 실제 하드웨어에서 철저한 테스트
- 모든 구성 변경사항 문서화

## 📝 라이선스 및 크레딧

교육 및 경쟁 목적을 위해 하노버 메이커스 페어 팀 4가 개발했습니다.

**핵심 기술:**
- Python 3.11+ async/await 프로그래밍
- TCP 소켓 프로그래밍
- CAN 버스 통신 프로토콜
- 컴퓨터 비전 및 스트리밍
- 실시간 임베디드 제어 시스템

---

*영어 문서는 [README.md](README.md)를 참조하세요*