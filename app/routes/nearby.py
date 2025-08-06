from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for
from flask_login import login_required, current_user
import requests
import os
from datetime import datetime

nearby_bp = Blueprint('nearby', __name__)

# Google Maps API configuration
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
PLACES_API_BASE_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
PLACE_DETAILS_URL = 'https://maps.googleapis.com/maps/api/place/details/json'

@nearby_bp.route('/nearby')
@login_required
def nearby_medical_facilities():
    """Render the nearby medical facilities page"""
    return render_template('menstrual_enhanced/nearby.html', 
                         google_maps_api_key=GOOGLE_MAPS_API_KEY)

@nearby_bp.route('/test-api')
@login_required
def test_api():
    """Test endpoint to verify Google Maps API key is working"""
    test_address = "New York"
    test_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={test_address}&key={GOOGLE_MAPS_API_KEY}"
    
    try:
        response = requests.get(test_url)
        data = response.json()
        
        if data.get('status') == 'OK':
            return jsonify({
                'status': 'success',
                'message': 'Google Maps API is working correctly',
                'test_address': test_address,
                'response_status': data.get('status'),
                'results_count': len(data.get('results', [])),
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Google Maps API returned an error',
                'test_address': test_address,
                'api_status': data.get('status', 'UNKNOWN_ERROR'),
                'error_message': data.get('error_message', 'No error message provided'),
                'timestamp': datetime.utcnow().isoformat()
            }), 400
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to connect to Google Maps API',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@nearby_bp.route('/api/nearby')
@login_required
def get_nearby_places():
    """
    API endpoint to get nearby medical facilities
    Query params:
    - lat: latitude
    - lng: longitude
    - type: hospital|pharmacy|doctor
    - radius: search radius in meters (default: 5000)
    """
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        place_type = request.args.get('type', 'hospital')
        radius = request.args.get('radius', 5000, type=int)
        
        if not all([lat, lng]):
            return jsonify({'error': 'Latitude and longitude are required'}), 400
            
        # Map place types to Google Places types
        type_mapping = {
            'hospital': 'hospital',
            'clinic': 'doctor',
            'pharmacy': 'pharmacy',
            'medical_store': 'pharmacy'
        }
        
        place_type = type_mapping.get(place_type, 'hospital')
        
        params = {
            'location': f'{lat},{lng}',
            'radius': radius,
            'type': place_type,
            'keyword': 'medical' if place_type == 'doctor' else None,
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(PLACES_API_BASE_URL, params=params)
        data = response.json()
        
        if data.get('status') != 'OK':
            return jsonify({'error': 'Failed to fetch nearby places'}), 500
            
        # Get more details for each place
        places = []
        for place in data.get('results', [])[:10]:  # Limit to 10 results
            place_id = place.get('place_id')
            details = get_place_details(place_id)
            if details:
                places.append({
                    'id': place_id,
                    'name': place.get('name'),
                    'address': details.get('formatted_address', 'Address not available'),
                    'phone': details.get('formatted_phone_number', 'Phone not available'),
                    'rating': place.get('rating', 'N/A'),
                    'location': place.get('geometry', {}).get('location'),
                    'opening_hours': details.get('opening_hours', {}).get('weekday_text', []),
                    'website': details.get('website', '')
                })
        
        return jsonify({'places': places})
        
    except Exception as e:
        current_app.logger.error(f"Error in get_nearby_places: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching nearby places'}), 500

def get_place_details(place_id):
    """Get detailed information about a place"""
    try:
        params = {
            'place_id': place_id,
            'fields': 'formatted_phone_number,website,opening_hours,formatted_address',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(PLACE_DETAILS_URL, params=params)
        data = response.json()
        
        if data.get('status') == 'OK':
            return data.get('result', {})
        return {}
        
    except Exception as e:
        current_app.logger.error(f"Error getting place details: {str(e)}")
        return {}
