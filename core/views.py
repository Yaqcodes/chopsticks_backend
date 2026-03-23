from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import RestaurantSettings, Quote
from .utils import get_business_from_request
from .serializers import (
    RestaurantSettingsSerializer, 
    PublicRestaurantSettingsSerializer,
    QuoteSerializer,
    QuoteCreateSerializer,
    QuoteAdminSerializer
)

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
        return get_business_from_request(self.request)
    
    def get_permissions(self):
        """Only staff can update settings."""
        if self.request.method in ['PUT', 'PATCH']:
            return [IsAuthenticated()]
        return [AllowAny()]


@api_view(['GET'])
@permission_classes([AllowAny])
def public_restaurant_info(request):
    """Get public restaurant information."""
    
    restaurant_settings = get_business_from_request(request)
    serializer = PublicRestaurantSettingsSerializer(restaurant_settings)
    
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
    
    settings = get_business_from_request(request)
    
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
        settings = get_business_from_request(request)
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


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_quote(request):
    """Submit a quote request from the frontend."""
    try:
        # Identify business from frontend origin
        restaurant_settings = get_business_from_request(request)
        
        # Create quote with business association
        serializer = QuoteCreateSerializer(data=request.data)
        if serializer.is_valid():
            quote = serializer.save(restaurant_settings=restaurant_settings)
            response_serializer = QuoteSerializer(quote)
            return Response({
                'message': 'Quote request submitted successfully. We will get back to you soon!',
                'quote': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as e:
        return Response({
            'error': 'Business identification failed',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Failed to submit quote request',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QuoteListView(generics.ListAPIView):
    """List quote requests (admin only, filtered by business)."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = QuoteAdminSerializer
    
    def get_queryset(self):
        """Filter quotes by business."""
        if not self.request.user.is_staff:
            return Quote.objects.none()
        
        try:
            restaurant_settings = get_business_from_request(self.request)
            return Quote.objects.filter(restaurant_settings=restaurant_settings)
        except ValueError:
            return Quote.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Override list to check permissions."""
        if not request.user.is_staff:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)


class QuoteDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve and update quote request (admin only)."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = QuoteAdminSerializer
    
    def get_queryset(self):
        """Filter quotes by business."""
        if not self.request.user.is_staff:
            return Quote.objects.none()
        
        try:
            restaurant_settings = get_business_from_request(self.request)
            return Quote.objects.filter(restaurant_settings=restaurant_settings)
        except ValueError:
            return Quote.objects.none()
    
    def get(self, request, *args, **kwargs):
        """Override get to check permissions."""
        if not request.user.is_staff:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().get(request, *args, **kwargs)
    
    def patch(self, request, *args, **kwargs):
        """Override patch to check permissions."""
        if not request.user.is_staff:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().patch(request, *args, **kwargs)
