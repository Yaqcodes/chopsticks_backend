import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Payment
from .services import PaystackService, PaystackError, PaystackAPIError, PaystackVerificationError
from orders.models import Order
from loyalty.services import award_points_for_order
from django.conf import settings
from .services import kobo_to_naira

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny for guest checkout
def initialize_payment(request):
    """Initialize payment for an order."""
    try:
        order_id = request.data.get('order_id')
        if not order_id:
            return Response({'error': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the order
        order = get_object_or_404(Order, id=order_id)
        
        # Check if order is pending payment
        if order.payment_status != 'pending':
            return Response({'error': 'Order is not pending payment'}, status=status.HTTP_400_BAD_REQUEST)
        
        # For authenticated users, verify they own the order
        if order.user and request.user.is_authenticated:
            if order.user != request.user:
                return Response({'error': 'You can only pay for your own orders'}, status=status.HTTP_403_FORBIDDEN)
        # For guest orders, no user verification needed
        
        # Initialize Paystack transaction
        paystack = PaystackService()
        result = paystack.initialize_transaction(
            email=order.get_customer_email(),
            amount_kobo=order.get_paystack_amount(),
            order_number=order.order_number,
            callback_url=settings.PAYSTACK_CALLBACK_URL
        )
        
        # Create Payment record
        payment = Payment.objects.create(
            reference=result['reference'],
            order=order,
            amount=order.total_amount,
            amount_kobo=order.get_paystack_amount(),
            access_code=result['access_code'],
            authorization_url=result['authorization_url'],
            customer_email=order.get_customer_email()
        )
        
        # Update order with Paystack reference
        order.paystack_reference = result['reference']
        order.paystack_access_code = result['access_code']
        order.save()
        
        return Response({
            'authorization_url': result['authorization_url'],
            'reference': result['reference'],
            'access_code': result['access_code']
        })
        
    except PaystackAPIError as e:
        logger.error(f"Paystack API error: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Payment initialization failed: {str(e)}")
        return Response({'error': 'Payment initialization failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # Allow public access for payment verification
def verify_payment(request, reference):
    """Verify payment status."""
    try:
        # Get payment record
        payment = get_object_or_404(Payment, reference=reference)
        
        # Verify with Paystack
        paystack = PaystackService()
        result = paystack.verify_transaction(reference)
        
        # Update payment status
        payment.paystack_status = result.get('status', '')
        payment.verified_at = timezone.now()
        
        if result.get('status') == 'success':
            payment.status = 'success'
            
            # Update order status
            order = payment.order
            order.payment_status = 'paid'
            order.payment_verified_at = timezone.now()
            order.save()
            
            # Award loyalty points
            if order.user:
                award_points_for_order(order)
            
        else:
            payment.status = 'failed'
            payment.order.payment_status = 'failed'
            payment.order.save()
        
        payment.save()
        
        return Response({
            'status': payment.status,
            'paystack_status': payment.paystack_status,
            'order_status': payment.order.payment_status,
            'order_id': payment.order.id,
            'order_number': payment.order.order_number,
            'amount': str(payment.amount),
            'currency': payment.currency
        })
        
    except PaystackVerificationError as e:
        logger.error(f"Paystack verification error: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        return Response({'error': 'Payment verification failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(View):
    """Handle Paystack webhook events."""
    
    def post(self, request, *args, **kwargs):
        try:
            # Get webhook signature
            signature = request.headers.get('X-Paystack-Signature')
            if not signature:
                return HttpResponse('Missing signature', status=400)
            
            # Verify webhook signature
            paystack = PaystackService()
            if not paystack.verify_webhook_signature(request.body.decode('utf-8'), signature):
                return HttpResponse('Invalid signature', status=400)
            
            # Parse webhook data
            data = json.loads(request.body)
            event = data.get('event')
            
            if event == 'charge.success':
                # Handle successful payment
                transaction_data = data.get('data', {})
                reference = transaction_data.get('reference')
                
                if reference:
                    # Get or create payment record
                    payment, created = Payment.objects.get_or_create(
                        reference=reference,
                        defaults={
                            'order': None,  # Will be set below
                            'amount': kobo_to_naira(transaction_data.get('amount', 0)),
                            'amount_kobo': transaction_data.get('amount', 0),
                            'customer_email': transaction_data.get('customer', {}).get('email', ''),
                            'status': 'success',
                            'paystack_status': 'success',
                            'verified_at': timezone.now()
                        }
                    )
                    
                    if not created:
                        # Update existing payment
                        payment.status = 'success'
                        payment.paystack_status = 'success'
                        payment.verified_at = timezone.now()
                        payment.save()
                    
                    # Update order if payment exists
                    if payment.order:
                        order = payment.order
                        order.payment_status = 'paid'
                        order.payment_verified_at = timezone.now()
                        order.save()
                        
                        # Award loyalty points
                        if order.user:
                            award_points_for_order(order)
                    
                    logger.info(f"Webhook processed successfully for reference: {reference}")
            
            return HttpResponse('OK', status=200)
            
        except json.JSONDecodeError:
            return HttpResponse('Invalid JSON', status=400)
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return HttpResponse('Internal error', status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def payment_callback(request):
    """
    Handle Paystack payment callback redirects.
    This is called when users are redirected back from Paystack after payment.
    """
    try:
        # Get reference from query parameters
        reference = request.GET.get('reference')
        trxref = request.GET.get('trxref')
        
        if not reference:
            return Response({
                'error': 'Missing payment reference',
                'message': 'Payment reference not found in callback'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify the payment
        paystack = PaystackService()
        result = paystack.verify_transaction(reference)
        
        # Get payment record
        payment = get_object_or_404(Payment, reference=reference)
        
        # Update payment status
        payment.paystack_status = result.get('status', '')
        payment.verified_at = timezone.now()
        
        if result.get('status') == 'success':
            payment.status = 'success'
            payment.order.payment_status = 'paid'
            payment.order.payment_verified_at = timezone.now()
            payment.order.save()
            
            # Award loyalty points
            if payment.order.user:
                award_points_for_order(payment.order)
            
            return Response({
                'status': 'success',
                'message': 'Payment completed successfully',
                'order_number': payment.order.order_number,
                'amount': str(payment.amount),
                'reference': reference
            })
        else:
            payment.status = 'failed'
            payment.order.payment_status = 'failed'
            payment.order.save()
            
            return Response({
                'status': 'failed',
                'message': 'Payment verification failed',
                'reference': reference
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Payment callback error: {str(e)}")
        return Response({
            'error': 'Payment callback processing failed',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
