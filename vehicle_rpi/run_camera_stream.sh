#!/bin/bash

echo "🎥 Raspberry Pi Camera Web Streaming Server 시작..."
echo "=================================================="

# Use system Python to access system PiCamera2
exec /usr/bin/python3 "$(dirname "$0")/camera_stream.py" "$@"