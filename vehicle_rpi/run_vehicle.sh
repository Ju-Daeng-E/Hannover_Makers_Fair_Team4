#!/bin/bash
# RC Car Vehicle Startup Script
# 차량 시작 스크립트

echo "🚗 Starting RC Car Vehicle System..."
echo "=" * 50

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root for GPIO access
if [ "$EUID" -ne 0 ]; then
    print_warning "Not running as root - GPIO access may be limited"
    print_warning "For full GPIO access, run with: sudo ./run_vehicle.sh"
else
    print_status "Running with root privileges for GPIO access"
fi

# Check Python dependencies
print_status "Checking Python dependencies..."
if [ -f "requirements.txt" ]; then
    # Check if we need to handle numpy compatibility
    if python3 -c "import simplejpeg" 2>/dev/null; then
        print_status "Using system packages for camera compatibility"
    else
        print_status "Installing minimal dependencies..."
        # Only install what's not available in system packages
        python3 -m pip install --user --break-system-packages opencv-python pyyaml 2>/dev/null || {
            print_warning "Some dependencies may not be fully installed"
        }
    fi
else
    print_warning "requirements.txt not found - using system packages"
fi

# Note: Using system packages for PiCamera2/numpy compatibility

# Check camera availability
print_status "Checking camera availability..."
CAMERA_FOUND=false

# Check for Raspberry Pi camera
if [ -e /dev/video0 ]; then
    print_status "Camera detected at /dev/video0"
    CAMERA_FOUND=true
elif command -v vcgencmd &> /dev/null && vcgencmd get_camera | grep -q "detected=1"; then
    print_status "Raspberry Pi camera detected"
    CAMERA_FOUND=true
fi

# Check for USB cameras
for i in {0..15}; do
    if [ -e "/dev/video$i" ]; then
        print_status "USB camera detected at /dev/video$i"
        CAMERA_FOUND=true
        break
    fi
done

if [ "$CAMERA_FOUND" = false ]; then
    print_warning "No camera detected - streaming will be disabled"
fi

# Enable camera interface (if Raspberry Pi)
if command -v raspi-config &> /dev/null; then
    print_status "Enabling camera interface..."
    raspi-config nonint do_camera 0 2>/dev/null || print_warning "Could not enable camera interface"
fi

# Check network configuration
print_status "Network configuration:"
IPS=$(hostname -I)
for ip in $IPS; do
    if [[ $ip =~ ^192\.168\. ]] || [[ $ip =~ ^10\. ]] || [[ $ip =~ ^172\. ]]; then
        print_status "Vehicle IP: $ip"
        print_status "🌐 Camera stream: http://$ip:8080"
        print_status "🎮 Control port: 8888"
        break
    fi
done

# Additional network info for debugging
if [ "$EUID" -eq 0 ]; then
    print_status "Root access confirmed - all features available"
else
    print_warning "Limited user access - some features may not work"
fi

# Create log directory with proper permissions
mkdir -p logs
if [ "$EUID" -eq 0 ]; then
    # If running as root, ensure pi user can access logs
    chown pi:pi logs 2>/dev/null || print_warning "Could not set log directory ownership"
    chmod 755 logs
    print_status "Log directory created with pi user access"
else
    print_status "Log directory created"
fi

# Set display environment for pygame (if available)
if [ -z "$DISPLAY" ] && [ -n "$XDG_SESSION_TYPE" ]; then
    export DISPLAY=:0
fi

# Function to handle cleanup
cleanup() {
    print_status "Cleaning up..."
    # Kill any camera processes
    pkill -f "camera_stream.py" 2>/dev/null || true
    print_status "Vehicle stopped"
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGINT SIGTERM

# Check if camera streaming should run separately
if [ "$1" = "--camera-only" ]; then
    print_status "Starting camera streaming only..."
    # Set environment for camera streaming
    export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
    export PYTHONNOUSERSITE=1
    /usr/bin/python3 camera_stream.py --port 8080
    cleanup
fi

# Run vehicle with error handling
print_status "Starting vehicle main program..."
print_status "Waiting for controller connection..."
print_status "Press Ctrl+C to stop"
echo "=" * 50

# Set PYTHONPATH to ensure system packages are used first
export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"

# Unset any user site-packages to avoid numpy conflicts
export PYTHONNOUSERSITE=1

# Use system Python to avoid numpy compatibility issues
print_status "Starting vehicle with system Python environment..."

# Check if user wants camera only mode
if [ "$1" = "--camera-speed" ]; then
    print_status "Starting camera streaming with speed sensor..."
    /usr/bin/python3 camera_stream.py --port 8080
else
    # Start vehicle main program (which includes camera streaming)
    /usr/bin/python3 vehicle_main.py
fi

# Cleanup on exit
cleanup