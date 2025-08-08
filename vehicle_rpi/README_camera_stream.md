# 🎥 RC Car Camera Stream

Raspberry Pi camera streaming server for the RC car project.

## ⚠️ Important: Camera Setup

The camera requires **PiCamera2** which must be installed as a system package:

```bash
sudo apt update && sudo apt install -y python3-picamera2
```

## 🚀 Quick Start

Use the provided shell script wrapper:

```bash
./run_camera_stream.sh
```

This script uses system Python to access PiCamera2 and starts the camera stream server.

## 🔧 Manual Usage

If you need to run with system Python directly:

```bash
/usr/bin/python3 camera_stream.py [options]
```

### Options

- `--port PORT`: Streaming port (default: 8080)  
- `--width WIDTH`: Frame width (default: 640)
- `--height HEIGHT`: Frame height (default: 480)
- `--fps FPS`: Frame rate (default: 30)

## 🌐 Accessing the Stream

Once running, access the camera stream at:

- **Web Interface**: http://[vehicle-ip]:8080
- **Direct Stream**: http://[vehicle-ip]:8080/video_feed  
- **Status API**: http://[vehicle-ip]:8080/status

## 🛠️ Troubleshooting

### Camera Not Detected

1. Check camera connection:
   ```bash
   vcgencmd get_camera
   ```

2. List cameras with libcamera:
   ```bash
   libcamera-hello --list-cameras
   ```

3. Verify camera interface is enabled:
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options > Camera > Enable
   ```

### Import Errors

- **PiCamera2 not found**: Install system package with `sudo apt install python3-picamera2`
- **Numpy compatibility issues**: Use system Python (`/usr/bin/python3`) instead of virtual environment

### Performance Issues

- Lower resolution: `./run_camera_stream.sh --width 320 --height 240`
- Reduce frame rate: `./run_camera_stream.sh --fps 15`
- Check CPU usage: `htop`

## 📱 Mobile Access

The web interface is mobile-responsive and works well on smartphones and tablets for remote monitoring.

## 🔗 Integration

This camera stream can be integrated into:
- OBS Studio (use the /video_feed URL)
- VLC Media Player  
- Custom applications via HTTP streaming
- Main vehicle controller system

## ⚡ Performance Notes

- OV5647 camera module detected
- Default resolution: 640x480 @ 30fps
- MJPEG streaming over HTTP
- Real-time overlay with timestamp and system info