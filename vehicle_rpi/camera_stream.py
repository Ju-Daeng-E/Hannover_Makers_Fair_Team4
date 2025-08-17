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
from speed_sensor import SpeedSensor

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
    
    def __init__(self, port: int = 8080, width: int = 800, height: int = 600, fps: int = 30, 
                 enable_speed_sensor: bool = True, speed_gpio_pin: int = 16):
        self.port = port
        self.width = width
        self.height = height
        self.fps = fps
        self.camera = None
        self.cap = None
        self.streaming = False
        self.frame = None
        self.lock = threading.Lock()
        
        # Speed sensor
        self.enable_speed_sensor = enable_speed_sensor
        self.speed_sensor = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize speed sensor
        if self.enable_speed_sensor:
            self.setup_speed_sensor(speed_gpio_pin)
        
        # Initialize camera
        self.setup_camera()
        
        # Flask app for streaming
        self.app = Flask(__name__)
        self.setup_routes()
    
    def setup_speed_sensor(self, gpio_pin: int):
        """Setup speed sensor for RPM and speed monitoring"""
        try:
            # Try real sensor first, fallback to simulation
            self.speed_sensor = SpeedSensor(
                gpio_pin=gpio_pin,
                pulses_per_turn=40,  # Same as Arduino code
                wheel_diameter_mm=64,  # Same as Arduino code
                simulation_mode=False  # Try real sensor first
            )
            self.logger.info(f"✅ Speed sensor initialized on GPIO {gpio_pin}")
        except Exception as e:
            self.logger.warning(f"⚠️ Real speed sensor failed: {e}")
            # Fallback to simulation mode
            try:
                self.speed_sensor = SpeedSensor(
                    gpio_pin=gpio_pin,
                    pulses_per_turn=40,
                    wheel_diameter_mm=64,
                    simulation_mode=True
                )
                self.logger.info(f"✅ Speed sensor initialized (simulation mode fallback)")
            except Exception as e2:
                self.logger.error(f"❌ Speed sensor setup completely failed: {e2}")
                self.speed_sensor = None
    
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
        
        # Fallback to USB camera if available
        for i in range(4):  # Try video0 to video3
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Test if we can read from this camera
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        cap.set(cv2.CAP_PROP_FPS, self.fps)
                        self.cap = cap
                        self.logger.info(f"✅ USB Camera initialized at /dev/video{i}")
                        return True
                    cap.release()
            except Exception as e:
                self.logger.debug(f"Failed to initialize camera {i}: {e}")
                continue
        
        self.logger.error("❌ No camera available")
        return False
    
    def capture_frame(self):
        """Capture frame from camera with corrections"""
        try:
            if self.camera:  # PiCamera2
                frame = self.camera.capture_array()
                
                # Fix vertical flip issue first
                frame = cv2.flip(frame, 0)  # 0 = flip vertically (upside down fix)
                # Fix horizontal flip (left-right mirror)
                frame = cv2.flip(frame, 1)  # 1 = flip horizontally (left-right mirror fix)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) 
                
                return frame
                
            elif self.cap:  # USB Camera
                ret, frame = self.cap.read()
                if ret:
                    # Fix vertical flip for USB camera too if needed
                    frame = cv2.flip(frame, 0)
                    # Fix horizontal flip (left-right mirror)
                    frame = cv2.flip(frame, 1)
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
                
                # Encode frame as JPEG with optimized settings for low latency
                ret, buffer = cv2.imencode('.jpg', frame_bgr, [
                    cv2.IMWRITE_JPEG_QUALITY, 75,  # Good quality but not too high
                    cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                ])
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
            
            # Add speed information if available
            if self.speed_sensor:
                speed_data = self.speed_sensor.get_speed_data()
                
                # Check if data is fresh (within 2 seconds)
                if speed_data['age_seconds'] <= 2.0:
                    # Add RPM (RGB format: Cyan = (0, 255, 255))
                    rpm_text = f"RPM: {speed_data['rpm']}"
                    cv2.putText(frame, rpm_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    
                    # Add Speed in km/h (RGB format: Yellow = (255, 255, 0))
                    speed_text = f"Speed: {speed_data['speed_kmh']:.1f} km/h"
                    cv2.putText(frame, speed_text, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    
                    # Add Speed in m/s (RGB format: Orange = (255, 165, 0))
                    speed_ms_text = f"({speed_data['speed_ms']:.2f} m/s)"
                    cv2.putText(frame, speed_ms_text, (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
                else:
                    # Show "No Speed Data" if data is stale
                    cv2.putText(frame, "Speed: No Data", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (128, 128, 128), 2)
            
            # Add system info (RGB format: White = (255, 255, 255))
            cv2.putText(frame, "RC Car Live Stream", (10, frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Add frame size info (RGB format: Light Blue = (173, 216, 230))
            size_info = f"{frame.shape[1]}x{frame.shape[0]} @ {self.fps}fps"
            cv2.putText(frame, size_info, (10, frame.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (173, 216, 230), 1)
            
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
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .video-wrapper {
            position: relative;
            margin: 20px 0;
            display: flex;
            justify-content: center;
            width: 100%;
        }
        .video-container {
            border: 2px solid #333;
            border-radius: 10px;
            overflow: hidden;
            background: #000;
            width: 100%;
            max-width: 800px;
            display: flex;
            justify-content: center;
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
            margin: 0 auto;
            border-radius: 8px;
        }
        .fullscreen img {
            width: 100vw;
            height: 100vh;
            object-fit: cover;
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
        }
        .fullscreen-btn:hover {
            background: rgba(0, 0, 0, 0.9);
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
            return Response(
                self.generate_stream(), 
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        @self.app.route('/status')
        def status():
            """Status endpoint"""
            return {
                'streaming': self.streaming,
                'resolution': f"{self.width}x{self.height}",
                'fps': self.fps,
                'camera_type': 'PiCamera2' if self.camera else 'USB',
                'timestamp': datetime.now().isoformat()
            }
    
    def generate_stream(self):
        """Generate MJPEG stream"""
        while self.streaming:
            with self.lock:
                if self.frame is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + self.frame + b'\r\n')
            time.sleep(0.01)  # Very low latency
    
    def start_streaming(self):
        """Start camera streaming"""
        if not CV2_AVAILABLE or (not self.camera and not self.cap):
            self.logger.error("❌ Cannot start streaming - no camera available")
            return False
        
        # Start speed sensor if enabled
        if self.speed_sensor:
            if self.speed_sensor.start():
                self.logger.info("✅ Speed sensor started")
            else:
                self.logger.warning("⚠️ Speed sensor failed to start")
        
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
        
        # Stop speed sensor
        if self.speed_sensor:
            self.speed_sensor.stop()
            self.logger.info("🛑 Speed sensor stopped")
        
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
    parser.add_argument('--width', type=int, default=800, help='Frame width (default: 800)')
    parser.add_argument('--height', type=int, default=600, help='Frame height (default: 600)')
    parser.add_argument('--fps', type=int, default=30, help='Frame rate (default: 30)')
    parser.add_argument('--no-speed', action='store_true', help='Disable speed sensor')
    parser.add_argument('--speed-gpio', type=int, default=16, help='Speed sensor GPIO pin (default: 16)')
    parser.add_argument('--speed-sim', action='store_true', help='Use speed simulation mode')
    
    args = parser.parse_args()
    
    print("📹 RC Car Camera Streaming Server")
    print("=" * 40)
    print(f"🌐 Starting server on http://0.0.0.0:{args.port}")
    print(f"📱 Mobile access: http://[vehicle-ip]:{args.port}")
    print("🔗 Direct stream: http://[vehicle-ip]:{args.port}/video_feed")
    print(f"🏎️ Speed sensor: {'Disabled' if args.no_speed else f'GPIO {args.speed_gpio}'}")
    print("=" * 40)
    
    streamer = CameraStreamer(
        port=args.port, 
        width=args.width, 
        height=args.height, 
        fps=args.fps,
        enable_speed_sensor=not args.no_speed,
        speed_gpio_pin=args.speed_gpio
    )
    
    try:
        streamer.start_streaming()
    except KeyboardInterrupt:
        print("\n🛑 Stopping camera stream...")
        streamer.stop_streaming()

if __name__ == "__main__":
    main()