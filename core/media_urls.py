"""
Single source of truth for resolving stored media references to public URLs.

Resolution order:
1. If ``MEDIA_CDN_BASE_URL`` is set, return ``{cdn}/{key}`` (Phase 2: stable, cacheable).
2. Else if S3-compatible storage is active, ask the storage backend (Phase 1:
   presigned URLs against private Railway buckets, configurable TTL).
3. Else (local dev / legacy disk), build an absolute URL from
   ``BASE_URL`` + ``MEDIA_URL`` + key so the API contract always returns a
   browser-resolvable URL regardless of environment.

Callers should pass either a Django ``FieldFile`` / ``ImageField`` value or a
raw object key string. ``None`` / empty inputs return ``None``.
"""

from __future__ import annotations

from typing import Optional, Union

from django.conf import settings
from django.core.files.storage import default_storage


def _file_name(value) -> str:
    if value is None:
        return ''
    name = getattr(value, 'name', None)
    if name:
        return str(name).strip()
    return str(value).strip()


def _backend_base_url() -> str:
    base = getattr(settings, 'BACKEND_BASE_URL', '') or ''
    base = str(base).strip()
    if not base:
        return ''
    if not base.startswith(('http://', 'https://')):
        base = 'https://' + base
    return base.rstrip('/')


def absolute_media_url(value: Union[str, object, None]) -> Optional[str]:
    """Return a public, browser-resolvable URL for a stored media reference."""
    name = _file_name(value)
    if not name:
        return None
    if name.startswith(('http://', 'https://')):
        return name

    key = name.lstrip('/')

    cdn_base = (getattr(settings, 'MEDIA_CDN_BASE_URL', '') or '').rstrip('/')
    if cdn_base:
        return f'{cdn_base}/{key}'

    if getattr(settings, 'USE_S3_STORAGE', False):
        try:
            return default_storage.url(key)
        except Exception:
            return None

    media_url = (getattr(settings, 'MEDIA_URL', '/media/') or '/media/').rstrip('/')
    backend = _backend_base_url()
    relative = f'{media_url}/{key}' if media_url else f'/{key}'
    if backend:
        return f'{backend}{relative}'
    return relative
