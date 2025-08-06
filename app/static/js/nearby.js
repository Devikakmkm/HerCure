/**
 * Nearby Medical Facilities - Google Maps Integration
 * 
 * This script handles the interactive map and search functionality for finding
 * nearby medical facilities including hospitals, clinics, and pharmacies.
 */

// Global variables
let map;
let markers = [];
let infoWindow;
let userLocation = null;
let placesService;

// Initialize the map when the page loads
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    setupEventListeners();
});

/**
 * Initialize the Google Map
 */
function initMap() {
    // Default to a central location (can be set to user's location later)
    const defaultLocation = { lat: 20.5937, lng: 78.9629 }; // Center of India
    
    map = new google.maps.Map(document.getElementById('map'), {
        center: defaultLocation,
        zoom: 12,
        mapTypeControl: true,
        streetViewControl: false,
        fullscreenControl: true,
        zoomControl: true,
        styles: [
            {
                "featureType": "poi.medical",
                "elementType": "labels.icon",
                "stylers": [{"visibility": "on"}]
            },
            {
                "featureType": "poi.medical",
                "elementType": "labels.text.fill",
                "stylers": [{"color": "#d10808"}]
            }
        ]
    });
    
    // Initialize places service
    placesService = new google.maps.places.PlacesService(map);
    
    // Initialize info window
    infoWindow = new google.maps.InfoWindow();
    
    // Try to get user's current location
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                map.setCenter(userLocation);
                
                // Add a marker for user's location
                new google.maps.Marker({
                    position: userLocation,
                    map: map,
                    title: 'Your Location',
                    icon: {
                        url: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                        scaledSize: new google.maps.Size(40, 40)
                    }
                });
                
                // Auto-search with user's location
                searchNearbyPlaces();
            },
            (error) => {
                console.error('Error getting user location:', error);
                // If geolocation fails, use the default location
                userLocation = defaultLocation;
                searchNearbyPlaces();
            },
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            }
        );
    } else {
        // Browser doesn't support geolocation
        console.error('Geolocation is not supported by this browser.');
        userLocation = defaultLocation;
        searchNearbyPlaces();
    }
}

/**
 * Set up event listeners for the UI elements
 */
function setupEventListeners() {
    // Search button click
    const useLocationBtn = document.getElementById('use-location');
    if (useLocationBtn) {
        useLocationBtn.addEventListener('click', searchNearbyPlaces);
    }
    
    // Facility type change
    const facilityTypeSelect = document.getElementById('facility-type');
    if (facilityTypeSelect) {
        facilityTypeSelect.addEventListener('change', searchNearbyPlaces);
    }
    
    // Radius change
    const radiusSlider = document.getElementById('radius');
    if (radiusSlider) {
        radiusSlider.addEventListener('input', function() {
            const radiusValue = document.getElementById('radius-value');
            if (radiusValue) {
                radiusValue.textContent = this.value;
            }
        });
    }
    
    // Close modal
    const closeModalBtn = document.getElementById('close-modal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', function() {
            const modal = document.getElementById('place-modal');
            if (modal) {
                modal.classList.add('hidden');
            }
        });
    }
    
    // Close modal when clicking outside
    const modal = document.getElementById('place-modal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.add('hidden');
            }
        });
    }
}

/**
 * Search for nearby medical facilities based on user's location and filters
 */
function searchNearbyPlaces() {
    if (!userLocation) return;
    
    const facilityType = document.getElementById('facility-type')?.value || 'hospital';
    const radius = document.getElementById('radius')?.value || 5000;
    
    // Show loading state
    const placesList = document.getElementById('places-list');
    if (placesList) {
        placesList.innerHTML = `
            <div class="col-span-full text-center py-12">
                <i class="fas fa-spinner fa-spin text-4xl text-blue-500 mb-4"></i>
                <p class="text-gray-600">Searching for nearby ${getFacilityTypeName(facilityType)}...</p>
            </div>
        `;
    }
    
    // Clear existing markers
    clearMarkers();
    
    // Make API request to our backend
    fetch(`/api/nearby?lat=${userLocation.lat}&lng=${userLocation.lng}&type=${facilityType}&radius=${radius}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            displayPlaces(data.places || []);
            addMarkersToMap(data.places || []);
        })
        .catch(error => {
            console.error('Error fetching nearby places:', error);
            if (placesList) {
                placesList.innerHTML = `
                    <div class="col-span-full text-center py-12 text-red-500">
                        <i class="fas fa-exclamation-circle text-4xl mb-4"></i>
                        <p>Error: ${error.message || 'Failed to load nearby places'}</p>
                        <button onclick="window.searchNearbyPlaces()" class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                            Try Again
                        </button>
                    </div>
                `;
            }
        });
}

/**
 * Display places in the list view
 * @param {Array} places - Array of place objects to display
 */
function displayPlaces(places) {
    const placesList = document.getElementById('places-list');
    if (!placesList) return;
    
    if (!places || places.length === 0) {
        placesList.innerHTML = `
            <div class="col-span-full text-center py-12 text-gray-500">
                <i class="fas fa-search-location text-4xl mb-4"></i>
                <p>No places found in this area. Try adjusting your search radius.</p>
            </div>
        `;
        return;
    }
    
    // Sort by rating (highest first)
    const sortedPlaces = [...places].sort((a, b) => (b.rating || 0) - (a.rating || 0));
    
    placesList.innerHTML = sortedPlaces.map(place => `
        <div class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
            <div class="p-5">
                <div class="flex justify-between items-start mb-3">
                    <h3 class="text-lg font-semibold text-gray-800">${escapeHtml(place.name)}</h3>
                    ${place.rating ? `
                        <span class="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
                            ${place.rating} <i class="fas fa-star text-yellow-400"></i>
                        </span>
                    ` : ''}
                </div>
                <p class="text-gray-600 text-sm mb-3">
                    <i class="fas fa-map-marker-alt text-red-500 mr-2"></i>
                    ${escapeHtml(place.address || 'Address not available')}
                </p>
                ${place.phone && place.phone !== 'Phone not available' ? `
                    <p class="text-gray-600 text-sm mb-3">
                        <i class="fas fa-phone-alt text-green-500 mr-2"></i>
                        <a href="tel:${place.phone.replace(/[^0-9+]/g, '')}" class="hover:underline">
                            ${place.phone}
                        </a>
                    </p>
                ` : ''}
                <div class="flex justify-between items-center mt-4">
                    <button onclick="window.showPlaceDetails('${place.id}')" 
                            class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                        <i class="fas fa-info-circle mr-1"></i> Details
                    </button>
                    <a href="https://www.google.com/maps/dir/?api=1&destination=${place.location.lat},${place.location.lng}" 
                       target="_blank" 
                       rel="noopener noreferrer"
                       class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                        <i class="fas fa-directions mr-1"></i> Directions
                    </a>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Add markers to the map for each place
 * @param {Array} places - Array of place objects to add as markers
 */
function addMarkersToMap(places) {
    if (!places || !places.length || !map) return;
    
    const bounds = new google.maps.LatLngBounds();
    
    places.forEach(place => {
        if (!place.location || !place.location.lat || !place.location.lng) return;
        
        const position = new google.maps.LatLng(place.location.lat, place.location.lng);
        bounds.extend(position);
        
        const marker = new google.maps.Marker({
            position: position,
            map: map,
            title: place.name,
            icon: {
                url: getMarkerIcon(place.type),
                scaledSize: new google.maps.Size(32, 32)
            },
            animation: google.maps.Animation.DROP
        });
        
        // Store place data on the marker for later use
        marker.placeData = place;
        
        // Add click event to show info window
        marker.addListener('click', () => {
            showPlaceDetails(place.id);
        });
        
        markers.push(marker);
    });
    
    // Fit map to show all markers with some padding
    if (!bounds.isEmpty()) {
        map.fitBounds(bounds, { top: 100, right: 100, bottom: 100, left: 100 });
    }
}

/**
 * Show detailed information about a place in a modal
 * @param {string} placeId - ID of the place to show details for
 */
window.showPlaceDetails = function(placeId) {
    // Find the place in the current markers
    const place = markers.find(marker => 
        marker.placeData && marker.placeData.id === placeId
    )?.placeData;
    
    if (!place) return;
    
    // Update modal content
    const modalTitle = document.getElementById('modal-title');
    const modalAddress = document.getElementById('modal-address');
    const modalPhone = document.getElementById('modal-phone');
    const modalHours = document.getElementById('modal-hours');
    const modalWebsite = document.getElementById('modal-website');
    const modalWebsiteContainer = document.getElementById('modal-website-container');
    const modalHoursContainer = document.getElementById('modal-hours-container');
    const modalDirections = document.getElementById('modal-directions');
    
    if (modalTitle) modalTitle.textContent = place.name || 'No name available';
    if (modalAddress) modalAddress.textContent = place.address || 'Address not available';
    if (modalPhone) modalPhone.textContent = place.phone || 'Phone not available';
    
    // Update website if available
    if (modalWebsite && modalWebsiteContainer) {
        if (place.website) {
            try {
                const url = new URL(place.website);
                modalWebsite.href = url.toString();
                modalWebsite.textContent = url.hostname.replace('www.', '');
                modalWebsiteContainer.classList.remove('hidden');
            } catch (e) {
                modalWebsiteContainer.classList.add('hidden');
            }
        } else {
            modalWebsiteContainer.classList.add('hidden');
        }
    }
    
    // Update opening hours if available
    if (modalHours && modalHoursContainer) {
        if (place.opening_hours && place.opening_hours.length > 0) {
            modalHours.innerHTML = place.opening_hours.map(time => 
                `<li class="py-1">${escapeHtml(time)}</li>`
            ).join('');
            modalHoursContainer.classList.remove('hidden');
        } else {
            modalHoursContainer.classList.add('hidden');
        }
    }
    
    // Update directions link
    if (modalDirections && place.location) {
        modalDirections.href = `https://www.google.com/maps/dir/?api=1&destination=${place.location.lat},${place.location.lng}`;
    }
    
    // Show the modal
    const modal = document.getElementById('place-modal');
    if (modal) {
        modal.classList.remove('hidden');
    }
    
    // Pan to the selected marker
    const marker = markers.find(m => m.placeData && m.placeData.id === placeId);
    if (marker && map) {
        map.panTo(marker.getPosition());
        // Bounce the marker to highlight it
        marker.setAnimation(google.maps.Animation.BOUNCE);
        setTimeout(() => {
            if (marker.getAnimation() !== null) {
                marker.setAnimation(null);
            }
        }, 1500);
    }
};

/**
 * Clear all markers from the map
 */
function clearMarkers() {
    markers.forEach(marker => marker.setMap(null));
    markers = [];
}

/**
 * Get appropriate marker icon based on place type
 * @param {string} type - Type of the place (hospital, clinic, pharmacy, etc.)
 * @returns {string} URL of the marker icon
 */
function getMarkerIcon(type) {
    const icons = {
        'hospital': 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
        'clinic': 'https://maps.google.com/mapfiles/ms/icons/green-dot.png',
        'pharmacy': 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
        'medical_store': 'https://maps.google.com/mapfiles/ms/icons/purple-dot.png',
        'default': 'https://maps.google.com/mapfiles/ms/icons/red-dot.png'
    };
    
    return icons[type] || icons['default'];
}

/**
 * Get a human-readable name for the facility type
 * @param {string} type - The facility type code
 * @returns {string} Human-readable name
 */
function getFacilityTypeName(type) {
    const names = {
        'hospital': 'hospitals',
        'clinic': 'clinics',
        'pharmacy': 'pharmacies',
        'medical_store': 'medical stores',
        'default': 'facilities'
    };
    
    return names[type] || names['default'];
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make the search function available globally
window.searchNearbyPlaces = searchNearbyPlaces;
