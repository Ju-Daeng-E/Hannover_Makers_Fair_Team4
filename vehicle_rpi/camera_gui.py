#!/usr/bin/env python3
"""
Camera GUI Viewer for SSH X11 Forwarding
Direct camera display using OpenCV GUI for remote viewing
"""

import os
import time
import cv2
import numpy as np
import threading
import logging
from datetime import datetime

# Configure OpenCV for SSH X11 environment
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QT_X11_NO_MITSHM'] = '1'  # Disable shared memory for SSH
if 'DISPLAY' in os.environ and 'SSH_CLIENT' in os.environ:
    # Force OpenCV to use GTK backend for better SSH compatibility
    os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '0'
    os.environ['OPENCV_VIDEOIO_DEBUG'] = '1'

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    print("⚠️ PiCamera2 not available")
    PICAMERA2_AVAILABLE = False

class CameraGUI:
    """Direct camera GUI viewer with X11 forwarding support"""
    
    def __init__(self, width: int = 864, height: int = 480, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self.camera = None
        self.running = False
        self.frame = None
        self.lock = threading.Lock()
        
        # Performance metrics
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.actual_fps = 0
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Check display environment
        self.check_display_environment()
        
    def check_display_environment(self):
        """Check if X11 display is available and configure for SSH"""
        display = os.environ.get('DISPLAY')
        if not display:
            self.logger.warning("⚠️ No DISPLAY environment variable found")
            self.logger.info("💡 SSH 연결시 'ssh -X username@hostname' 사용하세요")
            return False
        else:
            self.logger.info(f"✅ DISPLAY found: {display}")
            
            # Configure for SSH environment
            if 'SSH_CLIENT' in os.environ:
                self.logger.info("🔧 SSH 환경 최적화 설정 적용")
                # Disable hardware acceleration for SSH
                os.environ['LIBGL_ALWAYS_INDIRECT'] = '1'
                # Use software rendering
                os.environ['MESA_GL_VERSION_OVERRIDE'] = '3.3'
            
            return True
    
    def setup_camera(self):
        """Setup camera with optimal settings for GUI display"""
        if not PICAMERA2_AVAILABLE:
            self.logger.error("❌ PiCamera2 not available")
            return False
        
        try:
            self.camera = Picamera2()
            
            # Configure camera for optimal GUI performance
            camera_config = self.camera.create_preview_configuration(
                main={"format": "RGB888", "size": (self.width, self.height)},
                controls={
                    "FrameRate": self.fps,
                    "AwbEnable": True,
                    "AeEnable": True,
                }
            )
            self.camera.configure(camera_config)
            
            # Optimize camera settings for GUI viewing
            self.camera.set_controls({
                "AwbMode": 0,  # Auto white balance
                "Saturation": 1.2,  # Enhanced saturation for better viewing
                "Brightness": 0.1,  # Slightly brighter
                "Contrast": 1.1,    # Enhanced contrast
                "NoiseReductionMode": 1,  # Minimal noise reduction for speed
            })
            
            # Start camera
            self.camera.start()
            time.sleep(2)  # Wait for camera to stabilize
            
            # Test frame capture
            test_array = self.camera.capture_array()
            if test_array is not None and test_array.size > 0:
                self.logger.info(f"✅ PiCamera2 initialized - {test_array.shape}")
                return True
            else:
                self.logger.error("❌ Camera test capture failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Camera setup failed: {e}")
            return False
    
    def capture_frame(self):
        """Capture frame from camera with optimizations for GUI display"""
        try:
            if self.camera:
                frame = self.camera.capture_array()
                
                # Fix vertical flip if needed
                frame = cv2.flip(frame, 0)  # 0 = flip vertically
                
                # Convert RGB to BGR for OpenCV display
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                return frame
        except Exception as e:
            self.logger.error(f"❌ Frame capture error: {e}")
        
        return None
    
    def add_overlay(self, frame):
        """Add informational overlay to frame"""
        try:
            # Add timestamp (BGR format: Green)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Add system info (BGR format: White)
            cv2.putText(frame, "RC Car Direct View", (10, frame.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Add frame size and actual FPS (BGR format: Cyan)
            size_info = f"{frame.shape[1]}x{frame.shape[0]} @ {self.actual_fps:.1f}fps"
            cv2.putText(frame, size_info, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Add controls info (BGR format: Orange)
            cv2.putText(frame, "Press 'q' to quit, 's' to save screenshot", (10, frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Overlay error: {e}")
        
        return frame
    
    def update_fps(self):
        """Update actual FPS counter"""
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.actual_fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
    
    def start_gui(self):
        """Start GUI camera viewer with SSH optimization"""
        if not self.setup_camera():
            return False
        
        try:
            # Try to set OpenCV backend to GTK for better SSH compatibility
            cv2.namedWindow('test', cv2.WINDOW_NORMAL)
            cv2.destroyWindow('test')
            self.logger.info("✅ OpenCV GUI 백엔드 초기화 성공")
        except Exception as e:
            self.logger.warning(f"⚠️ OpenCV 백엔드 경고: {e}")
        
        # Create OpenCV window with specific properties for SSH
        window_name = "RC Car Camera - SSH Remote View"
        try:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
            cv2.resizeWindow(window_name, self.width, self.height)
            self.logger.info("🖼️ 카메라 창 생성 완료")
        except Exception as e:
            self.logger.error(f"❌ 창 생성 실패: {e}")
            return False
        
        self.logger.info("🖥️ Starting GUI camera viewer")
        self.logger.info("📋 Controls:")
        self.logger.info("   'q' or ESC: Quit")
        self.logger.info("   's': Save screenshot")
        self.logger.info("   'f': Toggle fullscreen")
        self.logger.info("   'r': Reset camera")
        
        self.running = True
        fullscreen = False
        
        try:
            while self.running:
                frame = self.capture_frame()
                
                if frame is not None:
                    # Update FPS counter
                    self.update_fps()
                    
                    # Add overlay information
                    frame = self.add_overlay(frame)
                    
                    # Display frame
                    cv2.imshow(window_name, frame)
                    
                    # Handle keyboard input
                    key = cv2.waitKey(1) & 0xFF
                    
                    if key == ord('q') or key == 27:  # 'q' or ESC
                        self.logger.info("🛑 Quit requested by user")
                        break
                    elif key == ord('s'):  # Save screenshot
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"screenshot_{timestamp}.jpg"
                        cv2.imwrite(filename, frame)
                        self.logger.info(f"📸 Screenshot saved: {filename}")
                    elif key == ord('f'):  # Toggle fullscreen
                        if fullscreen:
                            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                            fullscreen = False
                            self.logger.info("🔲 Windowed mode")
                        else:
                            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                            fullscreen = True
                            self.logger.info("🔳 Fullscreen mode")
                    elif key == ord('r'):  # Reset camera
                        self.logger.info("🔄 Resetting camera...")
                        self.camera.stop()
                        time.sleep(1)
                        self.camera.start()
                        time.sleep(2)
                
                # Control frame rate
                time.sleep(1.0 / self.fps)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Interrupted by user (Ctrl+C)")
        except Exception as e:
            self.logger.error(f"❌ GUI error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        if self.camera:
            try:
                self.camera.stop()
                self.camera.close()
            except:
                pass
        
        cv2.destroyAllWindows()
        self.logger.info("🧹 Cleanup completed")

def main():
    """Main entry point for GUI camera viewer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RC Car Camera GUI Viewer for SSH')
    parser.add_argument('--width', type=int, default=864, help='Frame width (default: 864)')
    parser.add_argument('--height', type=int, default=480, help='Frame height (default: 480)')
    parser.add_argument('--fps', type=int, default=30, help='Frame rate (default: 30)')
    
    args = parser.parse_args()
    
    print("🖥️ RC Car Camera GUI Viewer")
    print("=" * 40)
    print("🔧 SSH X11 Forwarding을 위한 직접 GUI 뷰어")
    print(f"📐 해상도: {args.width}x{args.height}")
    print(f"🎬 FPS: {args.fps}")
    print("💡 SSH 연결시 'ssh -X username@hostname' 사용")
    print("=" * 40)
    
    # Check if running in SSH environment
    if 'SSH_CLIENT' in os.environ:
        print("🌐 SSH 연결 감지됨")
        if 'DISPLAY' not in os.environ:
            print("❌ X11 포워딩이 활성화되지 않았습니다")
            print("💡 'ssh -X' 또는 'ssh -Y' 옵션을 사용하세요")
            return
        else:
            print(f"✅ X11 포워딩 활성화됨: {os.environ['DISPLAY']}")
    
    gui = CameraGUI(args.width, args.height, args.fps)
    
    try:
        gui.start_gui()
    except KeyboardInterrupt:
        print("\n🛑 카메라 GUI 종료됨")

if __name__ == "__main__":
    main()