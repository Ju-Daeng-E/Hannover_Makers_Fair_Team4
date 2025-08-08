#!/usr/bin/env python3

import cv2
import time

print("Testing camera with different backends...")

# Test different backends and formats
backends = [
    (cv2.CAP_V4L2, "V4L2"),
    (cv2.CAP_ANY, "ANY"),
]

fourcc_formats = [
    (cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'), "YUYV"),
    (cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), "MJPG"),
    (None, "DEFAULT"),
]

for backend_id, backend_name in backends:
    print(f"\n--- Testing {backend_name} backend ---")
    
    try:
        cap = cv2.VideoCapture(0, backend_id)
        if cap.isOpened():
            print(f"✅ Camera opened with {backend_name}")
            
            for fourcc, format_name in fourcc_formats:
                print(f"  Testing {format_name} format...")
                
                # Reset capture
                cap.release()
                cap = cv2.VideoCapture(0, backend_id)
                
                if fourcc is not None:
                    cap.set(cv2.CAP_PROP_FOURCC, fourcc)
                
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                # Test frame reading
                time.sleep(0.5)  # Let camera warm up
                
                success_count = 0
                for i in range(10):  # Try 10 frames
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        success_count += 1
                        if i == 0:
                            print(f"    ✅ First frame: {frame.shape}, dtype: {frame.dtype}")
                    time.sleep(0.1)
                
                print(f"    Success rate: {success_count}/10 frames")
                
                if success_count >= 8:
                    print(f"    🎯 {backend_name} with {format_name} works well!")
                    
                    # Save test image
                    if success_count > 0:
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            cv2.imwrite(f'/home/pi/test_{backend_name}_{format_name}.jpg', frame)
                            print(f"    📸 Test image saved")
                
                cap.release()
        else:
            print(f"❌ Could not open camera with {backend_name}")
            
    except Exception as e:
        print(f"❌ Error with {backend_name}: {e}")

print("\n--- Direct V4L2 test ---")
import subprocess
try:
    result = subprocess.run(['v4l2-ctl', '-d', '/dev/video0', '--set-fmt-video=width=640,height=480,pixelformat=YUYV'], 
                          capture_output=True, text=True)
    print("v4l2-ctl output:", result.stdout)
    if result.stderr:
        print("v4l2-ctl errors:", result.stderr)
except Exception as e:
    print(f"v4l2-ctl error: {e}")