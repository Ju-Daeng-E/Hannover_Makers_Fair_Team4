#!/bin/bash

# Raspberry Pi libcamera Web Streaming 실행 스크립트

echo "🎥 Raspberry Pi libcamera Web Streaming 서버 시작 스크립트"
echo "================================================================"

# Python 버전 확인
echo "Python 버전 확인 중..."
python3 --version

# libcamera 설치 확인
echo ""
echo "📦 libcamera 패키지 확인..."
if ! command -v libcamera-hello &> /dev/null; then
    echo "libcamera 패키지가 설치되지 않았습니다. 설치 중..."
    sudo apt update
    sudo apt install -y libcamera-apps libcamera-tools
else
    echo "✅ libcamera 패키지가 이미 설치되어 있습니다"
fi

# 시스템 패키지 설치
echo ""
echo "📦 필요한 시스템 패키지 확인 및 설치..."
sudo apt install -y python3-flask python3-pip

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

# 가상환경에서 Flask 설치
echo ""
echo "📦 Flask 패키지 설치..."
venv/bin/pip install flask --break-system-packages 2>/dev/null || {
    echo "시스템 패키지를 사용합니다..."
}

# 카메라 상태 확인
echo ""
echo "📷 카메라 상태 확인..."

# libcamera 카메라 목록
echo "   사용 가능한 카메라:"
libcamera-hello --list-cameras 2>/dev/null || echo "   카메라를 찾을 수 없습니다"

# 포트 8888 사용 중인 프로세스 종료 (이전 실행이 남아있을 경우)
echo ""
echo "🔧 포트 정리 중..."
sudo pkill -f libcamera-vid 2>/dev/null || true
sudo fuser -k 8888/tcp 2>/dev/null || true

# 방화벽 설정 안내
echo ""
echo "🔥 방화벽 설정 (필요시 실행):"
echo "   sudo ufw allow 5000/tcp"
echo "   sudo ufw allow 8888/tcp"

echo ""
echo "🌐 접속 정보:"
echo "   로컬: http://localhost:5000"
echo "   네트워크: http://$(hostname -I | cut -d' ' -f1):5000"

echo ""
echo "🚀 libcamera 카메라 스트리밍 서버 시작..."
echo "종료하려면 Ctrl+C를 누르세요"
echo "================================================================"
echo ""

# Python 스크립트 실행 (가상환경 사용)
venv/bin/python camera_stream_libcamera.py