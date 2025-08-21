import requests
from django.conf import settings
import math


def geocode_address(address_string):
    """Geocode an address using Google Maps API."""
    
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        return None
    
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': address_string,
        'key': api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            result = data['results'][0]
            location = result['geometry']['location']
            
            return {
                'latitude': location['lat'],
                'longitude': location['lng'],
                'formatted_address': result['formatted_address'],
                'confidence': result.get('geometry', {}).get('location_type', 'unknown')
            }
        
        return None
    
    except requests.RequestException as e:
        print(f"Geocoding error: {str(e)}")
        return None


def calculate_distance(point1, point2):
    """Calculate distance between two points using Haversine formula."""
    
    lat1, lon1 = point1
    lat2, lon2 = point2
    
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def reverse_geocode(latitude, longitude):
    """Reverse geocode coordinates to get address."""
    
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        return None
    
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'latlng': f"{latitude},{longitude}",
        'key': api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            result = data['results'][0]
            return {
                'formatted_address': result['formatted_address'],
                'components': result.get('address_components', [])
            }
        
        return None
    
    except requests.RequestException as e:
        print(f"Reverse geocoding error: {str(e)}")
        return None


def validate_address(address_string):
    """Validate an address and return geocoded information."""
    
    geocoded = geocode_address(address_string)
    if not geocoded:
        return {
            'valid': False,
            'error': 'Could not geocode the provided address.'
        }
    
    return {
        'valid': True,
        'latitude': geocoded['latitude'],
        'longitude': geocoded['longitude'],
        'formatted_address': geocoded['formatted_address']
    }


def get_delivery_zone(latitude, longitude):
    """Check if coordinates are within delivery zone."""
    
    try:
        # Prioritize RestaurantSettings over Django settings
        from core.models import RestaurantSettings
        settings = RestaurantSettings.get_settings()
        restaurant_lat = settings.restaurant_latitude
        restaurant_lng = settings.restaurant_longitude
        delivery_radius = settings.delivery_radius
    except Exception:
        # Fallback to Django settings only if RestaurantSettings fails
        restaurant_lat = getattr(settings, 'RESTAURANT_LATITUDE', 9.0820)  # Abuja coordinates
        restaurant_lng = getattr(settings, 'RESTAURANT_LONGITUDE', 7.3986)
        delivery_radius = getattr(settings, 'DELIVERY_RADIUS_KM', 10.0)
    
    distance = calculate_distance(
        (restaurant_lat, restaurant_lng),
        (latitude, longitude)
    )
    
    return {
        'within_zone': distance <= delivery_radius,
        'distance_km': distance,
        'delivery_radius_km': delivery_radius
    }
