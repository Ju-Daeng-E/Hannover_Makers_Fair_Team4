// Vehicle Dashboard JavaScript
class VehicleDashboard {
    constructor() {
        this.currentData = {
            rpmValue: 0,
            speedValue: 0,
            gear: 'D',
            batteryLevel: 0,
            connectionStatus: 'Connected'
        };
        
        this.animatedValues = {
            rpm: 0,
            speed: 0,
            battery: 0
        };
        
        this.isInitialized = false;
        this.updateInterval = null;
        this.animationInterval = null;
        
        // WebSocket 비디오 스트리밍
        this.websocket = null;
        this.websocketPort = 8765;
        this.videoConnected = false;
        
        this.init();
    }
    
    init() {
        this.updateClock();
        this.startClockTimer();
        this.startDataFetching();
        this.startAnimationLoop();
        this.initVideoStream();
        
        // Wait a bit before showing animations
        setTimeout(() => {
            this.isInitialized = true;
        }, 100);
    }
    
    updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        const dateString = now.toLocaleDateString();
        
        document.getElementById('timeDisplay').textContent = timeString;
        document.getElementById('dateDisplay').textContent = dateString;
    }
    
    startClockTimer() {
        setInterval(() => {
            this.updateClock();
        }, 1000);
    }
    
    async fetchVehicleData() {
        try {
            console.log('🔄 Fetching vehicle data...');
            const response = await fetch('/api/vehicle-data');
            if (response.ok) {
                const data = await response.json();
                console.log('📡 API Response:', data);
                this.updateVehicleData(data);
            } else {
                console.warn('⚠️ Failed to fetch vehicle data, status:', response.status);
                // Use simulation data if API fails
                this.updateVehicleData(this.generateSimulationData());
            }
        } catch (error) {
            console.error('❌ Error fetching vehicle data:', error);
            // Use simulation data on error
            this.updateVehicleData(this.generateSimulationData());
        }
    }
    
    generateSimulationData() {
        // Generate realistic simulation data
        const time = Date.now() / 1000;
        const rpmBase = 800 + Math.sin(time * 0.1) * 200;
        const speedBase = 10 + Math.sin(time * 0.15) * 5;
        
        return {
            rpmValue: Math.max(0, Math.round(rpmBase + (Math.random() - 0.5) * 100)),
            speedValue: Math.max(0, Math.round((speedBase + (Math.random() - 0.5) * 2) * 10) / 10),
            gear: ['D', 'R', 'N', 'P'][Math.floor(Math.random() * 4)],
            batteryLevel: 0, // Will be handled by real INA sensor
            connectionStatus: 'Connected'
        };
    }
    
    updateVehicleData(data) {
        this.currentData = { ...this.currentData, ...data };
        
        // Update gear immediately (no animation needed)
        document.getElementById('gearValue').textContent = this.currentData.gear;
        
        // Update system status based on connection and sensor status
        const systemValue = document.getElementById('systemValue');
        const sensorStatus = data.sensorStatus || 'unknown';
        const connectionStatus = this.currentData.connectionStatus;
        
        if (connectionStatus === 'Connected' && sensorStatus === 'active') {
            systemValue.textContent = 'OK';
            systemValue.className = 'status-value system-value';
            systemValue.style.color = '#4ade80'; // Green
        } else if (sensorStatus === 'stale') {
            systemValue.textContent = 'STALE';
            systemValue.className = 'status-value';
            systemValue.style.color = '#facc15'; // Yellow
        } else if (sensorStatus === 'unavailable') {
            systemValue.textContent = 'NO SENSOR';
            systemValue.className = 'status-value';
            systemValue.style.color = '#ef4444'; // Red
        } else {
            systemValue.textContent = 'ERROR';
            systemValue.className = 'status-value';
            systemValue.style.color = '#ef4444'; // Red
        }
        
        // Debug logging for sensor data
        if (window.DEBUG_GAUGES && data.sensorStatus) {
            console.log('Sensor Data:', {
                rpm: data.rpmValue,
                speed: data.speedValue,
                sensorStatus: data.sensorStatus,
                dataAge: data.dataAge,
                gear: data.gear
            });
        }
    }
    
    startDataFetching() {
        this.fetchVehicleData(); // Initial fetch
        this.updateInterval = setInterval(() => {
            this.fetchVehicleData();
        }, 200); // Update every 200ms for faster response
    }
    
    startAnimationLoop() {
        this.animationInterval = setInterval(() => {
            this.animateValues();
        }, 33); // ~30 FPS (reduced from 60 FPS)
    }
    
    animateValues() {
        if (!this.isInitialized) return;
        
        const lerp = (start, end, factor) => {
            return start + (end - start) * factor;
        };
        
        const animationSpeed = 0.1; // Adjust for faster/slower animations
        
        // Animate RPM
        this.animatedValues.rpm = lerp(
            this.animatedValues.rpm, 
            this.currentData.rpmValue, 
            animationSpeed
        );
        
        // Animate Speed  
        this.animatedValues.speed = lerp(
            this.animatedValues.speed, 
            this.currentData.speedValue, 
            animationSpeed
        );
        
        // Animate battery value
        this.animatedValues.battery = lerp(
            this.animatedValues.battery, 
            this.currentData.batteryLevel, 
            animationSpeed * 0.3  // Slower animation for battery
        );
        
        // Update UI
        this.updateGauges();
        this.updateStatusValues();
    }
    
    updateGauges() {
        // SVG circle with radius 85 has circumference = 2 * PI * 85 ≈ 534
        const circumference = 534;
        
        // Update RPM gauge (max 300)
        const rpmPercent = Math.min(this.animatedValues.rpm / 300, 1);
        const rpmOffset = circumference - (rpmPercent * circumference);
        
        const rpmElement = document.getElementById('rpmProgress');
        if (rpmElement) {
            rpmElement.style.strokeDasharray = `${circumference} ${circumference}`;
            rpmElement.style.strokeDashoffset = `${rpmOffset}`;
        }
        
        const rpmValueElement = document.getElementById('rpmValue');
        if (rpmValueElement) {
            rpmValueElement.textContent = Math.round(this.animatedValues.rpm);
        }
        
        // Update Speed gauge (max 5 km/h)
        const speedPercent = Math.min(this.animatedValues.speed / 5, 1);
        const speedOffset = circumference - (speedPercent * circumference);
        
        const speedElement = document.getElementById('speedProgress');
        if (speedElement) {
            speedElement.style.strokeDasharray = `${circumference} ${circumference}`;
            speedElement.style.strokeDashoffset = `${speedOffset}`;
        }
        
        const speedValueElement = document.getElementById('speedValue');
        if (speedValueElement) {
            speedValueElement.textContent = this.animatedValues.speed.toFixed(1);
        }
        
        // Debug logging (only when enabled)
        if (window.DEBUG_GAUGES) {
            console.log('🎛️ Gauge Update:', {
                rpm: this.animatedValues.rpm,
                rpmPercent: (rpmPercent * 100).toFixed(1) + '%',
                rpmOffset: rpmOffset.toFixed(1),
                speed: this.animatedValues.speed,
                speedPercent: (speedPercent * 100).toFixed(1) + '%',
                speedOffset: speedOffset.toFixed(1),
                circumference: circumference,
                rpmElement: !!rpmElement,
                speedElement: !!speedElement
            });
        }
    }
    
    updateStatusValues() {
        // Update battery level with proper status handling
        const batteryElement = document.getElementById('batteryValue');
        const batteryStatus = this.currentData.batteryStatus || 'unknown';
        
        if (batteryStatus === 'unavailable' || batteryStatus === 'error') {
            batteryElement.textContent = 'N/A';
            batteryElement.style.color = '#ef4444'; // Red
        } else if (batteryStatus === 'ok' && this.animatedValues.battery >= 0) {
            const batteryPercent = Math.round(this.animatedValues.battery);
            batteryElement.textContent = batteryPercent + '%';
            
            // Color coding based on battery level
            if (batteryPercent > 50) {
                batteryElement.style.color = '#4ade80'; // Green
            } else if (batteryPercent > 20) {
                batteryElement.style.color = '#facc15'; // Yellow
            } else {
                batteryElement.style.color = '#ef4444'; // Red
            }
        } else {
            batteryElement.textContent = '---%';
            batteryElement.style.color = '#94a3b8'; // Gray
        }
    }
    
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.animationInterval) {
            clearInterval(this.animationInterval);
        }
    }
}

// WebSocket 비디오 스트림 메서드들을 VehicleDashboard 클래스에 추가
VehicleDashboard.prototype.initVideoStream = function() {
    console.log('🎥 WebSocket 비디오 스트림 초기화...');
    this.websocketPort = 8765;
    this.videoConnected = false;
    this.firstFrameReceived = false;
    this.connectVideoWebSocket();
    this.startKeepAliveTimer();
};

VehicleDashboard.prototype.connectVideoWebSocket = function() {
    try {
        const host = window.location.hostname;
        const wsUrl = `ws://${host}:${this.websocketPort}`;
        console.log(`🔌 WebSocket 연결 시도: ${wsUrl}`);
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = (event) => {
            console.log('✅ WebSocket 비디오 연결 성공');
            this.videoConnected = true;
            this.updateVideoStatus('연결됨');
        };
        
        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleVideoMessage(data);
            } catch (error) {
                console.error('❌ WebSocket 메시지 파싱 오류:', error);
            }
        };
        
        this.websocket.onerror = (error) => {
            console.error('❌ WebSocket 오류:', error);
            this.videoConnected = false;
            this.updateVideoStatus('오류');
        };
        
        this.websocket.onclose = (event) => {
            console.log('🔌 WebSocket 연결 종료:', event.code, event.reason);
            this.videoConnected = false;
            this.updateVideoStatus('연결 끊김');
            
            // 3초 후 재연결 시도
            setTimeout(() => {
                if (!this.videoConnected) {
                    console.log('🔄 WebSocket 재연결 시도...');
                    this.connectVideoWebSocket();
                }
            }, 3000);
        };
        
    } catch (error) {
        console.error('❌ WebSocket 연결 실패:', error);
        this.updateVideoStatus('연결 실패');
    }
};

VehicleDashboard.prototype.handleVideoMessage = function(data) {
    switch (data.type) {
        case 'connection':
            console.log('📡 연결 상태:', data.status, data.message);
            if (data.status === 'connected') {
                this.updateVideoStatus('스트림 준비');
            }
            break;
            
        case 'video_frame':
            // Base64 이미지 데이터를 카메라 스트림에 표시
            this.updateCameraFrame(data.data);
            break;
            
        case 'pong':
            // Keep-alive 응답
            break;
            
        default:
            console.log('📡 알 수 없는 메시지 타입:', data.type);
    }
};

VehicleDashboard.prototype.updateCameraFrame = function(imageData) {
    const cameraStream = document.getElementById('cameraStream');
    if (cameraStream) {
        cameraStream.src = imageData;
        cameraStream.style.display = 'block';
        
        // 처음 프레임 수신 시 상태 업데이트
        if (!this.firstFrameReceived) {
            this.firstFrameReceived = true;
            this.updateVideoStatus('스트리밍 중');
            console.log('✅ 첫 번째 비디오 프레임 수신');
        }
    }
};

VehicleDashboard.prototype.updateVideoStatus = function(status) {
    // 비디오 상태를 UI에 표시 (필요시 추가 구현)
    console.log(`📹 비디오 상태: ${status}`);
};

VehicleDashboard.prototype.sendKeepAlive = function() {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({
            type: 'ping',
            timestamp: Date.now()
        }));
    }
};

// Keep-alive 타이머 (30초마다)
VehicleDashboard.prototype.startKeepAliveTimer = function() {
    setInterval(() => {
        this.sendKeepAlive();
    }, 30000);
};

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚗 Vehicle Dashboard Loading...');
    
    // Initialize dashboard
    const dashboard = new VehicleDashboard();
    
    // Make dashboard globally accessible for debugging
    window.dashboard = dashboard;
    
    // WebSocket video is now integrated into the dashboard class
    
    // Handle page visibility for performance
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            console.log('Dashboard hidden - reducing update frequency');
            // Could reduce update frequency here
        } else {
            console.log('Dashboard visible - resuming normal updates');
            // Resume normal updates
        }
    });
    
    // Handle errors
    window.addEventListener('error', (event) => {
        console.error('Dashboard error:', event.error);
    });
    
    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        dashboard.destroy();
    });
    
    console.log('✅ Vehicle Dashboard Initialized');
    
    // Enable debug mode for gauges
    window.DEBUG_GAUGES = false;
    
    // Add manual test function for gauges
    window.testGauges = function(rpm = 1000, speed = 10) {
        console.log(`🧪 Testing gauges: RPM=${rpm}, Speed=${speed}`);
        const dashboard = window.dashboard;
        if (dashboard) {
            dashboard.currentData.rpmValue = rpm;
            dashboard.currentData.speedValue = speed;
            dashboard.animatedValues.rpm = rpm;
            dashboard.animatedValues.speed = speed;
            dashboard.updateGauges();
            console.log('✅ Gauge test completed');
        } else {
            console.error('❌ Dashboard not found');
        }
    };
    
    // Add immediate gauge test with current API data
    window.forceAPIUpdate = function() {
        console.log('🔧 Forcing API update...');
        const dashboard = window.dashboard;
        if (dashboard) {
            dashboard.fetchVehicleData();
        }
    };
    
    console.log('🔧 Debug mode enabled - use window.testGauges(rpm, speed) to test');
});

// Global error handler
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    event.preventDefault(); // Prevent the default behavior
});

// Debug information
console.log('🔧 Debug mode enabled for GPIO sensor monitoring');

// Add debug info to console
setInterval(() => {
    const dashboard = window.dashboard;
    if (dashboard && window.DEBUG_GAUGES) {
        console.log('📊 Real-time Sensor Data:', {
            rpm: dashboard.currentData.rpmValue,
            speed: dashboard.currentData.speedValue,
            sensorStatus: dashboard.currentData.sensorStatus,
            dataAge: dashboard.currentData.dataAge,
            connectionStatus: dashboard.currentData.connectionStatus,
            gear: dashboard.currentData.gear
        });
        console.log('🎛️ Animated Gauge Values:', {
            rpmGauge: Math.round(dashboard.animatedValues.rpm),
            speedGauge: dashboard.animatedValues.speed.toFixed(1)
        });
    }
}, 3000); // Every 3 seconds