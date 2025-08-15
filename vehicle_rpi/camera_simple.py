#!/usr/bin/env python3
"""
Simple Camera Streaming Server - Using sender_to_pc.py approach
"""

import subprocess
import threading
import time
from flask import Flask, Response

class SimpleCameraStream:
    def __init__(self, port=8080):
        self.port = port
        self.app = Flask(__name__)
        self.setup_routes()
    
    def capture_frame(self):
        """Capture single JPEG frame using libcamera-still"""
        try:
            cmd = ["libcamera-still", "-t", "1", "--width", "640", "--height", "480", "-e", "jpg", "-o", "-"]
            process = subprocess.run(cmd, capture_output=True, timeout=3)
            
            if process.returncode == 0 and len(process.stdout) > 0:
                return process.stdout
            else:
                print(f"Frame capture error: {process.stderr}")
                return None
        except Exception as e:
            print(f"Capture exception: {e}")
            return None
    
    def generate_frames(self):
        """Generate frames for MJPEG stream"""
        while True:
            frame = self.capture_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + 
                       frame + b'\r\n')
            time.sleep(0.1)  # 10 FPS
    
    def setup_routes(self):
        @self.app.route('/')
        def index():
            return '''
<!DOCTYPE html>
<html>
<head>
    <title>RC Car Camera</title>
</head>
<body>
    <h1>RC Car Live Stream</h1>
    <img src="/video_feed" style="width:100%; max-width:800px;">
</body>
</html>
            '''
        
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self.generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def run(self):
        print(f"Starting simple camera stream on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)

if __name__ == "__main__":
    stream = SimpleCameraStream(8080)
    stream.run()