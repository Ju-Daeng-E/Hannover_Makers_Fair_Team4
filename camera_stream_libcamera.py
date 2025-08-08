#!/usr/bin/env python3
"""
Raspberry Pi Camera Web Streaming Server (libcamera version)
Streams camera feed via Flask web server using libcamera-vid for better compatibility
"""

import subprocess
import threading
import time
import logging
from flask import Flask, render_template_string, Response
import signal
import sys
import os

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
            <p>실시간 카메라 스트리밍이 활성화되었습니다 (libcamera)</p>
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

class LibcameraStream:
    """libcamera 기반 카메라 스트리밍 클래스"""
    
    def __init__(self, width=640, height=480, framerate=30):
        self.width = width
        self.height = height  
        self.framerate = framerate
        self.process = None
        self.running = False
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def start_camera(self):
        """libcamera-vid를 사용한 스트리밍 시작"""
        try:
            # libcamera-vid 명령 구성
            cmd = [
                'libcamera-vid',
                '--timeout', '0',  # 무한 실행
                '--width', str(self.width),
                '--height', str(self.height),
                '--framerate', str(self.framerate),
                '--inline',  # SPS/PPS를 각 프레임에 포함
                '--listen',  # TCP 서버 모드
                '--output', 'tcp://127.0.0.1:8888',
                '--codec', 'mjpeg',  # MJPEG 코덱 사용
                '--quality', '85',
                '--nopreview'
            ]
            
            self.logger.info("libcamera-vid 시작 중...")
            self.logger.info(f"명령어: {' '.join(cmd)}")
            
            # libcamera-vid 프로세스 시작
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # 카메라 초기화 대기
            time.sleep(3)
            
            # 프로세스가 살아있는지 확인
            if self.process.poll() is None:
                self.running = True
                self.logger.info("✅ libcamera-vid 시작 성공")
                return True
            else:
                stdout, stderr = self.process.communicate()
                self.logger.error(f"libcamera-vid 실행 실패:")
                self.logger.error(f"stdout: {stdout.decode()}")
                self.logger.error(f"stderr: {stderr.decode()}")
                return False
                
        except FileNotFoundError:
            self.logger.error("libcamera-vid를 찾을 수 없습니다. libcamera 패키지를 설치하세요:")
            self.logger.error("sudo apt update && sudo apt install -y libcamera-apps")
            return False
        except Exception as e:
            self.logger.error(f"카메라 시작 오류: {e}")
            return False
    
    def stop_camera(self):
        """카메라 스트리밍 정지"""
        self.running = False
        if self.process:
            try:
                # 프로세스 그룹 종료
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except:
                    pass
            self.process = None
        self.logger.info("카메라 정지됨")

# Flask 앱 초기화
app = Flask(__name__)
camera = LibcameraStream()

@app.route('/')
def index():
    """메인 페이지"""
    import socket
    hostname = socket.gethostname()
    try:
        # 네트워크 인터페이스에서 IP 가져오기
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "localhost"
    
    return render_template_string(HTML_TEMPLATE, 
                                host=local_ip, 
                                port=5000)

def generate_frames():
    """TCP 스트림에서 MJPEG 프레임 읽기"""
    import socket
    
    while camera.running:
        try:
            # TCP 소켓으로 libcamera-vid에 연결
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('127.0.0.1', 8888))
            
            buffer = b""
            
            while camera.running:
                # 데이터 수신
                data = sock.recv(4096)
                if not data:
                    break
                    
                buffer += data
                
                # JPEG 시작/끝 마커 찾기
                start_marker = b'\xff\xd8'  # JPEG 시작
                end_marker = b'\xff\xd9'    # JPEG 끝
                
                while True:
                    start_pos = buffer.find(start_marker)
                    if start_pos == -1:
                        break
                        
                    end_pos = buffer.find(end_marker, start_pos + 2)
                    if end_pos == -1:
                        break
                        
                    # 완전한 JPEG 프레임 추출
                    frame_data = buffer[start_pos:end_pos + 2]
                    buffer = buffer[end_pos + 2:]
                    
                    # 멀티파트 응답 형식으로 전송
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                    
        except Exception as e:
            logging.error(f"스트림 오류: {e}")
            time.sleep(1)  # 재연결 대기
        finally:
            try:
                sock.close()
            except:
                pass

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
        'width': camera.width,
        'height': camera.height,
        'framerate': camera.framerate
    }

def signal_handler(sig, frame):
    """시그널 핸들러"""
    print("\n🛑 서버 종료 중...")
    camera.stop_camera()
    sys.exit(0)

def main():
    """메인 함수"""
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("🎥 Raspberry Pi Camera Web Streaming Server (libcamera) 시작...")
        print("=" * 60)
        
        # 카메라 시작
        if not camera.start_camera():
            print("❌ 카메라 초기화 실패")
            print("\n다음을 확인하세요:")
            print("1. libcamera 패키지 설치: sudo apt install -y libcamera-apps")
            print("2. 카메라 연결 확인: libcamera-hello --list-cameras")
            print("3. 카메라 테스트: libcamera-hello -t 5000")
            return
            
        print("✅ 카메라 초기화 완료")
        
        # 네트워크 정보 출력
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "localhost"
        
        print(f"🌐 서버 정보:")
        print(f"   - 로컬 주소: http://localhost:5000")
        print(f"   - 네트워크 주소: http://{local_ip}:5000")
        print(f"📷 카메라 설정:")
        print(f"   - 해상도: {camera.width}x{camera.height}")
        print(f"   - 프레임레이트: {camera.framerate}fps")
        print(f"   - 코덱: MJPEG")
        print("=" * 60)
        print("웹 브라우저에서 위 주소로 접속하여 스트림을 확인하세요")
        print("종료하려면 Ctrl+C를 누르세요")
        print("=" * 60)
        
        # Flask 서버 시작
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("\n🛑 서버 종료 중...")
    except Exception as e:
        print(f"❌ 서버 오류: {e}")
    finally:
        camera.stop_camera()
        print("✅ 정리 완료")

if __name__ == '__main__':
    main()