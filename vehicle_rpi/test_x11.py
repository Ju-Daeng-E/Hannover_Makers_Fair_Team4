#!/usr/bin/env python3
"""
X11 Forwarding Test for SSH Camera GUI
Simple test to verify X11 display forwarding works
"""

import os
import cv2
import numpy as np

def test_x11_display():
    """Test if X11 forwarding is working"""
    print("🧪 X11 포워딩 테스트")
    print("=" * 30)
    
    # Check DISPLAY environment
    display = os.environ.get('DISPLAY')
    if not display:
        print("❌ DISPLAY 환경변수가 없습니다")
        print("💡 SSH 연결시 'ssh -X' 옵션을 사용하세요")
        return False
    else:
        print(f"✅ DISPLAY: {display}")
    
    # Check SSH environment
    if 'SSH_CLIENT' in os.environ:
        print(f"🌐 SSH 클라이언트: {os.environ['SSH_CLIENT'].split()[0]}")
    
    try:
        # Create test window
        print("🖼️ 테스트 창 생성 중...")
        
        # Create a simple test image
        test_image = np.zeros((300, 400, 3), dtype=np.uint8)
        test_image[:] = (50, 50, 50)  # Dark gray background
        
        # Add text
        cv2.putText(test_image, "X11 Test Success!", (50, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(test_image, "Press any key to close", (50, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(test_image, f"DISPLAY: {display}", (10, 280), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Display test window
        window_name = "X11 Forwarding Test"
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
        cv2.imshow(window_name, test_image)
        
        print("✅ 테스트 창이 표시되어야 합니다")
        print("⌨️ 아무 키나 눌러서 종료...")
        
        cv2.waitKey(0)  # Wait for key press
        cv2.destroyAllWindows()
        
        print("🎉 X11 포워딩이 정상적으로 작동합니다!")
        return True
        
    except Exception as e:
        print(f"❌ X11 테스트 실패: {e}")
        print("💡 다음을 확인해보세요:")
        print("   1. SSH 연결시 -X 또는 -Y 옵션 사용")
        print("   2. 로컬 컴퓨터에서 X11 서버 실행 (Windows: VcXsrv, macOS: XQuartz)")
        print("   3. 방화벽에서 X11 포트 허용")
        return False

if __name__ == "__main__":
    test_x11_display()