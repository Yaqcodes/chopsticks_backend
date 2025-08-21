from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import PromoCode, PromoCodeUsage
from .serializers import (
    PromoCodeSerializer, PromoCodeValidationSerializer,
    PromoCodeUsageSerializer, ActivePromotionsSerializer
)


class PromoCodeListView(generics.ListAPIView):
    """List all promotional codes (admin only)."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = PromoCodeSerializer
    queryset = PromoCode.objects.all()
    
    def get_queryset(self):
        # Only staff can see all promo codes
        if not self.request.user.is_staff:
            return PromoCode.objects.none()
        return super().get_queryset()


class ActivePromotionsView(generics.ListAPIView):
    """List all active promotional codes."""
    
    permission_classes = [AllowAny]
    serializer_class = ActivePromotionsSerializer
    
    def get_queryset(self):
        return PromoCode.objects.filter(is_active=True)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_promo_code(request):
    """Validate a promotional code for an order."""
    
    serializer = PromoCodeValidationSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    promo_code = serializer.validated_data['promo_code']
    discount_amount = serializer.validated_data['discount_amount']
    
    return Response({
        'promo_code': PromoCodeSerializer(promo_code).data,
        'discount_amount': discount_amount,
        'message': 'Promotional code applied successfully.'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_promo_usage(request):
    """Get user's promotional code usage history."""
    
    usages = PromoCodeUsage.objects.filter(user=request.user)
    serializer = PromoCodeUsageSerializer(usages, many=True)
    
    return Response({
        'usages': serializer.data,
        'total_usage_count': usages.count()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def promo_code_details(request, code):
    """Get details of a specific promotional code."""
    
    try:
        promo_code = PromoCode.objects.get(code=code.upper())
        
        if not promo_code.is_valid:
            return Response({
                'error': 'This promotional code is not currently valid.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = PromoCodeSerializer(promo_code)
        return Response(serializer.data)
    
    except PromoCode.DoesNotExist:
        return Response({
            'error': 'Promotional code not found.'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_promo_to_order(request, order_id):
    """Apply a promotional code to an existing order."""
    
    from orders.models import Order
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    serializer = PromoCodeValidationSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    promo_code = serializer.validated_data['promo_code']
    discount_amount = serializer.validated_data['discount_amount']
    
    # Check if promo code already applied to this order
    existing_usage = PromoCodeUsage.objects.filter(
        promo_code=promo_code,
        order=order
    ).exists()
    
    if existing_usage:
        return Response({
            'error': 'This promotional code has already been applied to this order.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Apply discount to order
    order.discount_amount += discount_amount
    order.calculate_totals()
    order.save()
    
    # Create usage record
    PromoCodeUsage.objects.create(
        promo_code=promo_code,
        user=request.user,
        order=order,
        discount_amount=discount_amount
    )
    
    return Response({
        'message': 'Promotional code applied to order successfully.',
        'discount_amount': discount_amount,
        'new_total': order.total_amount
    })
