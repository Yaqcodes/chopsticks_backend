from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Load dummy data into the database for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql-file',
            type=str,
            default='load_dummy_data.sql',
            help='Path to SQL file (default: load_dummy_data.sql)'
        )
        parser.add_argument(
            '--create-users',
            action='store_true',
            help='Create test users before loading data'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting dummy data loading...')
        
        # Create test users if requested
        if options['create_users']:
            self.create_test_users()
        
        # Load SQL data
        sql_file = options['sql_file']
        self.load_sql_data(sql_file)
        
        self.stdout.write(
            self.style.SUCCESS('✅ Dummy data loaded successfully!')
        )

    def create_test_users(self):
        """Create test users with proper password hashing"""
        self.stdout.write('Creating test users...')
        
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@chopsticks.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
                'password': 'testpass123'
            },
            {
                'username': 'testuser',
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'is_staff': False,
                'is_superuser': False,
                'password': 'testpass123'
            },
            {
                'username': 'john_doe',
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'is_staff': False,
                'is_superuser': False,
                'password': 'testpass123'
            },
            {
                'username': 'jane_smith',
                'email': 'jane@example.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'is_staff': False,
                'is_superuser': False,
                'password': 'testpass123'
            },
            {
                'username': 'mike_wilson',
                'email': 'mike@example.com',
                'first_name': 'Mike',
                'last_name': 'Wilson',
                'is_staff': False,
                'is_superuser': False,
                'password': 'testpass123'
            }
        ]
        
        for user_data in users_data:
            username = user_data['username']
            email = user_data['email']
            
            if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
                self.stdout.write(f'User {username} or email {email} already exists, skipping...')
                continue
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                is_staff=user_data['is_staff'],
                is_superuser=user_data['is_superuser'],
                password=user_data['password']
            )
            self.stdout.write(f'Created user: {username} ({email})')
        
        self.stdout.write('Test users created successfully!')

    def load_sql_data(self, sql_file):
        """Load data from SQL file"""
        self.stdout.write(f'Loading data from {sql_file}...')
        
        # Get the path to the SQL file
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        sql_path = os.path.join(base_dir, sql_file)
        
        if not os.path.exists(sql_path):
            self.stdout.write(
                self.style.ERROR(f'❌ SQL file not found: {sql_path}')
            )
            return
        
        try:
            with open(sql_path, 'r') as file:
                sql_content = file.read()
            
            # Split SQL into individual statements
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            with connection.cursor() as cursor:
                for i, statement in enumerate(statements, 1):
                    if statement and not statement.startswith('--'):
                        try:
                            cursor.execute(statement)
                            self.stdout.write(f'Executed statement {i}/{len(statements)}')
                        except Exception as e:
                            self.stdout.write(
                                self.style.WARNING(f'Warning in statement {i}: {e}')
                            )
            
            self.stdout.write('SQL data loaded successfully!')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error loading SQL data: {e}')
            )
