"""
Storage backends for Railway Buckets (S3-compatible, private).

Settings inject the connection details via env (BUCKET, ENDPOINT, ACCESS_KEY_ID,
SECRET_ACCESS_KEY, REGION). Defaults below are safe for Railway and most S3-compatible
providers; per-instance overrides come from settings.AWS_* values.
"""

from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """User-uploaded media (product/category/spotlight images, avatars, etc.)."""

    location = ''  # keep keys flat: menu_items/, categories/, spotlights/, avatars/
    default_acl = None  # Railway buckets are private; no ACL header
    file_overwrite = False  # never silently replace an existing key
    signature_version = 's3v4'
    addressing_style = 'virtual'
