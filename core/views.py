from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import RestaurantSettings
from .serializers import RestaurantSettingsSerializer, PublicRestaurantSettingsSerializer


class RestaurantSettingsView(generics.RetrieveUpdateAPIView):
    """Get and update restaurant settings (admin only)."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = RestaurantSettingsSerializer
    
    def get_object(self):
        return RestaurantSettings.get_settings()
    
    def get_permissions(self):
        """Only staff can update settings."""
        if self.request.method in ['PUT', 'PATCH']:
            return [IsAuthenticated()]
        return [AllowAny()]


@api_view(['GET'])
@permission_classes([AllowAny])
def public_restaurant_info(request):
    """Get public restaurant information."""
    
    settings = RestaurantSettings.get_settings()
    serializer = PublicRestaurantSettingsSerializer(settings)
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint for monitoring."""
    
    return Response({
        'status': 'healthy',
        'message': 'Chopsticks and Bowls API is running'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def system_status(request):
    """Get system status and maintenance information."""
    
    settings = RestaurantSettings.get_settings()
    
    return Response({
        'maintenance_mode': getattr(settings, 'maintenance_mode', False),
        'maintenance_message': getattr(settings, 'maintenance_message', ''),
        'is_open': getattr(settings, 'is_open', True),
        'opening_time': getattr(settings, 'opening_time', None),
        'closing_time': getattr(settings, 'closing_time', None)
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def restaurant_settings(request):
    """Get comprehensive restaurant settings for frontend display."""
    try:
        settings = RestaurantSettings.get_settings()
        serializer = PublicRestaurantSettingsSerializer(settings)
        return Response(serializer.data)
    except Exception as e:
        return Response({
            'error': 'Failed to retrieve restaurant settings',
            'details': str(e)
        }, status=500)
