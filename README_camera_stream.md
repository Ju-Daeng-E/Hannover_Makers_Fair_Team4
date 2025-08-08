# 🎥 Raspberry Pi Camera Web Streaming

라즈베리파이 카메라를 웹 브라우저에서 실시간으로 볼 수 있는 스트리밍 서버입니다.

## 📋 필요 사항

### 하드웨어
- Raspberry Pi (3B+ 이상 권장)
- Raspberry Pi Camera Module 또는 USB 웹캠
- 네트워크 연결 (WiFi 또는 이더넷)

### 소프트웨어
- Python 3.7+
- OpenCV
- Flask

## 🚀 빠른 시작

### 1. 카메라 활성화
```bash
sudo raspi-config
# Interface Options → Camera → Enable 선택
sudo reboot
```

### 2. 의존성 설치 및 실행
```bash
# 실행 권한 부여 (최초 1회)
chmod +x run_camera_stream.sh

# 스트리밍 서버 시작
./run_camera_stream.sh
```

### 3. 브라우저에서 접속
- 로컬: http://localhost:5000
- 네트워크: http://[라즈베리파이IP]:5000

## 📁 파일 구조

```
📦 camera_stream/
├── 📜 camera_stream.py         # 메인 스트리밍 서버
├── 📜 requirements.txt         # Python 의존성
├── 📜 run_camera_stream.sh     # 실행 스크립트
└── 📜 README_camera_stream.md  # 사용 설명서
```

## ⚙️ 설정 옵션

### 해상도 및 프레임레이트 변경
`camera_stream.py`에서 다음 값을 수정:
```python
camera = CameraStream(resolution=(640, 480), framerate=30)
```

### 포트 변경
```python
app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
```

## 🔧 문제 해결

### 카메라가 인식되지 않는 경우
```bash
# 카메라 장치 확인
ls /dev/video*

# 카메라 모듈 확인
vcgencmd get_camera

# 카메라 테스트
raspistill -o test.jpg
```

### 네트워크 접속 문제
```bash
# 방화벽 포트 열기
sudo ufw allow 5000/tcp

# IP 주소 확인
hostname -I
```

### 의존성 설치 문제
```bash
# 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# OpenCV 의존성 설치
sudo apt install python3-opencv python3-pip -y

# 수동 설치
pip3 install flask opencv-python numpy
```

## 🌐 네트워크 스트리밍

### 외부 네트워크에서 접속하려면:
1. 공유기에서 포트 포워딩 설정 (5000번 포트)
2. 공용 IP 주소 확인
3. 보안을 위해 인증 기능 추가 권장

## 📊 성능 최적화

### CPU 사용량 줄이기
- 해상도 낮추기: (320, 240)
- 프레임레이트 줄이기: 15fps
- JPEG 품질 조정: [cv2.IMWRITE_JPEG_QUALITY, 70]

### 메모리 사용량 최적화
- 버퍼 크기 제한
- 불필요한 프레임 복사 방지

## 🔒 보안 고려사항

- 기본적으로 인증 없이 접근 가능
- 프로덕션 환경에서는 HTTPS 및 인증 기능 추가 권장
- 방화벽 설정으로 접근 제한

## 📱 모바일 최적화

- 반응형 웹 디자인 적용
- 터치 스크린 최적화
- 저대역폭 모드 지원

## 🎮 확장 기능 아이디어

- 팬/틸트 컨트롤
- 움직임 감지
- 녹화 기능
- 다중 카메라 지원
- WebRTC를 이용한 저지연 스트리밍

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. 카메라 연결 상태
2. 네트워크 연결 상태  
3. Python 의존성 설치 상태
4. 방화벽 설정