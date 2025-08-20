#!/bin/bash
# 간단한 WebSocket 브릿지 실행

echo "🚀 WebSocket 브릿지 간단 실행"

# UDP 서버 확인
if netstat -ln 2>/dev/null | grep -q ":9999 "; then
    echo "✅ UDP 서버 실행 중"
else
    echo "⚠️ UDP 서버가 실행되지 않았습니다"
    echo "먼저 다른 터미널에서 실행하세요: sudo ./run_vehicle.sh"
fi

# WebSocket 브릿지 시작
echo "🌐 WebSocket 브릿지 시작: ws://192.168.86.59:8765"
echo "📡 브라우저 접속: http://192.168.86.59:8082"
echo "Ctrl+C로 종료"
echo ""

python3 udp_websocket_bridge.py --udp-host localhost --udp-port 9999 --websocket-port 8765