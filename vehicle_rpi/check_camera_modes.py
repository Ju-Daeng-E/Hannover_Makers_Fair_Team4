#!/usr/bin/env python3
"""
Camera Resolution Checker for Raspberry Pi
Checks available camera modes and resolutions
"""

import sys

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("❌ PiCamera2 not available")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("❌ OpenCV not available")

def check_picamera2_modes():
    """Check PiCamera2 available modes and resolutions"""
    if not PICAMERA2_AVAILABLE:
        return
    
    print("\n📹 PiCamera2 Available Modes:")
    print("=" * 50)
    
    try:
        camera = Picamera2()
        
        # Get camera info
        cameras = Picamera2.global_camera_info()
        print(f"🔍 Found {len(cameras)} camera(s):")
        for i, cam_info in enumerate(cameras):
            print(f"  Camera {i}: {cam_info}")
        
        # Get sensor modes
        sensor_modes = camera.sensor_modes
        print(f"\n📊 Available sensor modes ({len(sensor_modes)}):")
        
        for i, mode in enumerate(sensor_modes):
            print(f"  Mode {i}: {mode}")
            if hasattr(mode, 'size'):
                print(f"    Size: {mode['size']}")
            if hasattr(mode, 'format'):
                print(f"    Format: {mode['format']}")
            if hasattr(mode, 'fps'):
                print(f"    FPS: {mode.get('fps', 'Unknown')}")
            print()
        
        # Common resolutions to test
        common_resolutions = [
            (320, 240),    # QVGA
            (640, 480),    # VGA
            (800, 600),    # SVGA
            (1024, 768),   # XGA
            (1280, 720),   # HD 720p
            (1280, 960),   # SXGA
            (1600, 1200),  # UXGA
            (1920, 1080),  # Full HD 1080p
            (2592, 1944),  # Pi Camera v1 max
            (3280, 2464),  # Pi Camera v2/HQ max
        ]
        
        print("🧪 Testing common resolutions:")
        print("-" * 30)
        
        working_resolutions = []
        
        for width, height in common_resolutions:
            try:
                config = camera.create_preview_configuration(
                    main={"format": "RGB888", "size": (width, height)}
                )
                print(f"✅ {width}x{height} - Supported")
                working_resolutions.append((width, height))
            except Exception as e:
                print(f"❌ {width}x{height} - Not supported ({str(e)[:50]}...)")
        
        print(f"\n🎯 Working resolutions ({len(working_resolutions)}):")
        for width, height in working_resolutions:
            print(f"  • {width}x{height}")
        
        camera.close()
        
    except Exception as e:
        print(f"❌ Error checking PiCamera2: {e}")

def check_usb_camera_modes():
    """Check USB camera available resolutions"""
    if not CV2_AVAILABLE:
        return
    
    print("\n📹 USB Camera Available Modes:")
    print("=" * 50)
    
    # Find available cameras
    available_cameras = []
    for i in range(4):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                available_cameras.append(i)
            cap.release()
    
    if not available_cameras:
        print("❌ No USB cameras found")
        return
    
    print(f"🔍 Found USB camera(s): {available_cameras}")
    
    # Test first available camera
    camera_id = available_cameras[0]
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        print(f"❌ Could not open camera {camera_id}")
        return
    
    # Common resolutions to test
    common_resolutions = [
        (320, 240),    # QVGA
        (640, 480),    # VGA
        (800, 600),    # SVGA
        (1024, 768),   # XGA
        (1280, 720),   # HD 720p
        (1280, 960),   # SXGA
        (1600, 1200),  # UXGA
        (1920, 1080),  # Full HD 1080p
    ]
    
    print(f"\n🧪 Testing resolutions for camera {camera_id}:")
    print("-" * 30)
    
    working_resolutions = []
    
    for width, height in common_resolutions:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Check what was actually set
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Test frame capture
        ret, frame = cap.read()
        
        if ret and frame is not None:
            if actual_width == width and actual_height == height:
                print(f"✅ {width}x{height} - Perfect match")
                working_resolutions.append((width, height, "perfect"))
            else:
                print(f"⚠️  {width}x{height} - Got {actual_width}x{actual_height}")
                working_resolutions.append((actual_width, actual_height, "adjusted"))
        else:
            print(f"❌ {width}x{height} - Failed to capture")
    
    print(f"\n🎯 Working resolutions:")
    perfect_resolutions = []
    for res in working_resolutions:
        if res[2] == "perfect":
            perfect_resolutions.append((res[0], res[1]))
            print(f"  • {res[0]}x{res[1]} (perfect)")
        else:
            print(f"  • {res[0]}x{res[1]} (camera adjusted)")
    
    cap.release()
    
    return perfect_resolutions

def main():
    """Main function to check all camera modes"""
    print("🎥 Camera Resolution Checker")
    print("=" * 50)
    
    if PICAMERA2_AVAILABLE:
        check_picamera2_modes()
    
    if CV2_AVAILABLE:
        check_usb_camera_modes()
    
    print("\n💡 Recommendations:")
    print("• For smooth streaming: 640x480 or 800x600")
    print("• For good quality: 1280x720 (HD)")
    print("• For best quality: 1920x1080 (if supported)")
    print("• Consider FPS vs resolution trade-off")

if __name__ == "__main__":
    main()