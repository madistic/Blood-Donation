/**
 * Hospital Location & Notification System
 * Handles geolocation, hospital mapping, and notification requests
 */

class HospitalLocationManager {
    constructor() {
        this.userLocation = null;
        this.map = null;
        this.hospitals = [];
        this.markers = [];
        this.isLoading = false;
        this.notificationInProgress = false;
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    init() {
        console.log('Initializing Hospital Location Manager');
        this.setupEventListeners();
        this.initializeMap();
    }
    
    setupEventListeners() {
        // My Location button
        const locationBtn = document.getElementById('getLocationBtn');
        if (locationBtn) {
            locationBtn.addEventListener('click', () => this.getCurrentLocation());
        }
        
        // Notification button
        const notifyBtn = document.getElementById('notifyHospitalsBtn');
        if (notifyBtn) {
            notifyBtn.addEventListener('click', () => this.requestNotifications());
        }
        
        // Radius selector
        const radiusSelect = document.getElementById('searchRadius');
        if (radiusSelect) {
            radiusSelect.addEventListener('change', () => {
                if (this.userLocation) {
                    this.findNearbyHospitals();
                }
            });
        }
    }
    
    initializeMap() {
        // Initialize Leaflet map
        const mapContainer = document.getElementById('hospitalMap');
        if (!mapContainer) return;
        
        this.map = L.map('hospitalMap').setView([20.5937, 78.9629], 6); // Center of India
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(this.map);
        
        // Add map controls
        this.map.addControl(new L.Control.Scale());
    }
    
    getCurrentLocation() {
        if (this.isLoading) return;
        
        const locationBtn = document.getElementById('getLocationBtn');
        const statusDiv = document.getElementById('locationStatus');
        
        if (!navigator.geolocation) {
            this.showError('Geolocation is not supported by this browser');
            return;
        }
        
        this.isLoading = true;
        this.updateLocationButton('Getting location...', true);
        
        const options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 300000 // 5 minutes
        };
        
        navigator.geolocation.getCurrentPosition(
            (position) => this.onLocationSuccess(position),
            (error) => this.onLocationError(error),
            options
        );
    }
    
    onLocationSuccess(position) {
        this.userLocation = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy
        };
        
        console.log('Location acquired:', this.userLocation);
        
        // Update UI
        this.updateLocationButton('Location found!', false);
        this.showLocationStatus(`Location acquired (±${Math.round(this.userLocation.accuracy)}m accuracy)`);
        
        // Add user marker to map
        this.addUserMarker();
        
        // Find nearby hospitals
        this.findNearbyHospitals();
        
        this.isLoading = false;
    }
    
    onLocationError(error) {
        this.isLoading = false;
        this.updateLocationButton('Get My Location', false);
        
        let errorMessage = 'Unable to get your location';
        switch (error.code) {
            case error.PERMISSION_DENIED:
                errorMessage = 'Location access denied. Please enable location permissions.';
                break;
            case error.POSITION_UNAVAILABLE:
                errorMessage = 'Location information is unavailable.';
                break;
            case error.TIMEOUT:
                errorMessage = 'Location request timed out. Please try again.';
                break;
        }
        
        this.showError(errorMessage);
        console.error('Geolocation error:', error);
    }
    
    addUserMarker() {
        if (!this.map || !this.userLocation) return;
        
        // Remove existing user marker
        if (this.userMarker) {
            this.map.removeLayer(this.userMarker);
        }
        
        // Add new user marker
        this.userMarker = L.marker([this.userLocation.latitude, this.userLocation.longitude], {
            icon: L.divIcon({
                className: 'user-location-marker',
                html: '<div style="background: #3b82f6; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3);"></div>',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            })
        }).addTo(this.map);
        
        this.userMarker.bindPopup('📍 Your Location').openPopup();
        
        // Center map on user location
        this.map.setView([this.userLocation.latitude, this.userLocation.longitude], 12);
    }
    
    async findNearbyHospitals() {
        if (!this.userLocation) return;
        
        const radius = document.getElementById('searchRadius')?.value || 10;
        const loadingDiv = document.getElementById('hospitalsLoading');
        const resultsDiv = document.getElementById('hospitalsResults');
        
        try {
            // Show loading state
            if (loadingDiv) loadingDiv.style.display = 'block';
            if (resultsDiv) resultsDiv.style.display = 'none';
            
            // Fetch nearby hospitals from API
            const response = await fetch(
                `/api/nearby-hospitals/?lat=${this.userLocation.latitude}&lng=${this.userLocation.longitude}&radius_km=${radius}`,
                {
                    headers: {
                        'Authorization': `Bearer ${this.getAuthToken()}`,
                        'Content-Type': 'application/json',
                    }
                }
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.hospitals = data.hospitals || [];
            
            console.log(`Found ${this.hospitals.length} hospitals within ${radius}km`);
            
            // Update UI
            this.displayHospitals();
            this.addHospitalMarkers();
            this.enableNotificationButton();
            
        } catch (error) {
            console.error('Error fetching hospitals:', error);
            this.showError('Failed to load nearby hospitals. Please try again.');
        } finally {
            if (loadingDiv) loadingDiv.style.display = 'none';
            if (resultsDiv) resultsDiv.style.display = 'block';
        }
    }
    
    displayHospitals() {
        const container = document.getElementById('hospitalsList');
        if (!container) return;
        
        if (this.hospitals.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-hospital fa-3x mb-3" style="color: #d1d5db;"></i>
                    <h4>No Hospitals Found</h4>
                    <p>No partner hospitals found within the selected radius. Try increasing the search radius.</p>
                </div>
            `;
            return;
        }
        
        const hospitalsHTML = this.hospitals.map(hospital => `
            <div class="hospital-card" data-hospital-id="${hospital.id}">
                <div class="hospital-header">
                    <div class="hospital-name">${hospital.name}</div>
                    <div class="distance-badge">${hospital.distance} km</div>
                </div>
                
                <div class="hospital-details">
                    <div class="contact-info">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${hospital.address}, ${hospital.city}, ${hospital.state}</span>
                    </div>
                    
                    <div class="contact-info">
                        <i class="fas fa-phone"></i>
                        <span><a href="tel:${hospital.contact_phone}">${hospital.contact_phone}</a></span>
                    </div>
                    
                    <div class="contact-info">
                        <i class="fas fa-envelope"></i>
                        <span><a href="mailto:${hospital.contact_email}">${hospital.contact_email}</a></span>
                    </div>
                    
                    <div class="emergency-contact">
                        <i class="fas fa-ambulance"></i>
                        <span><strong>Emergency:</strong> <a href="tel:${hospital.emergency_contact}">${hospital.emergency_contact}</a></span>
                    </div>
                    
                    <div class="blood-stock-summary">
                        <h6><i class="fas fa-tint"></i> Blood Stock:</h6>
                        <div class="stock-badges">
                            ${Object.entries(hospital.blood_stock).map(([type, info]) => 
                                `<span class="stock-badge ${info.available ? 'available' : 'unavailable'}">${type}: ${info.units}</span>`
                            ).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = hospitalsHTML;
    }
    
    addHospitalMarkers() {
        if (!this.map) return;
        
        // Clear existing markers
        this.markers.forEach(marker => this.map.removeLayer(marker));
        this.markers = [];
        
        // Add hospital markers
        this.hospitals.forEach(hospital => {
            const marker = L.marker([hospital.latitude, hospital.longitude], {
                icon: L.divIcon({
                    className: 'hospital-marker',
                    html: '<div style="background: #dc2626; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3);"><i class="fas fa-hospital" style="font-size: 12px;"></i></div>',
                    iconSize: [30, 30],
                    iconAnchor: [15, 15]
                })
            }).addTo(this.map);
            
            // Create popup content
            const stockSummary = Object.entries(hospital.blood_stock)
                .filter(([type, info]) => info.available)
                .map(([type, info]) => `${type}: ${info.units}`)
                .join(', ') || 'No stock available';
            
            marker.bindPopup(`
                <div style="min-width: 200px;">
                    <h6 style="margin: 0 0 10px 0; color: #dc2626;">${hospital.name}</h6>
                    <p style="margin: 5px 0; font-size: 12px;"><strong>Distance:</strong> ${hospital.distance} km</p>
                    <p style="margin: 5px 0; font-size: 12px;"><strong>Phone:</strong> ${hospital.contact_phone}</p>
                    <p style="margin: 5px 0; font-size: 12px;"><strong>Emergency:</strong> ${hospital.emergency_contact}</p>
                    <p style="margin: 5px 0; font-size: 12px;"><strong>Stock:</strong> ${stockSummary}</p>
                    <button onclick="window.open('tel:${hospital.emergency_contact}')" style="background: #dc2626; color: white; border: none; padding: 5px 10px; border-radius: 5px; margin-top: 5px; cursor: pointer;">
                        <i class="fas fa-phone"></i> Call Emergency
                    </button>
                </div>
            `);
            
            this.markers.push(marker);
        });
        
        // Fit map to show all markers
        if (this.hospitals.length > 0) {
            const group = new L.featureGroup([this.userMarker, ...this.markers]);
            this.map.fitBounds(group.getBounds().pad(0.1));
        }
    }
    
    enableNotificationButton() {
        const notifyBtn = document.getElementById('notifyHospitalsBtn');
        if (notifyBtn && this.hospitals.length > 0) {
            notifyBtn.disabled = false;
            notifyBtn.innerHTML = '<i class="fas fa-bell"></i> Send SMS & Email Notifications';
        }
    }
    
    async requestNotifications() {
        if (this.notificationInProgress || !this.userLocation) return;
        
        const notifyBtn = document.getElementById('notifyHospitalsBtn');
        const radius = document.getElementById('searchRadius')?.value || 10;
        
        try {
            this.notificationInProgress = true;
            
            // Update button state
            if (notifyBtn) {
                notifyBtn.disabled = true;
                notifyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending notifications...';
            }
            
            // Send notification request
            const response = await fetch('/api/notify-hospitals/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    user_latitude: this.userLocation.latitude,
                    user_longitude: this.userLocation.longitude,
                    radius_km: parseInt(radius),
                    notification_type: 'BOTH'
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showSuccess(`Notifications queued successfully! You'll receive SMS and email within ${data.estimated_delivery}.`);
                
                // Poll for status updates
                this.pollNotificationStatus(data.job_id);
            } else {
                throw new Error(data.error || 'Failed to send notifications');
            }
            
        } catch (error) {
            console.error('Notification error:', error);
            this.showError(`Failed to send notifications: ${error.message}`);
        } finally {
            this.notificationInProgress = false;
            
            // Reset button after delay
            setTimeout(() => {
                if (notifyBtn) {
                    notifyBtn.disabled = false;
                    notifyBtn.innerHTML = '<i class="fas fa-bell"></i> Send SMS & Email Notifications';
                }
            }, 3000);
        }
    }
    
    async pollNotificationStatus(jobId) {
        const maxPolls = 10;
        let pollCount = 0;
        
        const poll = async () => {
            if (pollCount >= maxPolls) return;
            
            try {
                const response = await fetch(`/api/notification-status/${jobId}/`);
                const data = await response.json();
                
                if (data.status === 'COMPLETED') {
                    this.showSuccess('Notifications sent successfully! Check your SMS and email.');
                    return;
                } else if (data.status === 'FAILED') {
                    this.showError(`Notification failed: ${data.error_message}`);
                    return;
                } else if (data.status === 'PROCESSING') {
                    // Continue polling
                    pollCount++;
                    setTimeout(poll, 2000);
                }
                
            } catch (error) {
                console.error('Status polling error:', error);
            }
        };
        
        // Start polling after 2 seconds
        setTimeout(poll, 2000);
    }
    
    updateLocationButton(text, disabled) {
        const btn = document.getElementById('getLocationBtn');
        if (btn) {
            btn.innerHTML = disabled ? 
                `<i class="fas fa-spinner fa-spin"></i> ${text}` : 
                `<i class="fas fa-crosshairs"></i> ${text}`;
            btn.disabled = disabled;
        }
    }
    
    showLocationStatus(message) {
        const statusDiv = document.getElementById('locationStatus');
        if (statusDiv) {
            statusDiv.innerHTML = `<i class="fas fa-check-circle text-success"></i> ${message}`;
            statusDiv.className = 'alert alert-success';
            statusDiv.style.display = 'block';
        }
    }
    
    showError(message) {
        const statusDiv = document.getElementById('locationStatus');
        if (statusDiv) {
            statusDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
            statusDiv.className = 'alert alert-danger';
            statusDiv.style.display = 'block';
        }
        
        // Also show as toast notification
        this.showToast(message, 'error');
    }
    
    showSuccess(message) {
        const statusDiv = document.getElementById('locationStatus');
        if (statusDiv) {
            statusDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
            statusDiv.className = 'alert alert-success';
            statusDiv.style.display = 'block';
        }
        
        // Also show as toast notification
        this.showToast(message, 'success');
    }
    
    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'}"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: inherit; margin-left: 10px; cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Add styles
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#fee2e2' : '#d1fae5'};
            color: ${type === 'error' ? '#991b1b' : '#065f46'};
            border: 1px solid ${type === 'error' ? '#fecaca' : '#a7f3d0'};
            border-radius: 8px;
            padding: 15px;
            max-width: 400px;
            z-index: 10000;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    getAuthToken() {
        // For session-based auth, we don't need a token
        // This method is here for future token-based auth if needed
        return '';
    }
}

// CSS for toast animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .hospital-card {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        background: white;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    .hospital-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .hospital-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    
    .hospital-name {
        font-size: 18px;
        font-weight: 600;
        color: #dc2626;
    }
    
    .distance-badge {
        background: #10b981;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .contact-info {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
        font-size: 14px;
    }
    
    .contact-info i {
        width: 16px;
        color: #6b7280;
    }
    
    .emergency-contact {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 10px 0;
        padding: 10px;
        background: #fef2f2;
        border-radius: 8px;
        border: 1px solid #fecaca;
        font-size: 14px;
    }
    
    .emergency-contact i {
        color: #dc2626;
    }
    
    .blood-stock-summary h6 {
        margin: 15px 0 10px 0;
        color: #374151;
        font-weight: 600;
    }
    
    .stock-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
    }
    
    .stock-badge {
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }
    
    .stock-badge.available {
        background: #d1fae5;
        color: #065f46;
    }
    
    .stock-badge.unavailable {
        background: #fee2e2;
        color: #991b1b;
    }
    
    .empty-state {
        text-align: center;
        padding: 40px 20px;
        color: #6b7280;
    }
`;
document.head.appendChild(style);

// Initialize the hospital location manager
window.hospitalLocationManager = new HospitalLocationManager();

// Export for global access
window.HospitalLocationManager = HospitalLocationManager;