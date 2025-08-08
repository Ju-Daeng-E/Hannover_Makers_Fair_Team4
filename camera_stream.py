#!/usr/bin/env python3
"""
Raspberry Pi Camera Web Streaming Server
Streams camera feed via Flask web server for real-time viewing
"""

import io
import logging
import socketserver
import threading
from threading import Condition
from flask import Flask, render_template_string, Response
import cv2
import time

# HTML template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Raspberry Pi Camera Stream</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            background-color: #f0f0f0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        #stream {
            max-width: 100%;
            height: auto;
            border: 2px solid #ddd;
            border-radius: 5px;
        }
        .controls {
            margin-top: 20px;
        }
        .info {
            margin-top: 20px;
            padding: 10px;
            background-color: #e7f3ff;
            border-radius: 5px;
            color: #0066cc;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 Raspberry Pi Camera Live Stream</h1>
        <div class="info">
            <p>실시간 카메라 스트리밍이 활성화되었습니다</p>
            <p>해상도: 640x480 | 프레임레이트: 30fps</p>
        </div>
        <img id="stream" src="{{ url_for('video_feed') }}" alt="Camera Stream">
        <div class="controls">
            <p>스트림 상태: <span id="status" style="color: green;">활성</span></p>
            <p>접속 URL: http://{{ host }}:{{ port }}</p>
        </div>
    </div>
    
    <script>
        // 스트림 상태 모니터링
        const img = document.getElementById('stream');
        const status = document.getElementById('status');
        
        img.onload = () => {
            status.textContent = '활성';
            status.style.color = 'green';
        };
        
        img.onerror = () => {
            status.textContent = '연결 끊김';
            status.style.color = 'red';
        };
        
        // 5초마다 연결 상태 확인
        setInterval(() => {
            const timestamp = new Date().getTime();
            img.src = img.src.split('?')[0] + '?t=' + timestamp;
        }, 5000);
    </script>
</body>
</html>
'''

class CameraStream:
    """카메라 스트리밍 클래스"""
    
    def __init__(self, resolution=(640, 480), framerate=30):
        self.resolution = resolution
        self.framerate = framerate
        self.cap = None
        self.frame = None
        self.condition = Condition()
        self.running = False
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def start_camera(self):
        """카메라 초기화 및 시작"""
        # 여러 카메라 인덱스 시도
        camera_indices = [0, 1, 10, 11, 12, 13, 14, 15, 16]
        
        for idx in camera_indices:
            try:
                self.logger.info(f"카메라 인덱스 {idx} 시도 중...")
                
                # OpenCV로 카메라 초기화
                self.cap = cv2.VideoCapture(idx)
                
                # 카메라 설정
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                self.cap.set(cv2.CAP_PROP_FPS, self.framerate)
                
                # 카메라가 제대로 열렸는지 확인
                if not self.cap.isOpened():
                    self.logger.warning(f"카메라 인덱스 {idx}를 열 수 없음")
                    continue
                
                # 테스트 프레임 읽기
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    self.logger.warning(f"카메라 인덱스 {idx}에서 프레임을 읽을 수 없음")
                    self.cap.release()
                    continue
                
                # 성공한 경우
                self.running = True
                self.logger.info(f"✅ 카메라 시작 성공 - 인덱스: {idx}, 해상도: {self.resolution}, FPS: {self.framerate}")
                
                # 카메라 스레드 시작
                self.thread = threading.Thread(target=self._capture_frames)
                self.thread.daemon = True
                self.thread.start()
                
                return True
                
            except Exception as e:
                self.logger.warning(f"카메라 인덱스 {idx} 시도 중 오류: {e}")
                if self.cap:
                    self.cap.release()
                continue
        
        self.logger.error("❌ 사용 가능한 카메라를 찾을 수 없습니다")
        self.logger.error("다음을 확인하세요:")
        self.logger.error("1. 카메라가 올바르게 연결되어 있는지")
        self.logger.error("2. sudo raspi-config에서 카메라가 활성화되어 있는지") 
        self.logger.error("3. 시스템을 재부팅했는지")
        return False
    
    def _capture_frames(self):
        """프레임 캡처 스레드"""
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    # 프레임 품질 향상
                    frame = cv2.flip(frame, 1)  # 좌우 반전
                    
                    with self.condition:
                        self.frame = frame.copy()
                        self.condition.notify_all()
                        
                time.sleep(1.0 / self.framerate)  # FPS 제어
                
            except Exception as e:
                self.logger.error(f"프레임 캡처 오류: {e}")
                break
    
    def get_frame(self):
        """현재 프레임 반환"""
        with self.condition:
            self.condition.wait()
            return self.frame.copy() if self.frame is not None else None
    
    def stop_camera(self):
        """카메라 정지"""
        self.running = False
        if self.cap:
            self.cap.release()
        self.logger.info("카메라 정지됨")

# Flask 앱 초기화
app = Flask(__name__)
camera = CameraStream()

@app.route('/')
def index():
    """메인 페이지"""
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    # 현재 실행 중인 포트 가져오기 (Flask가 아직 실행되지 않았을 수 있으므로 전역 변수 사용)
    port = getattr(app, 'current_port', 5000)
    
    return render_template_string(HTML_TEMPLATE, 
                                host=local_ip, 
                                port=port)

def generate_frames():
    """비디오 프레임 생성기"""
    while True:
        try:
            frame = camera.get_frame()
            if frame is not None:
                # JPEG로 인코딩
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_bytes = buffer.tobytes()
                
                # 멀티파트 응답 형식
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            logging.error(f"프레임 생성 오류: {e}")
            break

@app.route('/video_feed')
def video_feed():
    """비디오 스트림 엔드포인트"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    """서버 상태 확인"""
    return {
        'status': 'running' if camera.running else 'stopped',
        'resolution': camera.resolution,
        'framerate': camera.framerate
    }

def main():
    """메인 함수"""
    import argparse
    
    # 커맨드라인 인자 파싱
    parser = argparse.ArgumentParser(description='Raspberry Pi Camera Web Streaming Server')
    parser.add_argument('--port', type=int, default=5000, help='Port for web server (default: 5000)')
    args = parser.parse_args()
    
    port = args.port
    
    try:
        print("🎥 Raspberry Pi Camera Web Streaming Server 시작...")
        print("=" * 50)
        
        # 카메라 시작
        if not camera.start_camera():
            print("❌ 카메라 초기화 실패")
            return
            
        print("✅ 카메라 초기화 완료")
        
        # 네트워크 정보 출력
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        print(f"🌐 서버 정보:")
        print(f"   - 로컬 주소: http://localhost:{port}")
        print(f"   - 네트워크 주소: http://{local_ip}:{port}")
        print(f"   - 호스트명: {hostname}")
        print(f"📷 카메라 설정:")
        print(f"   - 해상도: {camera.resolution}")
        print(f"   - 프레임레이트: {camera.framerate}fps")
        print("=" * 50)
        print("웹 브라우저에서 위 주소로 접속하여 스트림을 확인하세요")
        print("종료하려면 Ctrl+C를 누르세요")
        print("=" * 50)
        
        # Flask 앱에 포트 정보 저장
        app.current_port = port
        
        # Flask 서버 시작
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("\n🛑 서버 종료 중...")
    except Exception as e:
        print(f"❌ 서버 오류: {e}")
    finally:
        camera.stop_camera()
        print("✅ 정리 완료")

if __name__ == '__main__':
    main()