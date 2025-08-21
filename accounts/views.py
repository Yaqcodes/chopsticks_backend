from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from .models import User, SocialAccount
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    PasswordChangeSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer,
    SocialLoginSerializer
)
from .google_oauth import validate_google_oauth_token


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""
    
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'User registered successfully.',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """User login endpoint."""
    
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        login(request, user)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful.',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """User logout endpoint."""
    
    try:
        logout(request)
        return Response({'message': 'Logout successful.'})
    except Exception as e:
        return Response({'error': 'Logout failed.'}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """User profile management endpoint."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.GenericAPIView):
    """Password change endpoint."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully.'})


class PasswordResetView(generics.GenericAPIView):
    """Password reset request endpoint."""
    
    permission_classes = [AllowAny]
    serializer_class = PasswordResetSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Generate reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Send reset email
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
        send_mail(
            'Password Reset Request',
            f'Click the following link to reset your password: {reset_url}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        return Response({'message': 'Password reset email sent.'})


class PasswordResetConfirmView(generics.GenericAPIView):
    """Password reset confirmation endpoint."""
    
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    
    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is None or not default_token_generator.check_token(user, token):
            return Response({'error': 'Invalid reset link.'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password reset successful.'})


class SocialLoginView(generics.GenericAPIView):
    """Social authentication endpoint."""
    
    permission_classes = [AllowAny]
    serializer_class = SocialLoginSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        provider = data['provider']
        access_token = data['access_token']
        
        try:
            if provider == 'google':
                # Validate Google OAuth token and get user info
                google_user_info = validate_google_oauth_token(access_token)
                
                provider_user_id = google_user_info['provider_user_id']
                email = google_user_info['email']
                first_name = google_user_info['first_name']
                last_name = google_user_info['last_name']
                avatar_url = google_user_info.get('avatar_url', '')
                
                # Check if email is verified
                if not google_user_info.get('email_verified', False):
                    return Response({
                        'error': 'Email not verified with Google. Please verify your email first.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
            else:
                # For other providers, use the data from serializer
                provider_user_id = data['provider_user_id']
                email = data['email']
                first_name = data.get('first_name', '')
                last_name = data.get('last_name', '')
                avatar_url = data.get('avatar_url', '')
            
            # Check if social account exists
            try:
                social_account = SocialAccount.objects.get(
                    provider=provider,
                    provider_user_id=provider_user_id
                )
                user = social_account.user
                
                # Update social account tokens
                social_account.access_token = access_token
                social_account.save()
                
            except SocialAccount.DoesNotExist:
                # Check if user with this email already exists
                try:
                    user = User.objects.get(email=email)
                    
                    # Create social account for existing user
                    SocialAccount.objects.create(
                        user=user,
                        provider=provider,
                        provider_user_id=provider_user_id,
                        access_token=access_token,
                    )
                    
                except User.DoesNotExist:
                    # Create new user and social account
                    username = email.split('@')[0]  # Use email prefix as username
                    
                    # Ensure username is unique
                    base_username = username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    user = User.objects.create(
                        email=email,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    
                    # Set avatar if provided
                    if avatar_url:
                        user.avatar = avatar_url
                        user.save()
                    
                    SocialAccount.objects.create(
                        user=user,
                        provider=provider,
                        provider_user_id=provider_user_id,
                        access_token=access_token,
                    )
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': f'{provider.title()} login successful.',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            })
            
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Social login failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_referrals(request):
    """Get user's referral information."""
    
    user = request.user
    referrals = user.referrals.all()
    
    return Response({
        'referral_code': user.referral_code,
        'referrals_count': referrals.count(),
        'referrals': UserProfileSerializer(referrals, many=True).data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh_view(request):
    """Token refresh endpoint."""
    
    try:
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate and refresh the token
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        return Response({
            'access': access_token,
            'refresh': str(refresh)
        })
        
    except (InvalidToken, TokenError) as e:
        return Response(
            {'error': 'Invalid or expired refresh token.'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'error': 'Token refresh failed.'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def google_oauth_url(request):
    """Get Google OAuth authorization URL."""
    try:
        from .google_oauth import get_google_oauth_url
        oauth_url = get_google_oauth_url()
        
        return Response({
            'oauth_url': oauth_url,
            'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
        })
    except Exception as e:
        return Response({
            'error': f'Failed to generate OAuth URL: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
