// Vehicle Dashboard JavaScript
class VehicleDashboard {
    constructor() {
        this.currentData = {
            rpmValue: 0,
            speedValue: 0,
            gear: 'D',
            fuelLevel: 75,
            engineTemp: 90,
            batteryLevel: 85,
            connectionStatus: 'Connected'
        };
        
        this.animatedValues = {
            rpm: 0,
            speed: 0,
            fuel: 75,
            temp: 90,
            battery: 85
        };
        
        this.isInitialized = false;
        this.updateInterval = null;
        this.animationInterval = null;
        
        this.init();
    }
    
    init() {
        this.updateClock();
        this.startClockTimer();
        this.startDataFetching();
        this.startAnimationLoop();
        
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
            fuelLevel: 75 + Math.sin(time * 0.05) * 10,
            engineTemp: 90 + Math.sin(time * 0.08) * 5,
            batteryLevel: 85 + Math.sin(time * 0.03) * 8,
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
        }, 500); // Update every 500ms for smooth data
    }
    
    startAnimationLoop() {
        this.animationInterval = setInterval(() => {
            this.animateValues();
        }, 16); // ~60 FPS
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
        
        // Animate other values
        this.animatedValues.fuel = lerp(
            this.animatedValues.fuel, 
            this.currentData.fuelLevel, 
            animationSpeed * 0.5
        );
        
        this.animatedValues.temp = lerp(
            this.animatedValues.temp, 
            this.currentData.engineTemp, 
            animationSpeed * 0.5
        );
        
        this.animatedValues.battery = lerp(
            this.animatedValues.battery, 
            this.currentData.batteryLevel, 
            animationSpeed * 0.5
        );
        
        // Update UI
        this.updateGauges();
        this.updateStatusValues();
    }
    
    updateGauges() {
        // SVG circle with radius 85 has circumference = 2 * PI * 85 ≈ 534
        const circumference = 534;
        
        // Update RPM gauge (max 2000)
        const rpmPercent = Math.min(this.animatedValues.rpm / 2000, 1);
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
        
        // Update Speed gauge (max 20 km/h)
        const speedPercent = Math.min(this.animatedValues.speed / 20, 1);
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
        
        // Debug logging
        if (window.DEBUG_GAUGES || true) { // Force debug for now
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
        // Update fuel level
        document.getElementById('fuelValue').textContent = 
            Math.round(this.animatedValues.fuel) + '%';
        
        // Update temperature
        document.getElementById('tempValue').textContent = 
            Math.round(this.animatedValues.temp) + '°C';
        
        // Update battery level
        document.getElementById('batteryValue').textContent = 
            Math.round(this.animatedValues.battery) + '%';
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

// Camera management
class CameraManager {
    constructor() {
        this.cameraImg = document.getElementById('cameraStream');
        this.retryCount = 0;
        this.maxRetries = 5;
        this.retryDelay = 2000;
        
        this.init();
    }
    
    init() {
        // Try to load camera stream
        this.loadCameraStream();
        
        // Set up error handling
        this.cameraImg.addEventListener('error', () => {
            this.handleCameraError();
        });
        
        this.cameraImg.addEventListener('load', () => {
            this.handleCameraSuccess();
        });
        
        // Periodically check camera status
        setInterval(() => {
            this.checkCameraStatus();
        }, 10000); // Check every 10 seconds
    }
    
    loadCameraStream() {
        // Add timestamp to prevent caching
        const timestamp = new Date().getTime();
        this.cameraImg.src = `/video_feed?t=${timestamp}`;
    }
    
    handleCameraSuccess() {
        console.log('Camera stream loaded successfully');
        this.retryCount = 0; // Reset retry count on success
    }
    
    handleCameraError() {
        console.warn('Camera stream error, attempting retry...');
        this.retryCount++;
        
        if (this.retryCount <= this.maxRetries) {
            setTimeout(() => {
                this.loadCameraStream();
            }, this.retryDelay);
        } else {
            console.error('Camera stream failed after maximum retries');
            this.showCameraError();
        }
    }
    
    showCameraError() {
        const cameraView = document.getElementById('cameraView');
        cameraView.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #1e293b; color: #94a3b8; font-size: 1.2rem;">
                <div style="text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📹</div>
                    <div>Camera Unavailable</div>
                    <div style="font-size: 0.9rem; margin-top: 0.5rem;">Retrying connection...</div>
                </div>
            </div>
        `;
        
        // Reset retry count and try again after a longer delay
        setTimeout(() => {
            this.retryCount = 0;
            this.loadCameraStream();
        }, 5000);
    }
    
    checkCameraStatus() {
        // Try to reload if needed
        if (this.retryCount > 0 && this.retryCount <= this.maxRetries) {
            this.loadCameraStream();
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚗 Vehicle Dashboard Loading...');
    
    // Initialize dashboard
    const dashboard = new VehicleDashboard();
    
    // Make dashboard globally accessible for debugging
    window.dashboard = dashboard;
    
    // Initialize camera
    const cameraManager = new CameraManager();
    
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
    window.DEBUG_GAUGES = true;
    
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