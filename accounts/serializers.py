from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, SocialAccount


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'phone', 
                 'password', 'password_confirm', 'referral_code', 'date_of_birth']
        extra_kwargs = {
            'username': {'required': False},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        
        # Handle referral code
        referral_code = attrs.get('referral_code')
        if referral_code:
            try:
                referred_by = User.objects.get(referral_code=referral_code)
                if referred_by == self.context['request'].user:
                    raise serializers.ValidationError("You cannot refer yourself.")
                attrs['referred_by'] = referred_by
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid referral code.")
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        validated_data.pop('referral_code', None)
        
        # Generate username from email if not provided
        if not validated_data.get('username'):
            validated_data['username'] = validated_data['email']
        
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email_or_username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email_or_username = attrs.get('email_or_username')
        password = attrs.get('password')
        
        if email_or_username and password:
            # Use the custom authentication backend
            user = authenticate(username=email_or_username, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email/username and password.')
        
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile management."""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 
                 'phone', 'avatar', 'date_of_birth', 'referral_code', 'date_joined']
        read_only_fields = ['id', 'referral_code', 'date_joined']
    
    def update(self, instance, validated_data):
        # Handle email uniqueness
        email = validated_data.get('email')
        if email and email != instance.email:
            if User.objects.filter(email=email).exists():
                raise serializers.ValidationError("Email already exists.")
        
        # Handle username uniqueness
        username = validated_data.get('username')
        if username and username != instance.username:
            if User.objects.filter(username=username).exists():
                raise serializers.ValidationError("Username already exists.")
        
        return super().update(instance, validated_data)


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email address.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""
    
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs


class SocialLoginSerializer(serializers.Serializer):
    """Serializer for social authentication."""
    
    provider = serializers.ChoiceField(choices=SocialAccount.PROVIDER_CHOICES)
    access_token = serializers.CharField()
    provider_user_id = serializers.CharField(required=False)  # Not needed for Google
    email = serializers.EmailField(required=False)  # Not needed for Google
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    avatar_url = serializers.URLField(required=False)
    
    def validate(self, attrs):
        provider = attrs.get('provider')
        access_token = attrs.get('access_token')
        
        if not access_token:
            raise serializers.ValidationError("Access token is required.")
        
        # For Google OAuth, we only need provider and access_token
        # Other providers might need additional fields
        if provider == 'google':
            # Google OAuth will provide user info from the token
            pass
        else:
            # For other providers, validate required fields
            if not attrs.get('provider_user_id'):
                raise serializers.ValidationError("Provider user ID is required for non-Google providers.")
            if not attrs.get('email'):
                raise serializers.ValidationError("Email is required for non-Google providers.")
        
        return attrs
