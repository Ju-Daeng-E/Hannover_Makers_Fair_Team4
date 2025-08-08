#!/bin/bash

# Raspberry Pi Camera Web Streaming 실행 스크립트

echo "🎥 Raspberry Pi Camera Web Streaming 서버 시작 스크립트"
echo "================================================================"

# Python 버전 확인
echo "Python 버전 확인 중..."
python3 --version

# 시스템 패키지 설치 (관리자 권한 필요)
echo ""
echo "📦 시스템 패키지 확인 및 설치..."
echo "필요한 패키지들을 시스템에 설치합니다 (sudo 권한 필요):"

# 필수 시스템 패키지 설치
sudo apt update
sudo apt install -y python3-opencv python3-flask python3-pip python3-full

# 가상환경 생성 및 활성화
if [ ! -d "venv" ]; then
    echo ""
    echo "🔧 가상환경 생성 중..."
    python3 -m venv venv --system-site-packages
    echo "✅ 가상환경 생성 완료"
fi

echo ""
echo "🔄 가상환경 활성화..."
source venv/bin/activate

# 가상환경에서 추가 패키지 설치
echo ""
echo "📦 추가 Python 패키지 설치..."
venv/bin/pip install flask opencv-python numpy --break-system-packages 2>/dev/null || {
    echo "시스템 패키지를 사용합니다..."
}

# 카메라 상태 확인
echo ""
echo "📷 카메라 상태 확인..."

# 라즈베리파이 카메라 상태 확인
echo "   라즈베리파이 카메라 상태:"
vcgencmd get_camera

# 비디오 장치 확인
echo ""
echo "   사용 가능한 비디오 장치:"
ls /dev/video* 2>/dev/null | head -5 | while read device; do
    echo "      - $device"
done

# 카메라 활성화 안내
echo ""
echo "📋 카메라가 인식되지 않는 경우 다음을 실행하세요:"
echo "   1. sudo raspi-config"
echo "   2. Interface Options → Camera → Enable 선택"
echo "   3. sudo reboot"
echo ""
echo "또는 다음 명령어로 카메라 활성화:"
echo "   echo 'start_x=1' | sudo tee -a /boot/config.txt"
echo "   echo 'gpu_mem=128' | sudo tee -a /boot/config.txt"
echo "   sudo reboot"

# 방화벽 설정 안내
echo ""
echo "🔥 방화벽 설정 (필요시 실행):"
echo "   sudo ufw allow 5000/tcp"

echo ""
echo "🌐 접속 정보:"
echo "   로컬: http://localhost:5000"
echo "   네트워크: http://$(hostname -I | cut -d' ' -f1):5000"

echo ""
echo "🚀 카메라 스트리밍 서버 시작..."
echo "종료하려면 Ctrl+C를 누르세요"
echo "================================================================"
echo ""

# Python 스크립트 실행 (가상환경 사용)
venv/bin/python camera_stream.py