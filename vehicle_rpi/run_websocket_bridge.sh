#!/bin/bash
# WebSocket Bridge 수동 실행 스크립트
# UDP 스트림을 WebSocket으로 브릿지

echo "🌉 WebSocket Bridge 수동 실행"
echo "=" * 40

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if websockets library is installed
print_status "websockets 라이브러리 확인 중..."
if ! python3 -c "import websockets" 2>/dev/null; then
    print_error "websockets 라이브러리가 설치되지 않았습니다"
    print_status "설치 중..."
    
    if python3 -m pip install --user --break-system-packages websockets; then
        print_status "✅ websockets 라이브러리 설치 완료"
    else
        print_error "❌ websockets 라이브러리 설치 실패"
        print_error "수동으로 설치해주세요: pip install websockets"
        exit 1
    fi
else
    print_status "✅ websockets 라이브러리 확인됨"
fi

# Check for UDP server
UDP_PORT=${1:-9999}
WEBSOCKET_PORT=${2:-8765}

print_status "설정:"
print_status "  • UDP 소스 포트: $UDP_PORT"
print_status "  • WebSocket 서버 포트: $WEBSOCKET_PORT"

# Check if UDP server is running
print_status "UDP 서버 상태 확인 중..."
if netstat -ln 2>/dev/null | grep -q ":$UDP_PORT " || ss -ln 2>/dev/null | grep -q ":$UDP_PORT "; then
    print_status "✅ UDP 서버가 포트 $UDP_PORT에서 실행 중"
else
    print_warning "⚠️ UDP 서버가 포트 $UDP_PORT에서 실행되지 않는 것 같습니다"
    print_warning "먼저 vehicle_main.py --udp-streaming을 실행하세요"
    
    read -p "계속 진행하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "브릿지 실행을 취소합니다"
        exit 0
    fi
fi

# Check if WebSocket port is free
if netstat -ln 2>/dev/null | grep -q ":$WEBSOCKET_PORT " || ss -ln 2>/dev/null | grep -q ":$WEBSOCKET_PORT "; then
    print_error "❌ 포트 $WEBSOCKET_PORT가 이미 사용 중입니다"
    print_error "다른 포트를 사용하거나 실행 중인 프로세스를 종료하세요"
    exit 1
fi

# Function to handle cleanup
cleanup() {
    print_status "브릿지 종료 중..."
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGINT SIGTERM

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Show connection info
print_status "🌐 연결 정보:"
print_status "  • WebSocket 브릿지: ws://$LOCAL_IP:$WEBSOCKET_PORT"
print_status "  • 브라우저에서 접속: http://$LOCAL_IP:8082"
print_status "  • UDP 소스: localhost:$UDP_PORT"
print_status ""
print_status "🚀 WebSocket 브릿지 시작 중..."
print_status "Ctrl+C로 종료할 수 있습니다"
echo "=" * 40

# Set PYTHONPATH to include user packages 
export PYTHONPATH="/home/pi/.local/lib/python3.11/site-packages:/usr/lib/python3/dist-packages:$PYTHONPATH"
# Don't exclude user site packages for websockets
unset PYTHONNOUSERSITE

# Start the bridge
if [ -f "udp_websocket_bridge.py" ]; then
    /usr/bin/python3 udp_websocket_bridge.py \
        --udp-host localhost \
        --udp-port "$UDP_PORT" \
        --websocket-port "$WEBSOCKET_PORT"
else
    print_error "❌ udp_websocket_bridge.py 파일을 찾을 수 없습니다"
    exit 1
fi

# Cleanup on exit
cleanup