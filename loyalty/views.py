from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404, render
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect

from .models import UserPoints, PointsTransaction, Reward, UserReward, LoyaltyCard
from .serializers import (
    UserPointsSerializer, PointsTransactionSerializer, RewardSerializer,
    UserRewardSerializer, RewardRedemptionSerializer, PointsEarningSerializer,
    ReferralBonusSerializer, LoyaltyCardSerializer, QRCodeScanSerializer, QRCodeScanResponseSerializer
)
from .services import award_points_for_order, process_referral_bonus, scan_loyalty_card
# QR scanner functionality moved to frontend JavaScript
def validate_and_extract_loyalty_code(qr_data):
    """
    Validate if QR code data is a valid loyalty card.
    
    Args:
        qr_data: QR code data string
        
    Returns:
        str or None: Valid loyalty code or None
    """
    # Check if it's a Google Apps Script URL format
    if 'script.google.com' in qr_data and 'customerID=' in qr_data:
        try:
            # Extract customerID from URL
            import re
            match = re.search(r'customerID=(\d+)', qr_data)
            if match:
                customer_id = match.group(1)
                return customer_id
        except Exception as e:
            print(f"Error extracting customerID from URL: {e}")
            return None
    
    # Check if QR code starts with LOYALTY- prefix (legacy format)
    if qr_data.startswith('LOYALTY-'):
        # Check if it's the correct format (LOYALTY-XXXXXXXXXXXX)
        if len(qr_data) == 19:  # LOYALTY- + 12 characters
            return qr_data  # Return full QR code for database lookup
    
    # Check if it's just a plain customer ID number
    if qr_data.isdigit():
        return qr_data
    
    return None


class UserPointsView(generics.RetrieveAPIView):
    """Get user's points balance."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = UserPointsSerializer
    
    @swagger_auto_schema(
        operation_description="Retrieve the current user's loyalty points balance",
        operation_summary="Get User Points Balance",
        responses={
            200: openapi.Response(
                description="User points balance retrieved successfully",
                schema=UserPointsSerializer
            ),
            401: "Authentication required"
        },
        tags=["Loyalty Points"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_object(self):
        user_points, created = UserPoints.objects.get_or_create(user=self.request.user)
        return user_points


class PointsHistoryView(generics.ListAPIView):
    """Get user's points transaction history."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = PointsTransactionSerializer
    
    def get_queryset(self):
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return PointsTransaction.objects.none()
        return PointsTransaction.objects.filter(user=self.request.user)


class AvailableRewardsView(generics.ListAPIView):
    """List all available rewards."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = RewardSerializer
    
    def get_queryset(self):
        return Reward.objects.filter(is_active=True)


class UserRewardsView(generics.ListAPIView):
    """Get user's redeemed rewards."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = UserRewardSerializer
    
    def get_queryset(self):
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return UserReward.objects.none()
        
        # First, check and update expired rewards for this user
        user_rewards = UserReward.objects.filter(user=self.request.user, status='active')
        for user_reward in user_rewards:
            user_reward.check_and_update_expired_status()
        
        queryset = UserReward.objects.filter(user=self.request.user)
        
        # Filter by status if provided
        status = self.request.query_params.get('status')
        if status and status in ['active', 'used', 'expired']:
            queryset = queryset.filter(status=status)
        
        # Filter by reward type if provided
        reward_type = self.request.query_params.get('reward_type')
        if reward_type:
            queryset = queryset.filter(reward__reward_type=reward_type)
        
        # Filter by date range if provided
        date_from = self.request.query_params.get('date_from')
        if date_from:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(redeemed_at__date__gte=date_obj.date())
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(redeemed_at__date__lte=date_obj.date())
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        return queryset


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redeem_reward(request):
    """Redeem a reward with points."""
    
    serializer = RewardRedemptionSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    reward_id = serializer.validated_data['reward_id']
    user = request.user
    
    try:
        with transaction.atomic():
            # Get reward and user points
            reward = Reward.objects.get(id=reward_id)
            user_points = get_object_or_404(UserPoints, user=user)
            
            # Check if user has enough points
            if user_points.balance < reward.points_required:
                return Response({
                    'error': 'Insufficient points to redeem this reward.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Spend points
            user_points.spend_points(reward.points_required, f"Redeemed: {reward.name}")
            
            # Create user reward
            user_reward = UserReward.objects.create(
                user=user,
                reward=reward,
                points_spent=reward.points_required
            )
            
            # Update reward redemption count
            reward.current_redemptions += 1
            reward.save()
            
            return Response({
                'message': 'Reward redeemed successfully.',
                'user_reward': UserRewardSerializer(user_reward).data,
                'remaining_points': user_points.balance
            })
    
    except Exception as e:
        return Response({
            'error': f'Failed to redeem reward: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_points_earning(request):
    """Calculate points that would be earned from an order."""
    
    serializer = PointsEarningSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    points_breakdown = serializer.calculate_points()
    
    return Response({
        'points_breakdown': points_breakdown
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_referral_bonus_view(request):
    """Process referral bonus for a new user."""
    
    serializer = ReferralBonusSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    referral_code = serializer.validated_data['referral_code']
    
    try:
        success = process_referral_bonus(request.user, referral_code)
        if success:
            return Response({
                'message': 'Referral bonus processed successfully.'
            })
        else:
            return Response({
                'error': 'Failed to process referral bonus.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'error': f'Failed to process referral bonus: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loyalty_summary(request):
    """Get comprehensive loyalty summary for user."""
    
    user = request.user
    
    try:
        user_points = UserPoints.objects.get(user=user)
        recent_transactions = PointsTransaction.objects.filter(user=user)[:5]
        active_rewards = UserReward.objects.filter(user=user, status='active')
        available_rewards = Reward.objects.filter(is_active=True)
        
        # Calculate available rewards user can redeem
        redeemable_rewards = [
            reward for reward in available_rewards 
            if reward.can_be_redeemed_by(user)
        ]
        
        return Response({
            'points': UserPointsSerializer(user_points).data,
            'recent_transactions': PointsTransactionSerializer(recent_transactions, many=True).data,
            'active_rewards': UserRewardSerializer(active_rewards, many=True).data,
            'redeemable_rewards_count': len(redeemable_rewards),
            'referral_code': user.referral_code,
            'referrals_count': user.referrals.count()
        })
    
    except UserPoints.DoesNotExist:
        # Create user points if they don't exist
        user_points = UserPoints.objects.create(user=user)
        return Response({
            'points': UserPointsSerializer(user_points).data,
            'recent_transactions': [],
            'active_rewards': [],
            'redeemable_rewards_count': 0,
            'referral_code': user.referral_code,
            'referrals_count': 0
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_reward(request, reward_id):
    """Use a redeemed reward in an order."""
    
    try:
        user_reward = get_object_or_404(UserReward, id=reward_id, user=request.user, status='active')
        
        # Mark reward as used
        user_reward.use_reward()
        
        return Response({
            'message': 'Reward used successfully.',
            'user_reward': UserRewardSerializer(user_reward).data
        })
    
    except UserReward.DoesNotExist:
        return Response({
            'error': 'Reward not found or not available for use.'
        }, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='post',
    operation_description="Scan a loyalty card QR code and award points to the user",
    operation_summary="Scan Loyalty Card",
    request_body=QRCodeScanSerializer,
    responses={
        200: openapi.Response(
            description="Loyalty card scanned successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'user': openapi.Schema(type=openapi.TYPE_STRING),
                    'points_awarded': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'new_balance': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'scan_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                }
            )
        ),
        400: "Invalid QR code or scan failed",
        401: "Authentication required"
    },
    tags=["Loyalty Cards"]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scan_loyalty_card_view(request):
    """Scan a loyalty card QR code and award points."""
    
    serializer = QRCodeScanSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    qr_code = serializer.validated_data['qr_code']
    visit_amount = serializer.validated_data.get('visit_amount')
    visit_type = serializer.validated_data['visit_type']
    
    # Scan the loyalty card
    result = scan_loyalty_card(qr_code, visit_amount, visit_type)
    
    if result['success']:
        return Response({
            'message': 'Loyalty card scanned successfully.',
            'user': result['user'],
            'points_awarded': result['points_awarded'],
            'new_balance': result['new_balance'],
            'scan_time': result['scan_time']
        })
    else:
        return Response({
            'error': result['error']
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_loyalty_card(request):
    """Get user's loyalty card information with tier details."""
    
    try:
        # Get or create loyalty card
        loyalty_card, created = LoyaltyCard.objects.get_or_create(user=request.user)
        
        # Serialize with tier information
        serializer = LoyaltyCardSerializer(loyalty_card, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data,
            'message': 'Loyalty card retrieved successfully'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error retrieving loyalty card: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_qr_code(request):
    """Regenerate QR code for user's loyalty card."""
    
    try:
        loyalty_card = LoyaltyCard.objects.get(user=request.user)
        
        # Generate new QR code
        import uuid
        loyalty_card.qr_code = f"LOYALTY-{uuid.uuid4().hex[:12].upper()}"
        loyalty_card.save()
        
        return Response({
            'message': 'QR code regenerated successfully.',
            'qr_code': loyalty_card.qr_code
        })
    except LoyaltyCard.DoesNotExist:
        return Response({
            'error': 'Loyalty card not found.'
        }, status=status.HTTP_404_NOT_FOUND)


# Admin QR Code Scanning Views
@staff_member_required
def qr_scan_dashboard(request):
    """Admin dashboard for QR code scanning."""
    
    # Get recent transactions
    recent_transactions = PointsTransaction.objects.filter(
        transaction_type='physical_visit'
    ).select_related('user').order_by('-created_at')[:10]
    
    # Get statistics
    total_cards = LoyaltyCard.objects.count()
    active_cards = LoyaltyCard.objects.filter(is_active=True).count()
    today_scans = PointsTransaction.objects.filter(
        transaction_type='physical_visit',
        created_at__date=timezone.now().date()
    ).count()
    
    context = {
        'recent_transactions': recent_transactions,
        'total_cards': total_cards,
        'active_cards': active_cards,
        'today_scans': today_scans,
    }
    
    return render(request, 'loyalty/admin/qr_scan_dashboard.html', context)


@staff_member_required
def qr_scan_interface(request):
    """QR code scanning interface for staff."""
    
    return render(request, 'loyalty/admin/qr_scan_interface.html')


@method_decorator(csrf_exempt, name='dispatch')
class QRScanAPIView(View):
    """API view for QR code scanning (admin use)."""
    
    def post(self, request, *args, **kwargs):
        """Handle QR code scan."""
        try:
            # Check if it's a file upload or JSON data
            if request.FILES.get('qr_image'):
                # Handle image upload
                return self.handle_image_upload(request)
            else:
                # Handle JSON data (manual QR code entry)
                return self.handle_json_data(request)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error processing scan: {str(e)}'
            }, status=500)
    
    def handle_image_upload(self, request):
        """Handle QR code scanning from uploaded image."""
        try:
            # For now, we'll use the frontend JavaScript QR scanner
            # This method can be enhanced later with backend image processing
            return JsonResponse({
                'success': False,
                'error': 'Image upload scanning is not yet implemented. Please use the camera scanner or manual entry.'
            }, status=400)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error processing image: {str(e)}'
            }, status=400)
    
    def handle_json_data(self, request):
        """Handle manual QR code entry via JSON."""
        try:
            data = json.loads(request.body)
            qr_code = data.get('qr_code')
            visit_amount = data.get('visit_amount')
            
            if not qr_code:
                return JsonResponse({
                    'success': False,
                    'error': 'QR code is required.'
                }, status=400)
            
            # Validate loyalty QR code
            loyalty_code = validate_and_extract_loyalty_code(qr_code)
            if not loyalty_code:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid loyalty QR code format.'
                }, status=400)
            
            # Scan the loyalty card
            result = scan_loyalty_card(loyalty_code, visit_amount)
            
            return JsonResponse(result)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data.'
            }, status=400)


@staff_member_required
def loyalty_card_detail(request, card_id):
    """View loyalty card details."""
    
    loyalty_card = get_object_or_404(LoyaltyCard, id=card_id)
    
    # Get recent transactions for this user
    recent_transactions = PointsTransaction.objects.filter(
        user=loyalty_card.user
    ).order_by('-created_at')[:10]
    
    context = {
        'loyalty_card': loyalty_card,
        'recent_transactions': recent_transactions,
    }
    
    return render(request, 'loyalty/admin/loyalty_card_detail.html', context)


@staff_member_required
def link_loyalty_card_user(request, card_id):
    """Form to link a loyalty card to a user."""
    
    loyalty_card = get_object_or_404(LoyaltyCard, id=card_id)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            try:
                from accounts.models import User
                user = User.objects.get(id=user_id)
                loyalty_card.link_to_user(user)
                messages.success(request, f'Card {loyalty_card.qr_code} successfully linked to {user.email}')
                return HttpResponseRedirect(reverse('admin:loyalty_loyaltycard_change', args=[card_id]))
            except User.DoesNotExist:
                messages.error(request, 'Selected user not found.')
    
    # Get all users for the dropdown
    from accounts.models import User
    users = User.objects.all().order_by('email')
    
    context = {
        'loyalty_card': loyalty_card,
        'users': users,
    }
    
    return render(request, 'loyalty/admin/link_loyalty_card_user.html', context)


@staff_member_required
def confirm_link_loyalty_card_user(request, card_id):
    """Confirm linking a loyalty card to a user."""
    
    loyalty_card = get_object_or_404(LoyaltyCard, id=card_id)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            try:
                from accounts.models import User
                user = User.objects.get(id=user_id)
                
                # Check if user already has a loyalty card
                if hasattr(user, 'loyalty_card') and user.loyalty_card:
                    messages.warning(request, f'User {user.email} already has loyalty card {user.loyalty_card.qr_code}')
                    return HttpResponseRedirect(reverse('admin:loyalty_loyaltycard_change', args=[card_id]))
                
                loyalty_card.link_to_user(user)
                messages.success(request, f'Card {loyalty_card.qr_code} successfully linked to {user.email} and activated!')
                return HttpResponseRedirect(reverse('admin:loyalty_loyaltycard_change', args=[card_id]))
            except User.DoesNotExist:
                messages.error(request, 'Selected user not found.')
    
    return HttpResponseRedirect(reverse('admin:loyalty_loyaltycard_change', args=[card_id]))
