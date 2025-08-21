from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import RestaurantSettings
from .serializers import RestaurantSettingsSerializer, PublicRestaurantSettingsSerializer

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
import os


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


@staff_member_required
def user_guide(request):
    """Serve the user guide HTML file."""
    try:
        # Get the path to the HTML file
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_file_path = os.path.join(current_dir, 'USER_GUIDE.html')
        
        # Check if file exists
        if not os.path.exists(html_file_path):
            return HttpResponse(
                "User Guide not found. Please run the conversion script first.",
                status=404
            )
        
        # Read and serve the HTML file
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return HttpResponse(html_content, content_type='text/html')
        
    except Exception as e:
        return HttpResponse(
            f"Error serving user guide: {str(e)}",
            status=500
        )

@staff_member_required
def redirect_to_guide(request):
    """Redirect root URL to user guide."""
    return HttpResponseRedirect('/guide/user-guide/')
