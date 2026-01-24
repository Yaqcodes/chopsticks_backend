"""
Google OAuth utility functions for validating Google OAuth tokens.
"""

import json
import requests
from urllib.parse import urlencode
from django.conf import settings
from django.core.exceptions import ValidationError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


def validate_google_oauth_token(access_token, restaurant_settings):
    """
    Validate Google OAuth access token and return user information (business-scoped).
    
    Args:
        access_token (str): Google OAuth access token
        restaurant_settings: RestaurantSettings instance with OAuth credentials
        
    Returns:
        dict: User information from Google
        
    Raises:
        ValidationError: If token is invalid or expired
    """
    if not restaurant_settings or not restaurant_settings.google_oauth_client_id:
        raise ValidationError('OAuth credentials not configured for this business')
    
    client_id = restaurant_settings.google_oauth_client_id
    
    try:
        # First, try to validate the token using Google's ID token validation
        # This is more secure than just using the access token
        id_info = id_token.verify_oauth2_token(
            access_token, 
            google_requests.Request(), 
            client_id
        )
        
        # Verify the token was issued by Google
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValidationError('Invalid token issuer')
            
        # Verify the token is for our app
        if id_info['aud'] != client_id:
            raise ValidationError('Invalid token audience')
            
        return {
            'provider_user_id': id_info['sub'],
            'email': id_info['email'],
            'first_name': id_info.get('given_name', ''),
            'last_name': id_info.get('family_name', ''),
            'avatar_url': id_info.get('picture', ''),
            'email_verified': id_info.get('email_verified', False)
        }
        
    except Exception as e:
        # Fallback: try to get user info using the access token
        try:
            user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.get(user_info_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            user_data = response.json()
            
            return {
                'provider_user_id': user_data['id'],
                'email': user_data['email'],
                'first_name': user_data.get('given_name', ''),
                'last_name': user_data.get('family_name', ''),
                'avatar_url': user_data.get('picture', ''),
                'email_verified': user_data.get('verified_email', False)
            }
            
        except requests.RequestException as req_error:
            raise ValidationError(f'Failed to validate Google token: {str(req_error)}')
        except json.JSONDecodeError:
            raise ValidationError('Invalid response from Google API')
        except Exception as fallback_error:
            raise ValidationError(f'Google token validation failed: {str(e)}')


def get_google_oauth_url(restaurant_settings):
    """
    Get Google OAuth authorization URL for frontend (business-scoped).
    
    Args:
        restaurant_settings: RestaurantSettings instance with OAuth credentials
        
    Returns:
        str: Google OAuth authorization URL
        
    Raises:
        ValueError: If OAuth credentials are not configured
    """
    if not restaurant_settings or not restaurant_settings.google_oauth_client_id:
        raise ValueError('OAuth credentials not configured for this business')
    
    client_id = restaurant_settings.google_oauth_client_id
    redirect_uri = f"{settings.OAUTH_BASE_URL}/api/auth/google/callback/"
    scope = "openid email profile"
    
    # Build query parameters with proper URL encoding
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scope,
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_code_for_token(authorization_code, restaurant_settings):
    """
    Exchange authorization code for access token (business-scoped).
    
    Args:
        authorization_code (str): The authorization code from Google OAuth callback
        restaurant_settings: RestaurantSettings instance with OAuth credentials
        
    Returns:
        str: Access token from Google
        
    Raises:
        ValidationError: If token exchange fails
    """
    if not restaurant_settings or not restaurant_settings.google_oauth_client_id:
        raise ValidationError('OAuth credentials not configured for this business')
    
    try:
        client_id = restaurant_settings.google_oauth_client_id
        client_secret = restaurant_settings.google_oauth_client_secret
        if not client_secret:
            raise ValidationError('OAuth client secret not configured for this business')
        redirect_uri = f"{settings.OAUTH_BASE_URL}/api/auth/google/callback/"
        
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': authorization_code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            raise ValidationError('No access token received from Google')
            
        return access_token
        
    except requests.RequestException as req_error:
        raise ValidationError(f'Failed to exchange code for token: {str(req_error)}')
    except Exception as e:
        raise ValidationError(f'Token exchange failed: {str(e)}')
