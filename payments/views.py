import json
import logging
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from core.utils import get_business_from_request, get_frontend_url_from_business
from .models import Payment
from .services import PaystackService, PaystackError, PaystackAPIError, PaystackVerificationError
from orders.models import Order
from loyalty.services import award_points_for_order
from .services import kobo_to_naira

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny for guest checkout
def initialize_payment(request):
    """Initialize payment for an order."""
    try:
        restaurant_settings = get_business_from_request(request)
        order_id = request.data.get('order_id')
        if not order_id:
            return Response({'error': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the order
        order = get_object_or_404(Order, id=order_id)
        if order.restaurant_settings != restaurant_settings:
            return Response({'error': 'Order does not belong to this business'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if order is pending payment
        if order.payment_status != 'pending':
            return Response({'error': 'Order is not pending payment'}, status=status.HTTP_400_BAD_REQUEST)
        
        # For authenticated users, verify they own the order
        if order.user and request.user.is_authenticated:
            if order.user != request.user:
                return Response({'error': 'You can only pay for your own orders'}, status=status.HTTP_403_FORBIDDEN)
        # For guest orders, no user verification needed
        
        if not restaurant_settings.paystack_secret_key:
            return Response({'error': 'Paystack secret key not configured for this business'}, status=status.HTTP_400_BAD_REQUEST)
        if not restaurant_settings.paystack_public_key:
            return Response({'error': 'Paystack public key not configured for this business'}, status=status.HTTP_400_BAD_REQUEST)

        callback_url = request.build_absolute_uri('/api/payments/callback/')

        # Initialize Paystack transaction
        paystack = PaystackService(
            secret_key=restaurant_settings.paystack_secret_key,
            public_key=restaurant_settings.paystack_public_key,
        )
        result = paystack.initialize_transaction(
            email=order.get_customer_email(),
            amount_kobo=order.get_paystack_amount(),
            order_number=order.order_number,
            callback_url=callback_url
        )
        
        # Create Payment record and update order atomically
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Lock order to prevent concurrent payment initialization
                order = Order.objects.select_for_update().get(id=order.id)
                
                # Check if payment already initialized
                if order.paystack_reference:
                    logger.warning(f"Order {order.id} already has payment reference: {order.paystack_reference}")
                    # Return existing payment info
                    existing_payment = Payment.objects.filter(order=order).first()
                    if existing_payment:
                        return Response({
                            'authorization_url': existing_payment.authorization_url,
                            'reference': existing_payment.reference,
                            'access_code': existing_payment.access_code,
                            'public_key': restaurant_settings.paystack_public_key
                        })
                
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
                
                # Update order with Paystack reference atomically
                order.paystack_reference = result['reference']
                order.paystack_access_code = result['access_code']
                order.save()
        except Exception as e:
            logger.error(f"Error initializing payment in transaction: {str(e)}")
            raise
        
        return Response({
            'authorization_url': result['authorization_url'],
            'reference': result['reference'],
            'access_code': result['access_code'],
            'public_key': restaurant_settings.paystack_public_key
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
        restaurant_settings = get_business_from_request(request)
        # Get payment record
        payment = get_object_or_404(Payment, reference=reference)
        if payment.order.restaurant_settings != restaurant_settings:
            return Response({'error': 'Payment does not belong to this business'}, status=status.HTTP_403_FORBIDDEN)
        
        if not restaurant_settings.paystack_secret_key:
            return Response({'error': 'Paystack secret key not configured for this business'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify with Paystack
        paystack = PaystackService(secret_key=restaurant_settings.paystack_secret_key)
        result = paystack.verify_transaction(reference)
        
        # Update payment and order status atomically
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Lock payment and order rows to prevent concurrent updates
                payment = Payment.objects.select_for_update().get(id=payment.id)
                order = payment.order
                order = Order.objects.select_for_update().get(id=order.id)
                
                # Update payment status
                payment.paystack_status = result.get('status', '')
                payment.verified_at = timezone.now()
                
                if result.get('status') == 'success':
                    payment.status = 'success'
                    
                    # Update order status atomically
                    order.payment_status = 'paid'
                    order.payment_verified_at = timezone.now()
                    order.save()
                    
                    # Award loyalty points (within transaction)
                    if order.user:
                        award_points_for_order(order)
                    
                else:
                    payment.status = 'failed'
                    order.payment_status = 'failed'
                    order.save()
                
                payment.save()
        except Exception as e:
            logger.error(f"Error updating payment status in transaction: {str(e)}")
            raise
        
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
    """
    Handle Paystack webhook events.
    
    Note: Paystack webhooks come from Paystack's servers, so we identify
    the business from the payment reference in the webhook data, not from request headers.
    """
    
    def post(self, request, *args, **kwargs):
        try:
            # Get webhook signature
            signature = request.headers.get('X-Paystack-Signature')
            if not signature:
                return HttpResponse('Missing signature', status=400)
            
            # Parse webhook data first to get reference and identify business
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return HttpResponse('Invalid JSON', status=400)
            
            event = data.get('event')
            
            if event == 'charge.success':
                # Handle successful payment
                transaction_data = data.get('data', {})
                reference = transaction_data.get('reference')
                
                if not reference:
                    logger.error("Webhook missing reference in transaction data")
                    return HttpResponse('Missing reference', status=400)
                
                # Identify business from payment reference (webhooks don't have frontend headers)
                try:
                    payment = Payment.objects.get(reference=reference)
                    restaurant_settings = payment.order.restaurant_settings
                    logger.info(f"Identified business from webhook reference: {restaurant_settings.domain}")
                except Payment.DoesNotExist:
                    logger.error("Payment not found for reference: %s", reference)
                    return HttpResponse('Payment not found', status=404)
                
                # Verify webhook signature using the identified business's secret
                webhook_secret = restaurant_settings.paystack_webhook_secret or restaurant_settings.paystack_secret_key
                if not restaurant_settings.paystack_secret_key:
                    logger.error("Paystack secret key not configured for business: %s", restaurant_settings.domain)
                    return HttpResponse('Paystack secret key not configured for this business', status=400)
                
                paystack = PaystackService(
                    secret_key=restaurant_settings.paystack_secret_key,
                    webhook_secret=webhook_secret,
                )
                if not paystack.verify_webhook_signature(request.body.decode('utf-8'), signature):
                    logger.error("Invalid webhook signature for reference: %s", reference)
                    return HttpResponse('Invalid signature', status=400)

                # Update payment and order status atomically
                from django.db import transaction
                
                try:
                    with transaction.atomic():
                        # Lock payment and order rows to prevent concurrent updates
                        payment = Payment.objects.select_for_update().get(id=payment.id)
                        order = payment.order
                        order = Order.objects.select_for_update().get(id=order.id)
                        
                        # Prevent duplicate processing
                        if payment.status == 'success':
                            logger.warning(f"Payment {reference} already processed as success")
                            return HttpResponse('Already processed', status=200)
                        
                        # Update payment status
                        payment.status = 'success'
                        payment.paystack_status = 'success'
                        payment.verified_at = timezone.now()
                        payment.save()
                        
                        # Update order status atomically
                        order.payment_status = 'paid'
                        order.payment_verified_at = timezone.now()
                        order.save()
                        
                        # Award loyalty points (within transaction)
                        if order.user:
                            award_points_for_order(order)
                        
                        logger.info("Webhook processed successfully for reference: %s", reference)
                except Exception as e:
                    logger.error(f"Error processing webhook in transaction: {str(e)}")
                    # Don't return error to Paystack - we'll retry later
                    raise
                
                logger.info("Webhook processed successfully for reference: %s", reference)
            
            return HttpResponse('OK', status=200)
            
        except json.JSONDecodeError:
            return HttpResponse('Invalid JSON', status=400)
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return HttpResponse('Internal error', status=500)


@csrf_exempt
def payment_callback(request):
    """
    Handle Paystack payment callback redirects.
    This is called when users are redirected back from Paystack after payment.
    Note: Using regular Django view instead of @api_view to properly handle redirects.
    
    Note: Paystack callbacks come from checkout.paystack.com, so we identify
    the business from the payment reference, not from request headers.
    """
    try:
        logger.info(f"Payment callback received. Host: {request.get_host()}, Path: {request.path}, Query: {request.GET}")
        
        # Get reference from query parameters first
        reference = request.GET.get('reference')
        trxref = request.GET.get('trxref')
        
        logger.info(f"Payment callback - reference: {reference}, trxref: {trxref}")
        
        if not reference:
            logger.warning("Payment callback missing reference parameter")
            return JsonResponse({
                'error': 'Missing payment reference',
                'message': 'Payment reference not found in callback'
            }, status=400)
        
        # Identify business from payment reference (Paystack callbacks don't have frontend headers)
        try:
            payment = Payment.objects.get(reference=reference)
            restaurant_settings = payment.order.restaurant_settings
            logger.info(f"Identified business from payment reference: {restaurant_settings.domain}")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for reference: {reference}")
            return JsonResponse({
                'error': 'Payment not found',
                'message': f'Payment with reference {reference} does not exist'
            }, status=404)
        
        # Verify the payment
        if not restaurant_settings.paystack_secret_key:
            logger.error("Paystack secret key not configured")
            return JsonResponse({'error': 'Paystack secret key not configured for this business'}, status=400)
        
        logger.info(f"Verifying payment with reference: {reference}")
        paystack = PaystackService(secret_key=restaurant_settings.paystack_secret_key)
        result = paystack.verify_transaction(reference)
        logger.info(f"Payment verification result: {result.get('status')}")
        
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
            
            # Redirect to frontend success page
            # Use order's restaurant_settings to get correct frontend URL (multi-tenant)
            # Pass request to preserve protocol/subdomain/port from original request
            frontend_url = get_frontend_url_from_business(payment.order.restaurant_settings, request=request)
            frontend_url = frontend_url.rstrip('/')
            redirect_url = f"{frontend_url}/payment/success?reference={reference}"
            logger.info(f"Payment successful. Redirecting to frontend: {redirect_url} (business: {payment.order.restaurant_settings.domain})")
            
            # Create redirect response
            response = HttpResponseRedirect(redirect_url)
            logger.info(f"Redirect response created: {response.status_code}, Location: {response.get('Location', 'N/A')}")
            return response
        else:
            payment.status = 'failed'
            payment.order.payment_status = 'failed'
            payment.order.save()
            
            # Redirect to frontend success page with failed status
            # Use order's restaurant_settings to get correct frontend URL (multi-tenant)
            # Pass request to preserve protocol/subdomain/port from original request
            frontend_url = get_frontend_url_from_business(payment.order.restaurant_settings, request=request)
            frontend_url = frontend_url.rstrip('/')
            redirect_url = f"{frontend_url}/payment/success?reference={reference}&status=failed"
            logger.info(f"Payment failed. Redirecting to frontend: {redirect_url} (business: {payment.order.restaurant_settings.domain})")
            return HttpResponseRedirect(redirect_url)
            
    except Exception as e:
        logger.error(f"Payment callback error: {str(e)}", exc_info=True)
        # Even on error, try to redirect to frontend with error status
        reference = request.GET.get('reference', '')
        if reference:
            try:
                # Try to get frontend URL from payment/order if available
                try:
                    payment = Payment.objects.get(reference=reference)
                    frontend_url = get_frontend_url_from_business(payment.order.restaurant_settings, request=request)
                except (Payment.DoesNotExist, AttributeError):
                    # If payment doesn't exist, we can't identify business - log and return error
                    logger.error(f"Cannot redirect: Payment {reference} not found, cannot identify business")
                    return JsonResponse({
                        'error': 'Payment callback processing failed',
                        'message': 'Cannot identify business for redirect'
                    }, status=500)
                
                frontend_url = frontend_url.rstrip('/')
                redirect_url = f"{frontend_url}/payment/success?reference={reference}&error=1"
                logger.info(f"Error occurred, redirecting to frontend: {redirect_url}")
                return HttpResponseRedirect(redirect_url)
            except Exception as redirect_error:
                logger.error(f"Failed to redirect on error: {str(redirect_error)}")
                # Re-raise if business identification fails (strict multi-tenancy)
                raise
        
        return JsonResponse({
            'error': 'Payment callback processing failed',
            'message': str(e)
        }, status=500)
