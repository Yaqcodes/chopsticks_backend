from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Address
from .serializers import (
    AddressSerializer, AddressCreateSerializer, AddressUpdateSerializer,
    GeocodeRequestSerializer, GeocodeResponseSerializer
)
from utils.geocoding import geocode_address


class AddressListView(generics.ListCreateAPIView):
    """List and create user addresses."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = AddressCreateSerializer
    
    def get_queryset(self):
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Address.objects.none()
        
        # DEBUG: print(f"Fetching addresses for user: {self.request.user}")
        addresses = Address.objects.filter(user=self.request.user)
        # DEBUG: print(f"Found {addresses.count()} addresses")
        return addresses
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return AddressSerializer
        return AddressCreateSerializer
    
    def perform_create(self, serializer):
        """Automatically set the user when creating an address."""
        serializer.save(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        """Override list method to add debugging."""
        # DEBUG: print(f"List method called for user: {request.user}")
        # DEBUG: print(f"User ID: {request.user.id}")
        # DEBUG: print(f"User email: {request.user.email}")
        
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        #DEBUG: print(f"Serialized data: {serializer.data}")
        return Response(serializer.data)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete a specific address."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = AddressUpdateSerializer
    
    def get_queryset(self):
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Address.objects.none()
        return Address.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return AddressSerializer
        return AddressUpdateSerializer
    
    def perform_update(self, serializer):
        """Ensure user can only update their own addresses."""
        serializer.save(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_default_address(request, address_id):
    """Set an address as the default address for the user."""
    
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Set all other addresses to non-default
    Address.objects.filter(user=request.user).update(is_default=False)
    
    # Set this address as default
    address.is_default = True
    address.save()
    
    return Response({
        'message': 'Default address updated successfully.',
        'address': AddressSerializer(address).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def geocode_address_view(request):
    """Geocode an address using Google Maps API."""
    
    serializer = GeocodeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Build address string
        address_parts = [serializer.validated_data['address']]
        if serializer.validated_data.get('city'):
            address_parts.append(serializer.validated_data['city'])
        if serializer.validated_data.get('state'):
            address_parts.append(serializer.validated_data['state'])
        if serializer.validated_data.get('postal_code'):
            address_parts.append(serializer.validated_data['postal_code'])
        if serializer.validated_data.get('country'):
            address_parts.append(serializer.validated_data['country'])
        
        address_string = ', '.join(address_parts)
        
        # Geocode the address
        result = geocode_address(address_string)
        
        if result:
            response_data = {
                'latitude': result['latitude'],
                'longitude': result['longitude'],
                'formatted_address': result['formatted_address'],
                'confidence': result.get('confidence', 0.0)
            }
            return Response(response_data)
        else:
            return Response(
                {'error': 'Could not geocode the provided address.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Exception as e:
        return Response(
            {'error': f'Geocoding failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def default_address(request):
    """Get the user's default address."""
    
    try:
        default_address = Address.objects.get(user=request.user, is_default=True)
        serializer = AddressSerializer(default_address)
        return Response(serializer.data)
    except Address.DoesNotExist:
        return Response(
            {'error': 'No default address found.'},
            status=status.HTTP_404_NOT_FOUND
        )
