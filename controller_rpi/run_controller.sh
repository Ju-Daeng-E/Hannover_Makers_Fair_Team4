#!/bin/bash
# RC Car Controller Startup Script
# 컨트롤러 시작 스크립트

echo "🎮 Starting RC Car Controller System..."
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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

# Setup CAN interface
print_status "Setting up CAN interface..."
if ! command -v cansend &> /dev/null; then
    print_warning "CAN utilities not found. Installing..."
    apt-get update
    apt-get install -y can-utils
fi

# Configure CAN interfaces (both can0 and can1)
configure_can_interface() {
    local interface=$1
    if ip link show $interface &> /dev/null; then
        print_status "Configuring CAN interface $interface..."
        ip link set $interface down 2>/dev/null || true
        ip link set $interface type can bitrate 500000
        ip link set $interface up
        print_status "CAN interface $interface ready"
        return 0
    else
        print_warning "CAN interface $interface not found"
        return 1
    fi
}

# Try to configure both CAN interfaces
can0_ok=false
can1_ok=false

if configure_can_interface can0; then
    can0_ok=true
fi

if configure_can_interface can1; then
    can1_ok=true
fi

if [ "$can1_ok" = true ]; then
    print_status "BMW gear control will use can1"
elif [ "$can0_ok" = true ]; then
    print_status "BMW gear control will use can0 as fallback"
else
    print_warning "No CAN interfaces available - BMW gear control disabled"
fi

# Check Python dependencies
print_status "Checking Python dependencies..."
if [ -f "requirements.txt" ]; then
    source venv/bin/activate
    pip install -r requirements.txt
else
    print_warning "requirements.txt not found - installing basic dependencies"
    source venv/bin/activate
    pip install pyyaml
fi

# Check gamepad connection
print_status "Checking for gamepad..."
if [ -e /dev/input/js0 ]; then
    print_status "Gamepad detected at /dev/input/js0"
else
    print_warning "No gamepad detected - system will use mock gamepad"
fi

# Create log directory
mkdir -p logs

# Set environment variables
export PYTHONPATH="/home/pi/controller_rpi:$PYTHONPATH"

# Function to handle cleanup
cleanup() {
    print_status "Cleaning up..."
    # Stop CAN interface
    ip link set can0 down 2>/dev/null || true
    print_status "Controller stopped"
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGINT SIGTERM

# Run controller with error handling
print_status "Starting controller main program..."
print_status "Press Ctrl+C to stop"
echo "=" * 50

source venv/bin/activate && python controller_main.py

# Cleanup on exit
cleanup