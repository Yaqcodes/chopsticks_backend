import os
import uuid
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def download_and_save_avatar(avatar_url, user_id, username):
    """
    Download an avatar image from a URL and save it through the configured storage backend.

    Works on both local FileSystemStorage (dev) and S3-compatible storage (production).

    Returns:
        str: Storage key (e.g. ``avatars/<username>_<id>_<hash>.jpg``) suitable for
             assigning to ``ImageField.name`` / ``user.avatar.name``.
        None: If download failed.
    """
    try:
        response = requests.get(avatar_url, timeout=10)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            print(f"Warning: URL does not return an image. Content-Type: {content_type}")
            return None

        file_extension = get_file_extension(avatar_url)
        unique_filename = f"{username}_{user_id}_{uuid.uuid4().hex[:8]}{file_extension}"
        target_key = f'avatars/{unique_filename}'

        saved_key = default_storage.save(target_key, ContentFile(response.content))
        return saved_key

    except requests.RequestException as e:
        print(f"Failed to download avatar from {avatar_url}: {e}")
        return None
    except Exception as e:
        print(f"Error saving avatar: {e}")
        return None


def get_file_extension(url):
    """
    Extract file extension from URL or content type.
    Defaults to .jpg if no extension found.
    """
    # Try to get extension from URL
    parsed_url = urlparse(url)
    path = parsed_url.path
    if '.' in path:
        ext = os.path.splitext(path)[1]
        if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return ext
    
    # Default to .jpg
    return '.jpg'


def is_external_avatar_url(avatar_url):
    """
    Check if the avatar URL is external (not local media).
    
    Args:
        avatar_url: The avatar URL to check (can be string or ImageFieldFile)
    
    Returns:
        bool: True if external, False if local
    """
    if not avatar_url:
        return False
    
    # Convert ImageFieldFile to string if needed
    if hasattr(avatar_url, 'url'):
        avatar_url = avatar_url.url
    elif hasattr(avatar_url, 'name'):
        avatar_url = avatar_url.name
    
    # Convert to string if it's not already
    avatar_url = str(avatar_url)
    
    # Check if it's a local media URL
    if avatar_url.startswith('/media/'):
        return False
    
    # Check if it's a full URL (external)
    if avatar_url.startswith(('http://', 'https://')):
        return True
    
    return False
