#!/bin/bash

# 라즈베리파이 카메라 활성화 스크립트

echo "📷 라즈베리파이 카메라 활성화 설정"
echo "=================================================="

# 현재 카메라 상태 확인
echo "🔍 현재 카메라 상태:"
vcgencmd get_camera

# config.txt 백업
sudo cp /boot/config.txt /boot/config.txt.backup
echo "✅ /boot/config.txt 백업 완료"

# 카메라 관련 설정 추가/수정
echo ""
echo "⚙️ 카메라 설정 적용 중..."

# 기존 설정 제거 (있다면)
sudo sed -i '/^start_x=/d' /boot/config.txt
sudo sed -i '/^gpu_mem=/d' /boot/config.txt

# 새 설정 추가
echo "start_x=1" | sudo tee -a /boot/config.txt
echo "gpu_mem=128" | sudo tee -a /boot/config.txt

echo "✅ 카메라 설정이 /boot/config.txt에 추가되었습니다"

# 카메라 모듈 로드 확인
echo ""
echo "🔧 카메라 모듈 설정..."

# 카메라 모듈을 부트 시 자동 로드
echo "bcm2835-v4l2" | sudo tee -a /etc/modules

echo "✅ 카메라 모듈 설정 완료"

# 사용자를 video 그룹에 추가
sudo usermod -a -G video $USER
echo "✅ 사용자를 video 그룹에 추가했습니다"

# 권한 설정
sudo chmod 666 /dev/video* 2>/dev/null || true

echo ""
echo "🎯 설정 완료!"
echo "=================================================="
echo "⚠️  변경사항을 적용하려면 시스템을 재부팅해야 합니다:"
echo ""
echo "   sudo reboot"
echo ""
echo "재부팅 후 다음 명령어로 카메라 상태를 확인하세요:"
echo "   vcgencmd get_camera"
echo ""
echo "카메라가 활성화되면 다음과 같이 표시됩니다:"
echo "   supported=1 detected=1"
echo "=================================================="