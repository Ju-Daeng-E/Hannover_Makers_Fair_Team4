#!/bin/bash
# Quick WebSocket Bridge Test Script

echo "🧪 WebSocket 브릿지 빠른 테스트"
echo "=" * 40

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. 파일 존재 확인
if [ -f "udp_websocket_bridge.py" ]; then
    print_status "✅ udp_websocket_bridge.py 파일 확인됨"
else
    print_error "❌ udp_websocket_bridge.py 파일이 없습니다"
    exit 1
fi

# 2. websockets 라이브러리 확인
if python3 -c "import websockets; print('websockets version:', websockets.__version__)" 2>/dev/null; then
    print_status "✅ websockets 라이브러리 설치됨"
else
    print_error "❌ websockets 라이브러리 설치 필요"
    print_status "설치 중..."
    pip install --user websockets
fi

# 3. UDP 포트 확인 (9999)
if netstat -ln 2>/dev/null | grep -q ":9999 " || ss -ln 2>/dev/null | grep -q ":9999 "; then
    print_status "✅ UDP 포트 9999 사용 중 (차량 시스템 실행 중)"
else
    print_warning "⚠️ UDP 포트 9999가 사용되지 않음"
    print_warning "먼저 다른 터미널에서 실행하세요: sudo ./run_vehicle.sh"
fi

# 4. WebSocket 포트 확인 (8765)
if netstat -ln 2>/dev/null | grep -q ":8765 " || ss -ln 2>/dev/null | grep -q ":8765 "; then
    print_error "❌ WebSocket 포트 8765가 이미 사용 중입니다"
    print_error "실행 중인 프로세스를 종료하세요"
    exit 1
else
    print_status "✅ WebSocket 포트 8765 사용 가능"
fi

# 5. Python 모듈 import 테스트
print_status "Python 모듈 import 테스트 중..."
python3 -c "
import sys
import os
sys.path.insert(0, '.')

try:
    from udp_websocket_bridge import UDPWebSocketBridge
    print('✅ UDPWebSocketBridge import 성공')
    
    # 브릿지 객체 생성 테스트
    bridge = UDPWebSocketBridge(9999, 8765)
    print('✅ UDPWebSocketBridge 객체 생성 성공')
    
except ImportError as e:
    print(f'❌ Import 오류: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ 객체 생성 오류: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    print_status "✅ 모든 테스트 통과!"
    print_status "🚀 WebSocket 브릿지 시작..."
    
    # Set Python path
    export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
    export PYTHONNOUSERSITE=1
    
    # Start bridge
    /usr/bin/python3 udp_websocket_bridge.py --udp-host localhost --udp-port 9999 --websocket-port 8765
else
    print_error "❌ 테스트 실패 - 브릿지를 시작할 수 없습니다"
    exit 1
fi