"""
Google OAuth utility functions for validating Google OAuth tokens.
"""

import json
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


def validate_google_oauth_token(access_token):
    """
    Validate Google OAuth access token and return user information.
    
    Args:
        access_token (str): Google OAuth access token
        
    Returns:
        dict: User information from Google
        
    Raises:
        ValidationError: If token is invalid or expired
    """
    try:
        # First, try to validate the token using Google's ID token validation
        # This is more secure than just using the access token
        id_info = id_token.verify_oauth2_token(
            access_token, 
            google_requests.Request(), 
            settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
        )
        
        # Verify the token was issued by Google
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValidationError('Invalid token issuer')
            
        # Verify the token is for our app
        if id_info['aud'] != settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
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


def get_google_oauth_url():
    """
    Get Google OAuth authorization URL for frontend.
    
    Returns:
        str: Google OAuth authorization URL
    """
    client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
    redirect_uri = f"{settings.OAUTH_BASE_URL}/api/auth/google/callback/"
    scope = "openid email profile"
    
    return (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"access_type=offline&"
        f"prompt=consent"
    )


def exchange_code_for_token(authorization_code):
    """
    Exchange authorization code for access token.
    
    Args:
        authorization_code (str): The authorization code from Google OAuth callback
        
    Returns:
        str: Access token from Google
        
    Raises:
        ValidationError: If token exchange fails
    """
    try:
        client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
        client_secret = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
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
