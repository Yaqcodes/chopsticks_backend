from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

User = get_user_model()

try:
    # Import from utils directory using proper Django imports
    from utils.avatar_downloader import download_and_save_avatar, is_external_avatar_url
    logger.info("Avatar downloader imported successfully")
except ImportError as e:
    # If the avatar downloader is not available, log the error and skip processing
    logger.error(f"Failed to import avatar downloader: {e}")
    download_and_save_avatar = None
    is_external_avatar_url = None


@receiver(post_save, sender=User)
def handle_user_avatar_update(sender, instance, created, **kwargs):
    """
    Signal handler to automatically download OAuth avatars when users are created or updated.
    """
    logger.info(f"Signal triggered for user {instance.username} (created: {created})")
    
    if not download_and_save_avatar or not is_external_avatar_url:
        logger.warning("Avatar downloader not available, skipping avatar processing")
        return
    
    # Only process if the user has an avatar and it's external
    if instance.avatar and is_external_avatar_url(instance.avatar):
        logger.info(f"Processing external avatar for user {instance.username}: {instance.avatar}")
        try:
            # Download and save the avatar
            local_avatar_path = download_and_save_avatar(
                instance.avatar,
                instance.id,
                instance.username
            )
            
            if local_avatar_path:
                # Update the user's avatar field to point to local file
                # We need to avoid triggering the signal again
                User.objects.filter(id=instance.id).update(avatar=local_avatar_path)
                
                # Update the instance to reflect the change
                instance.avatar = local_avatar_path
                
                logger.info(f"Successfully downloaded avatar for user {instance.username}: {local_avatar_path}")
                print(f"Successfully downloaded avatar for user {instance.username}: {local_avatar_path}")
            else:
                logger.error(f"Failed to download avatar for user {instance.username}")
                print(f"Failed to download avatar for user {instance.username}")
                
        except Exception as e:
            logger.error(f"Error downloading avatar for user {instance.username}: {str(e)}")
            print(f"Error downloading avatar for user {instance.username}: {str(e)}")
    else:
        logger.debug(f"User {instance.username} has no avatar or avatar is not external: {instance.avatar}")
