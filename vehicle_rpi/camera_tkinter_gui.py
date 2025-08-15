#!/usr/bin/env python3
"""
Tkinter-based Camera GUI for SSH
Pure Python GUI without OpenCV display dependencies
"""

import os
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import numpy as np

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    print("⚠️ PiCamera2 not available")
    PICAMERA2_AVAILABLE = False

class TkinterCameraGUI:
    """Pure Tkinter camera GUI - most compatible with SSH"""
    
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.camera = None
        self.running = False
        self.current_frame = None
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Setup Tkinter GUI"""
        self.root = tk.Tk()
        self.root.title("RC Car Camera - SSH Remote View")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Info label
        self.info_label = ttk.Label(main_frame, text="카메라 초기화 중...")
        self.info_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Camera display label
        self.camera_label = ttk.Label(main_frame)
        self.camera_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0))
        
        self.start_button = ttk.Button(button_frame, text="카메라 시작", command=self.start_camera)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="카메라 정지", command=self.stop_camera, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = ttk.Button(button_frame, text="스크린샷", command=self.save_screenshot, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.quit_button = ttk.Button(button_frame, text="종료", command=self.on_closing)
        self.quit_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Keyboard bindings
        self.root.bind('<KeyPress-s>', lambda e: self.save_screenshot())
        self.root.bind('<KeyPress-q>', lambda e: self.on_closing())
        self.root.bind('<Escape>', lambda e: self.on_closing())
        
        # Focus for keyboard events
        self.root.focus_set()
        
    def setup_camera(self):
        """Setup camera"""
        if not PICAMERA2_AVAILABLE:
            self.status_var.set("❌ PiCamera2가 필요합니다")
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
                self.status_var.set("❌ 카메라 테스트 실패")
                return False
            
            self.status_var.set(f"✅ 카메라 준비됨: {test_frame.shape}")
            return True
            
        except Exception as e:
            self.status_var.set(f"❌ 카메라 오류: {e}")
            return False
    
    def capture_frame_thread(self):
        """Background thread for frame capture and display"""
        while self.running:
            try:
                if self.camera:
                    # Capture frame
                    frame = self.camera.capture_array()
                    if frame is not None:
                        # Flip if needed
                        frame = np.flip(frame, axis=0)  # Vertical flip
                        
                        # Convert to PIL Image
                        pil_image = Image.fromarray(frame.astype('uint8'), 'RGB')
                        
                        # Add timestamp overlay
                        draw = ImageDraw.Draw(pil_image)
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        try:
                            # Try to use default font
                            font = ImageFont.load_default()
                        except:
                            font = None
                        
                        # Draw timestamp
                        draw.text((10, 10), timestamp, fill=(0, 255, 0), font=font)
                        draw.text((10, self.height-30), f"RC Car Camera - {self.width}x{self.height}", 
                                 fill=(255, 255, 255), font=font)
                        
                        # Store current frame for saving
                        self.current_frame = pil_image.copy()
                        
                        # Resize for display if needed
                        display_image = pil_image.resize((640, 480), Image.Resampling.LANCZOS)
                        
                        # Convert to PhotoImage
                        photo = ImageTk.PhotoImage(display_image)
                        
                        # Update GUI (thread-safe)
                        self.root.after(0, self.update_camera_display, photo)
                        
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"프레임 오류: {e}"))
            
            time.sleep(1.0 / 15)  # ~15 FPS for smooth display
    
    def update_camera_display(self, photo):
        """Update camera display (called from main thread)"""
        self.camera_label.configure(image=photo)
        self.camera_label.image = photo  # Keep a reference
    
    def start_camera(self):
        """Start camera"""
        if self.setup_camera():
            self.running = True
            self.capture_thread = threading.Thread(target=self.capture_frame_thread, daemon=True)
            self.capture_thread.start()
            
            # Update UI
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.save_button.configure(state=tk.NORMAL)
            self.status_var.set("카메라 실행 중...")
            self.info_label.configure(text="키보드: 's'=저장, 'q'=종료, ESC=종료")
    
    def stop_camera(self):
        """Stop camera"""
        self.running = False
        
        if self.camera:
            try:
                self.camera.stop()
                self.camera.close()
                self.camera = None
            except:
                pass
        
        # Update UI
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.save_button.configure(state=tk.DISABLED)
        self.camera_label.configure(image='')
        self.status_var.set("카메라 정지됨")
        self.info_label.configure(text="카메라가 정지되었습니다")
    
    def save_screenshot(self):
        """Save current frame as screenshot"""
        if self.current_frame:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                self.current_frame.save(filename)
                self.status_var.set(f"📸 저장됨: {filename}")
                messagebox.showinfo("저장 완료", f"스크린샷이 저장되었습니다:\n{filename}")
            except Exception as e:
                messagebox.showerror("저장 실패", f"스크린샷 저장 실패:\n{e}")
        else:
            messagebox.showwarning("경고", "저장할 이미지가 없습니다")
    
    def on_closing(self):
        """Handle window closing"""
        if self.running:
            self.stop_camera()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Run GUI"""
        print("🖥️ Tkinter Camera GUI")
        print("📋 순수 Python GUI - SSH 완전 호환")
        print(f"📐 해상도: {self.width}x{self.height}")
        print("🔧 Qt 의존성 없음")
        
        # Check display
        display = os.environ.get('DISPLAY')
        if display:
            print(f"✅ Display: {display}")
        else:
            print("⚠️ No DISPLAY - SSH X11 forwarding 필요")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("🛑 Interrupted")
        finally:
            if self.running:
                self.stop_camera()

if __name__ == "__main__":
    import sys
    
    # Simple argument parsing
    width, height = 640, 480
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--small":
            width, height = 480, 320
        elif sys.argv[1] == "--large":
            width, height = 864, 480
    
    print("🚀 Tkinter 기반 카메라 GUI 시작...")
    
    gui = TkinterCameraGUI(width, height)
    gui.run()