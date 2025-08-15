#!/usr/bin/env python3
"""
Matplotlib-based Camera GUI for SSH
No Qt dependencies, uses matplotlib for display
"""

import os
import time
import numpy as np
from datetime import datetime
import threading

# Force matplotlib to use Agg backend initially, then switch to TkAgg for GUI
import matplotlib
matplotlib.use('TkAgg')  # Use Tkinter backend for SSH compatibility
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    print("⚠️ PiCamera2 not available")
    PICAMERA2_AVAILABLE = False

class MatplotlibCameraGUI:
    """Camera GUI using matplotlib - Qt-free solution"""
    
    def __init__(self, width=640, height=480, fps=15):
        self.width = width
        self.height = height
        self.fps = fps
        self.camera = None
        self.current_frame = None
        self.running = False
        
        # Setup environment for SSH
        self.setup_environment()
        
    def setup_environment(self):
        """Setup environment for matplotlib GUI"""
        # Check display
        display = os.environ.get('DISPLAY')
        if not display:
            print("❌ No DISPLAY - Use 'ssh -X' or 'ssh -Y'")
            return False
        
        print(f"✅ Display: {display}")
        
        # Configure for SSH
        os.environ['MPLBACKEND'] = 'TkAgg'
        
        return True
        
    def setup_camera(self):
        """Setup camera"""
        if not PICAMERA2_AVAILABLE:
            print("❌ PiCamera2 required")
            return False
            
        try:
            self.camera = Picamera2()
            
            # Camera configuration
            config = self.camera.create_preview_configuration(
                main={"format": "RGB888", "size": (self.width, self.height)}
            )
            self.camera.configure(config)
            self.camera.start()
            
            time.sleep(1)
            
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
    
    def capture_frame_thread(self):
        """Background thread for frame capture"""
        while self.running:
            try:
                if self.camera:
                    frame = self.camera.capture_array()
                    if frame is not None:
                        # Flip if needed and add timestamp
                        frame = np.flip(frame, axis=0)  # Vertical flip
                        self.current_frame = frame.copy()
            except Exception as e:
                print(f"Frame error: {e}")
            
            time.sleep(1.0 / self.fps)
    
    def update_plot(self, frame_num):
        """Update matplotlib plot with new frame"""
        if self.current_frame is not None:
            self.ax.clear()
            self.ax.imshow(self.current_frame)
            self.ax.axis('off')
            
            # Add timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.ax.text(10, 30, timestamp, color='lime', fontsize=12, 
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='black', alpha=0.7))
            
            # Add info
            self.ax.text(10, self.height-20, f"RC Car Camera - {self.width}x{self.height}", 
                        color='white', fontsize=10,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='black', alpha=0.7))
        
        return []
    
    def on_key_press(self, event):
        """Handle keyboard events"""
        if event.key == 'q' or event.key == 'escape':
            print("🛑 Quit requested")
            self.running = False
            plt.close('all')
        elif event.key == 's':
            if self.current_frame is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.png"
                plt.imsave(filename, self.current_frame)
                print(f"📸 Saved: {filename}")
    
    def run(self):
        """Run matplotlib GUI"""
        if not self.setup_camera():
            return
            
        print("🖥️ Matplotlib Camera GUI")
        print("Controls: 'q'=quit, 's'=save, close window=quit")
        
        # Setup matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.fig.canvas.manager.set_window_title('RC Car Camera - SSH Remote View')
        
        # Connect keyboard events
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        
        # Start camera thread
        self.running = True
        self.capture_thread = threading.Thread(target=self.capture_frame_thread, daemon=True)
        self.capture_thread.start()
        
        try:
            # Create animation
            ani = FuncAnimation(self.fig, self.update_plot, interval=1000//self.fps, 
                              blit=False, cache_frame_data=False)
            
            # Show plot
            plt.tight_layout()
            plt.show()
            
        except KeyboardInterrupt:
            print("🛑 Interrupted")
        except Exception as e:
            print(f"❌ Display error: {e}")
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
        
        plt.close('all')
        print("✅ Cleanup done")

if __name__ == "__main__":
    import sys
    
    # Simple argument parsing
    width, height = 640, 480
    fps = 15  # Lower FPS for matplotlib
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--small":
            width, height = 480, 320
        elif sys.argv[1] == "--large":
            width, height = 864, 480
        elif sys.argv[1] == "--fast":
            fps = 20
    
    print(f"📐 Resolution: {width}x{height} @ {fps}fps")
    print("🔧 Using matplotlib backend (Qt-free)")
    
    gui = MatplotlibCameraGUI(width, height, fps)
    gui.run()