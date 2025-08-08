#!/usr/bin/env python3
"""
Camera Streaming Server for RC Car Vehicle
Real-time camera streaming using Flask and OpenCV
"""

import os
import time
import threading
import logging
from datetime import datetime
from flask import Flask, Response, render_template_string

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    print("⚠️ OpenCV not available - camera streaming disabled")
    CV2_AVAILABLE = False

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    print("⚠️ PiCamera2 not available - using USB camera fallback")
    PICAMERA2_AVAILABLE = False

class CameraStreamer:
    """Camera streaming handler with multiple camera support"""
    
    def __init__(self, port: int = 8080, width: int = 640, height: int = 480, fps: int = 30):
        self.port = port
        self.width = width
        self.height = height
        self.fps = fps
        self.camera = None
        self.cap = None
        self.streaming = False
        self.frame = None
        self.lock = threading.Lock()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize camera
        self.setup_camera()
        
        # Flask app for streaming
        self.app = Flask(__name__)
        self.setup_routes()
    
    def setup_camera(self):
        """Setup camera based on availability"""
        if not CV2_AVAILABLE:
            self.logger.error("❌ OpenCV not available")
            return False
        
        # Try PiCamera2 first (Raspberry Pi camera) - this is the preferred method
        if PICAMERA2_AVAILABLE:
            try:
                self.camera = Picamera2()
                
                # List available cameras
                cameras = Picamera2.global_camera_info()
                self.logger.info(f"Available cameras: {len(cameras)}")
                for i, cam_info in enumerate(cameras):
                    self.logger.info(f"  Camera {i}: {cam_info}")
                
                # Configure camera with proper color space settings
                camera_config = self.camera.create_preview_configuration(
                    main={"format": "RGB888", "size": (self.width, self.height)},
                    controls={
                        "AwbEnable": True,  # Auto White Balance
                        "AeEnable": True,   # Auto Exposure
                    }
                )
                self.camera.configure(camera_config)
                
                # Set additional controls for better color reproduction
                self.camera.set_controls({
                    "AwbMode": 0,  # Auto white balance mode
                    "Saturation": 1.0,  # Normal saturation
                    "Brightness": 0.0,  # Normal brightness
                    "Contrast": 1.0,    # Normal contrast
                })
                
                # Start camera
                self.camera.start()
                
                # Wait for camera to be ready
                time.sleep(2)
                
                # Test frame capture
                test_array = self.camera.capture_array()
                if test_array is not None and test_array.size > 0:
                    self.logger.info(f"✅ PiCamera2 initialized - {test_array.shape}")
                    return True
                else:
                    self.logger.error("❌ PiCamera2 test capture failed")
                    self.camera.stop()
                    self.camera.close()
                    
            except Exception as e:
                self.logger.error(f"❌ PiCamera2 failed: {e}")
                if hasattr(self, 'camera') and self.camera:
                    try:
                        self.camera.stop()
                        self.camera.close()
                    except:
                        pass
        
        # Fallback message - OpenCV won't work with this camera setup
        self.logger.error("❌ Camera requires PiCamera2 - please install: pip install picamera2")
        return False
    
    def capture_frame(self):
        """Capture frame from camera with corrections"""
        try:
            if self.camera:  # PiCamera2
                frame = self.camera.capture_array()
                
                # PiCamera2 gives RGB format
                # For proper web streaming, we need BGR format for OpenCV operations
                # But the color issue might be due to incorrect conversion
                
                # Fix vertical flip issue first
                frame = cv2.flip(frame, 0)  # 0 = flip vertically (upside down fix)
                
                # PiCamera2 outputs RGB format which is correct for web streaming
                # No color conversion needed - keep RGB format
                # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # This was causing red/blue swap
                
                return frame
                
            elif self.cap:  # USB Camera
                ret, frame = self.cap.read()
                if ret:
                    # Fix vertical flip for USB camera too if needed
                    frame = cv2.flip(frame, 0)
                    return frame
                    
        except Exception as e:
            self.logger.error(f"❌ Frame capture error: {e}")
        
        return None
    
    def frame_generator(self):
        """Generate frames for streaming"""
        while self.streaming:
            frame = self.capture_frame()
            
            if frame is not None:
                # Add overlay information
                frame = self.add_overlay(frame)
                
                # Convert RGB to BGR only for JPEG encoding (OpenCV expects BGR)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    with self.lock:
                        self.frame = buffer.tobytes()
                
            time.sleep(1.0 / self.fps)  # Control frame rate
    
    def add_overlay(self, frame):
        """Add overlay information to frame"""
        try:
            # Add timestamp (RGB format: Green = (0, 255, 0))
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Add system info (RGB format: White = (255, 255, 255))
            cv2.putText(frame, "RC Car Live Stream", (10, frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Add frame size info (RGB format: Yellow = (255, 255, 0))
            size_info = f"{frame.shape[1]}x{frame.shape[0]} @ {self.fps}fps"
            cv2.putText(frame, size_info, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Overlay error: {e}")
        
        return frame
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main page with video stream"""
            return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RC Car Live Stream</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #1e1e1e;
            color: white;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .video-wrapper {
            position: relative;
            margin: 20px 0;
            display: inline-block;
        }
        .video-container {
            border: 2px solid #333;
            border-radius: 10px;
            overflow: hidden;
            background: #000;
        }
        .video-container.fullscreen {
            border: none;
            border-radius: 0;
            width: 100vw !important;
            height: 100vh !important;
            position: fixed;
            top: 0;
            left: 0;
            z-index: 9999;
            background: #000;
        }
        img {
            max-width: 100%;
            height: auto;
            display: block;
        }
        .fullscreen img {
            width: 100vw;
            height: 100vh;
            object-fit: contain;
        }
        .fullscreen-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            z-index: 10000;
            transition: background 0.3s ease;
        }
        .fullscreen-btn:hover {
            background: rgba(0, 0, 0, 0.9);
        }
        .fullscreen-btn:active {
            transform: scale(0.95);
        }
        .exit-fullscreen {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255, 0, 0, 0.8);
            color: white;
            border: none;
            padding: 15px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 18px;
            z-index: 10001;
            display: none;
        }
        .exit-fullscreen:hover {
            background: rgba(255, 0, 0, 1);
        }
        .info {
            background-color: #333;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .status {
            color: #4CAF50;
            font-weight: bold;
        }
        h1 {
            color: #4CAF50;
        }
        .controls {
            margin: 15px 0;
        }
        .control-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .control-btn:hover {
            background: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 RC Car Live Stream</h1>
        
        <div class="info">
            <p>📡 <span class="status">Streaming Active</span></p>
            <p>📹 Resolution: {{ width }}x{{ height }} @ {{ fps }}fps</p>
            <p>🌐 Stream URL: http://[vehicle-ip]:{{ port }}/video_feed</p>
        </div>
        
        <div class="video-wrapper">
            <div class="video-container" id="videoContainer">
                <img src="{{ url_for('video_feed') }}" alt="Live Stream" id="videoStream">
                <button class="fullscreen-btn" onclick="toggleFullscreen()" id="fullscreenBtn">⛶ 전체화면</button>
            </div>
        </div>
        
        <button class="exit-fullscreen" onclick="exitFullscreen()" id="exitBtn">✕ 전체화면 종료</button>
        
        <div class="controls">
            <button class="control-btn" onclick="refreshStream()">🔄 새로고침</button>
            <button class="control-btn" onclick="window.open('/video_feed', '_blank')">🔗 스트림만 보기</button>
        </div>
        
        <div class="info">
            <p>💡 <strong>사용법:</strong></p>
            <p>• 전체화면 버튼을 클릭하여 전체화면으로 시청</p>
            <p>• ESC 키 또는 종료 버튼으로 전체화면 해제</p>
            <p>• 직접 스트림 접근: <code>/video_feed</code></p>
            <p>• VLC/OBS URL: <code>http://[vehicle-ip]:{{ port }}/video_feed</code></p>
        </div>
    </div>

    <script>
        let isFullscreen = false;
        const videoContainer = document.getElementById('videoContainer');
        const videoStream = document.getElementById('videoStream');
        const fullscreenBtn = document.getElementById('fullscreenBtn');
        const exitBtn = document.getElementById('exitBtn');

        function toggleFullscreen() {
            if (!isFullscreen) {
                enterFullscreen();
            } else {
                exitFullscreen();
            }
        }

        function enterFullscreen() {
            // 브라우저 전체화면 API 사용
            if (videoContainer.requestFullscreen) {
                videoContainer.requestFullscreen();
            } else if (videoContainer.mozRequestFullScreen) {
                videoContainer.mozRequestFullScreen();
            } else if (videoContainer.webkitRequestFullscreen) {
                videoContainer.webkitRequestFullscreen();
            } else if (videoContainer.msRequestFullscreen) {
                videoContainer.msRequestFullscreen();
            } else {
                // 전체화면 API가 지원되지 않는 경우 CSS로 전체화면 효과
                customFullscreen();
            }
        }

        function customFullscreen() {
            videoContainer.classList.add('fullscreen');
            fullscreenBtn.style.display = 'none';
            exitBtn.style.display = 'block';
            isFullscreen = true;
            
            // 스크롤 방지
            document.body.style.overflow = 'hidden';
        }

        function exitFullscreen() {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            } else {
                // 커스텀 전체화면 해제
                customExitFullscreen();
            }
        }

        function customExitFullscreen() {
            videoContainer.classList.remove('fullscreen');
            fullscreenBtn.style.display = 'block';
            exitBtn.style.display = 'none';
            isFullscreen = false;
            
            // 스크롤 복원
            document.body.style.overflow = '';
        }

        function refreshStream() {
            const timestamp = new Date().getTime();
            videoStream.src = "{{ url_for('video_feed') }}" + "?t=" + timestamp;
        }

        // 전체화면 상태 변화 감지
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        document.addEventListener('mozfullscreenchange', handleFullscreenChange);
        document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
        document.addEventListener('msfullscreenchange', handleFullscreenChange);

        function handleFullscreenChange() {
            const isCurrentlyFullscreen = !!(document.fullscreenElement || 
                document.mozFullScreenElement || 
                document.webkitFullscreenElement || 
                document.msFullscreenElement);
            
            if (isCurrentlyFullscreen) {
                fullscreenBtn.style.display = 'none';
                exitBtn.style.display = 'block';
                isFullscreen = true;
            } else {
                fullscreenBtn.style.display = 'block';
                exitBtn.style.display = 'none';
                isFullscreen = false;
                videoContainer.classList.remove('fullscreen');
                document.body.style.overflow = '';
            }
        }

        // ESC 키로 전체화면 해제
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && isFullscreen) {
                exitFullscreen();
            }
        });

        // 스트림 로드 오류 처리
        videoStream.addEventListener('error', function() {
            console.log('스트림 로딩 오류 - 자동 새로고침 시도');
            setTimeout(refreshStream, 2000);
        });

        // 페이지 로드 완료시 스트림 상태 확인
        window.addEventListener('load', function() {
            console.log('RC Car 스트리밍 페이지 로드 완료');
        });
    </script>
</body>
</html>
            ''', width=self.width, height=self.height, fps=self.fps, port=self.port)
        
        @self.app.route('/video_feed')
        def video_feed():
            """Video streaming route"""
            return Response(self.generate_stream(), 
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/status')
        def status():
            """Status endpoint"""
            return {
                'streaming': self.streaming,
                'resolution': f"{self.width}x{self.height}",
                'fps': self.fps,
                'timestamp': datetime.now().isoformat()
            }
    
    def generate_stream(self):
        """Generate MJPEG stream"""
        while self.streaming:
            with self.lock:
                if self.frame is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + self.frame + b'\r\n')
            time.sleep(0.033)  # ~30fps max
    
    def start_streaming(self):
        """Start camera streaming"""
        if not CV2_AVAILABLE or (not self.camera and not self.cap):
            self.logger.error("❌ Cannot start streaming - no camera available")
            return False
        
        self.streaming = True
        
        # Start frame capture thread
        self.capture_thread = threading.Thread(target=self.frame_generator, daemon=True)
        self.capture_thread.start()
        
        # Start Flask server
        try:
            self.logger.info(f"🚀 Starting camera stream on port {self.port}")
            self.app.run(host='0.0.0.0', port=self.port, debug=False, 
                        threaded=True, use_reloader=False)
        except Exception as e:
            self.logger.error(f"❌ Flask server error: {e}")
            self.streaming = False
            return False
    
    def stop_streaming(self):
        """Stop camera streaming"""
        self.streaming = False
        
        if self.camera:
            self.camera.stop()
            self.camera.close()
        
        if self.cap:
            self.cap.release()
        
        self.logger.info("🛑 Camera streaming stopped")

def main():
    """Main entry point for standalone camera streaming"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RC Car Camera Streaming Server')
    parser.add_argument('--port', type=int, default=8080, help='Streaming port (default: 8080)')
    parser.add_argument('--width', type=int, default=640, help='Frame width (default: 640)')
    parser.add_argument('--height', type=int, default=480, help='Frame height (default: 480)')
    parser.add_argument('--fps', type=int, default=30, help='Frame rate (default: 30)')
    
    args = parser.parse_args()
    
    print("📹 RC Car Camera Streaming Server")
    print("=" * 40)
    print(f"🌐 Starting server on http://0.0.0.0:{args.port}")
    print(f"📱 Mobile access: http://[vehicle-ip]:{args.port}")
    print("🔗 Direct stream: http://[vehicle-ip]:{args.port}/video_feed")
    print("=" * 40)
    
    streamer = CameraStreamer(args.port, args.width, args.height, args.fps)
    
    try:
        streamer.start_streaming()
    except KeyboardInterrupt:
        print("\n🛑 Stopping camera stream...")
        streamer.stop_streaming()

if __name__ == "__main__":
    main()