#!/usr/bin/env python3
"""
Simple Camera GUI for SSH - Minimal Dependencies
Lightweight camera viewer optimized for SSH X11 forwarding
"""

import os
import time
import cv2
import numpy as np
import logging
from datetime import datetime

# Force minimal OpenCV backend
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
os.environ['OPENCV_VIDEOIO_PRIORITY_GSTREAMER'] = '0'

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    print("⚠️ PiCamera2 not available")
    PICAMERA2_AVAILABLE = False

class SimpleCameraGUI:
    """Minimal camera GUI for SSH environments"""
    
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.camera = None
        
        # Setup minimal logging
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Check environment
        self.setup_environment()
    
    def setup_environment(self):
        """Setup minimal environment for SSH"""
        display = os.environ.get('DISPLAY')
        if not display:
            print("❌ No DISPLAY - Use 'ssh -X' or 'ssh -Y'")
            return False
            
        # Minimal X11 settings for SSH
        os.environ['QT_X11_NO_MITSHM'] = '1'
        os.environ['LIBGL_ALWAYS_INDIRECT'] = '1'
        
        print(f"✅ Display: {display}")
        return True
    
    def setup_camera(self):
        """Setup camera with minimal configuration"""
        if not PICAMERA2_AVAILABLE:
            print("❌ PiCamera2 required")
            return False
            
        try:
            self.camera = Picamera2()
            
            # Minimal camera config
            config = self.camera.create_preview_configuration(
                main={"format": "RGB888", "size": (self.width, self.height)}
            )
            self.camera.configure(config)
            self.camera.start()
            
            time.sleep(1)  # Short stabilization
            
            # Test capture
            test_frame = self.camera.capture_array()
            if test_frame is None:
                print("❌ Camera test failed")
                return False
                
            print(f"✅ Camera: {test_frame.shape}")
            return True
            
        except Exception as e:
            print(f"❌ Camera error: {e}")
            return False
    
    def run(self):
        """Run simple camera display"""
        if not self.setup_camera():
            return
            
        print("🖥️ Simple Camera GUI")
        print("Controls: 'q'=quit, 's'=save")
        
        window_name = "Simple Camera"
        
        try:
            # Create basic window
            cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
            
            while True:
                # Capture frame
                try:
                    frame = self.camera.capture_array()
                    if frame is None:
                        continue
                    
                    # Simple RGB to BGR conversion
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Flip if needed
                    frame = cv2.flip(frame, 0)
                    
                    # Add simple timestamp
                    timestamp = time.strftime("%H:%M:%S")
                    cv2.putText(frame, timestamp, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # Display
                    cv2.imshow(window_name, frame)
                    
                    # Handle keys
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:  # q or ESC
                        break
                    elif key == ord('s'):  # Save
                        filename = f"capture_{int(time.time())}.jpg"
                        cv2.imwrite(filename, frame)
                        print(f"📸 Saved: {filename}")
                        
                except Exception as e:
                    print(f"Frame error: {e}")
                    continue
                    
        except Exception as e:
            print(f"Display error: {e}")
            print("Try: export DISPLAY=:0.0")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up"""
        if self.camera:
            self.camera.stop()
            self.camera.close()
        cv2.destroyAllWindows()
        print("✅ Cleanup done")

if __name__ == "__main__":
    import sys
    
    # Parse simple args
    width = 640
    height = 480
    
    if len(sys.argv) > 1 and sys.argv[1] == "--small":
        width, height = 480, 320
    elif len(sys.argv) > 1 and sys.argv[1] == "--large":
        width, height = 864, 480
    
    print(f"📐 Resolution: {width}x{height}")
    
    gui = SimpleCameraGUI(width, height)
    gui.run()