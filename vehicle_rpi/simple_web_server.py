#!/usr/bin/env python3
"""
Simple Web Server for Testing
간단한 웹 서버 - 카메라가 없을 때 테스트용
"""

from flask import Flask, render_template_string
import argparse

app = Flask(__name__)

# 기본 HTML 템플릿
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RC Car Vehicle System</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        h1 {
            margin-bottom: 20px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        .status {
            font-size: 1.2em;
            margin: 20px 0;
            padding: 15px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        .ready {
            color: #4CAF50;
            font-weight: bold;
        }
        .info {
            margin-top: 30px;
            font-size: 1.1em;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 RC Car Vehicle System</h1>
        <div class="status ready">
            ✅ 차량 시스템 준비 완료
        </div>
        <div class="info">
            <p>📡 포트 {{ port }}에서 웹 인터페이스 실행 중</p>
            <p>🎮 컨트롤러 연결을 기다리는 중...</p>
            <p>📱 차량 제어는 컨트롤러 앱을 통해 수행됩니다</p>
        </div>
        <div class="status">
            <p>⚠️ 카메라 스트림 비활성화됨</p>
            <p>카메라를 연결하고 시스템을 재시작하세요</p>
        </div>
    </div>
    
    <script>
        // 5초마다 페이지 새로고침으로 상태 업데이트
        setInterval(() => {
            const timestamp = new Date().toLocaleTimeString('ko-KR');
            document.title = `RC Car Vehicle - ${timestamp}`;
        }, 5000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """메인 페이지"""
    import socket
    
    # 현재 실행 중인 포트 가져오기
    port = getattr(app, 'current_port', 8080)
    
    return render_template_string(HTML_TEMPLATE, port=port)

@app.route('/status')
def status():
    """상태 확인 API"""
    return {
        'status': 'ready',
        'camera': 'disabled',
        'controller': 'waiting',
        'port': getattr(app, 'current_port', 8080)
    }

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='Simple Web Server for RC Car')
    parser.add_argument('--port', type=int, default=8080, help='Port for web server (default: 8080)')
    args = parser.parse_args()
    
    port = args.port
    app.current_port = port
    
    print(f"🌐 Starting web server on port {port}")
    print(f"📱 Access: http://192.168.86.40:{port}")
    
    # Flask 서버 시작
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == '__main__':
    main()