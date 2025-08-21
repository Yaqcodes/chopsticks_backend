import logging
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
from datetime import datetime

from .models import Order, OrderItem
from .serializers import (
    OrderSerializer, OrderListSerializer, OrderDetailSerializer,
    CartCalculationSerializer, DeliveryFeeCalculationSerializer,
    OrderStatusUpdateSerializer, GuestOrderSerializer, UnifiedOrderSerializer
)
from menu.models import MenuItem
from .services import calculate_cart_totals
from loyalty.services import award_points_for_order

logger = logging.getLogger(__name__)


class OrderListView(generics.ListAPIView):
    """List user's order history with filtering capabilities."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'delivery_type']
    ordering_fields = ['created_at', 'total_amount', 'order_number']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        
        queryset = Order.objects.filter(user=self.request.user)
        
        # Handle date filtering manually
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
            except ValueError:
                # If date format is invalid, ignore the filter
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
            except ValueError:
                # If date format is invalid, ignore the filter
                pass
        
        return queryset


class OrderDetailView(generics.RetrieveAPIView):
    """Get detailed information about a specific order."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer
    
    def get_queryset(self):
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user)


class AdminOrderListView(generics.ListAPIView):
    """Admin view to list all orders with filtering capabilities."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'delivery_type']
    ordering_fields = ['created_at', 'total_amount', 'order_number', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        
        # Check if user is staff
        if not self.request.user.is_staff:
            return Order.objects.none()
        
        queryset = Order.objects.all()
        
        # Handle date filtering manually
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
            except ValueError:
                # If date format is invalid, ignore the filter
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
            except ValueError:
                # If date format is invalid, ignore the filter
                pass
        
        return queryset


@api_view(['POST'])
@permission_classes([AllowAny])
def create_order(request):
    """Create a new order for both authenticated and guest users."""
    
    try:
        # Log the incoming request data for debugging
        user_id = request.user.id if request.user.is_authenticated else 'guest'
        logger.info(f"Creating order for user {user_id} with data: {request.data}")
        
        serializer = UnifiedOrderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        # Create the order using the serializer
        order = serializer.save()
        
        # Award points for the order (commented out as requested)
        # if order.user:
        #     award_points_for_order(order)
        
        # Use the serializer to return the response data
        try:
            response_serializer = OrderDetailSerializer(order)
            response_data = response_serializer.data
            logger.info(f"Order {order.order_number} created successfully for user {user_id}")
            
            return Response({
                'message': 'Order created successfully.',
                'order': response_data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as serialization_error:
            logger.error(f"Error serializing order response: {serialization_error}")
            # Return a simplified response if serialization fails
            return Response({
                'message': 'Order created successfully.',
                'order': {
                    'id': order.id,
                    'order_number': order.order_number,
                    'status': order.status,
                    'total_amount': str(order.total_amount)
                }
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        user_id = request.user.id if request.user.is_authenticated else 'guest'
        logger.error(f"Error creating order for user {user_id}: {str(e)}")
        raise


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """Cancel an order."""
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order can be cancelled
    if order.status in ['delivered', 'cancelled', 'refunded']:
        return Response({
            'error': 'Order cannot be cancelled in its current status.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Update order status
    order.status = 'cancelled'
    order.save()
    
    return Response({
        'message': 'Order cancelled successfully.',
        'order': OrderDetailSerializer(order).data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def order_tracking(request, order_number):
    """Track an order by order number."""
    
    try:
        order = Order.objects.get(order_number=order_number)
    except Order.DoesNotExist:
        return Response({
            'error': 'Order not found.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # For authenticated users, ensure they own the order
    if request.user.is_authenticated and order.user != request.user:
        return Response({
            'error': 'You do not have permission to view this order.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    return Response({
        'order': OrderDetailSerializer(order).data
    })


@api_view(['POST'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny for guest checkout
def calculate_cart_totals_view(request):
    """Calculate cart totals including tax and delivery fees."""
    
    serializer = CartCalculationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    cart_items_with_prices = []

    for item in validated_data['items']:
        # Fetch the actual menu item from the database
        menu_item = MenuItem.objects.get(id=item['menu_item_id'])
        
        cart_items_with_prices.append({
            "menu_item_id": item['menu_item_id'],
            "quantity": item['quantity'],
            "price": menu_item.price  # add the price here
        })
    
    # Get UserReward if provided
    user_reward = None
    if validated_data.get('reward_id'):
        try:
            from loyalty.models import UserReward
            user_reward = UserReward.objects.get(
                id=validated_data['reward_id'],
                status='active'
            )
            # Verify user owns the reward if request is authenticated
            if request.user.is_authenticated and user_reward.user != request.user:
                return Response({
                    'error': 'You do not have permission to use this reward.'
                }, status=status.HTTP_403_FORBIDDEN)
        except UserReward.DoesNotExist:
            return Response({
                'error': 'Invalid or expired reward.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        totals = calculate_cart_totals(
            cart_items=cart_items_with_prices,
            delivery_type=validated_data['delivery_type'],
            delivery_fee=validated_data['delivery_fee'],
            promo_code=validated_data.get('promotion_code'),
            user_reward=user_reward
        )

        
        return Response(totals)
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny for guest checkout
def calculate_delivery_fee_view(request):
    """Validate delivery fee amount."""
    
    # Since delivery_fee is now passed directly from frontend, this view just validates it
    delivery_fee = request.data.get('delivery_fee')
    delivery_type = request.data.get('delivery_type', 'delivery')
    
    if delivery_fee is None:
        return Response({
            'error': 'delivery_fee is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        delivery_fee = Decimal(str(delivery_fee))
        if delivery_fee < 0:
            return Response({
                'error': 'delivery_fee must be non-negative'
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            'error': 'delivery_fee must be a valid decimal number'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'delivery_fee': str(delivery_fee),
        'delivery_type': delivery_type,
        'message': 'Delivery fee validated successfully'
    })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    """Update order status (admin functionality)."""
    
    # Check if user is staff/admin
    if not request.user.is_staff:
        return Response({
            'error': 'You do not have permission to update order status.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    order = get_object_or_404(Order, id=order_id)
    serializer = OrderStatusUpdateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Update order status
    order.status = serializer.validated_data['status']
    if serializer.validated_data.get('estimated_delivery_time'):
        order.estimated_delivery_time = serializer.validated_data['estimated_delivery_time']
    order.save()
    
    return Response({
        'message': 'Order status updated successfully.',
        'order': OrderDetailSerializer(order).data
    })
