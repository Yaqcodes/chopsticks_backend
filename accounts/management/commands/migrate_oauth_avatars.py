from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import sys

# Add the utils directory to the path so we can import the avatar downloader
sys.path.append(os.path.join(settings.BASE_DIR, 'utils'))
from avatar_downloader import download_and_save_avatar, is_external_avatar_url

User = get_user_model()


class Command(BaseCommand):
    help = 'Migrate OAuth avatar URLs to local storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even if avatar already exists locally',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write('Starting OAuth avatar migration...')
        
        # Get all users with external avatar URLs
        users_with_external_avatars = []
        for user in User.objects.all():
            # Check if user has an avatar and if it's an external URL
            if user.avatar:
                # Get the avatar value as a string
                avatar_str = str(user.avatar)
                # Check if it looks like an external URL (starts with http/https)
                if avatar_str.startswith(('http://', 'https://')):
                    users_with_external_avatars.append(user)
                    print(f"Found user with external avatar: {user.username} - {avatar_str}")
        
        if not users_with_external_avatars:
            self.stdout.write(self.style.SUCCESS('No users with external avatar URLs found.'))
            return
        
        self.stdout.write(f'Found {len(users_with_external_avatars)} users with external avatars.')
        
        if dry_run:
            self.stdout.write('DRY RUN - No changes will be made.')
            for user in users_with_external_avatars:
                avatar_str = str(user.avatar)
                self.stdout.write(f'  - {user.username}: {avatar_str}')
            return
        
        # Process each user
        success_count = 0
        error_count = 0
        
        for user in users_with_external_avatars:
            try:
                self.stdout.write(f'Processing {user.username}...')
                
                # Get the avatar URL as a string
                avatar_url = str(user.avatar)
                
                # Check if user already has a local avatar (unless force is used)
                if not force and avatar_url.startswith('/media/'):
                    self.stdout.write(f'  Skipping {user.username} - already has local avatar')
                    continue
                
                # Download and save the avatar
                local_avatar_path = download_and_save_avatar(
                    avatar_url, 
                    user.id, 
                    user.username
                )
                
                if local_avatar_path:
                    # Update the user's avatar field
                    user.avatar = local_avatar_path
                    user.save(update_fields=['avatar'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  Successfully migrated avatar for {user.username}: {local_avatar_path}'
                        )
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Failed to download avatar for {user.username}'
                        )
                    )
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  Error processing {user.username}: {str(e)}'
                    )
                )
                error_count += 1
        
        # Summary
        self.stdout.write('\nMigration completed!')
        self.stdout.write(f'  Successfully migrated: {success_count}')
        self.stdout.write(f'  Errors: {error_count}')
        
        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully migrated {success_count} OAuth avatars to local storage!'
                )
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'{error_count} avatars failed to migrate. Check the logs above for details.'
                )
            )
