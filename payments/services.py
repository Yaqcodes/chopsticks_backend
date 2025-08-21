import requests
import hmac
import hashlib
import json
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class PaystackError(Exception):
    """Base exception for Paystack errors."""
    pass


class PaystackAPIError(PaystackError):
    """Exception for Paystack API errors."""
    pass


class PaystackVerificationError(PaystackError):
    """Exception for Paystack verification errors."""
    pass


def naira_to_kobo(amount):
    """Convert Decimal Naira to integer kobo."""
    return int(amount * 100)


def kobo_to_naira(amount_kobo):
    """Convert integer kobo to Decimal Naira."""
    return Decimal(amount_kobo) / 100


class PaystackService:
    """Service class for Paystack API interactions."""
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = settings.PAYSTACK_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }
    
    def initialize_transaction(self, email, amount_kobo, order_number, callback_url):
        """Initialize a Paystack transaction."""
        print(f"Initializing transaction with URL: {self.base_url}/transaction/initialize")
        url = f"{self.base_url}/transaction/initialize"
        
        payload = {
            'email': email,
            'amount': amount_kobo,
            'callback_url': callback_url,
            'metadata': {
                'order_number': order_number,
                'custom_fields': [
                    {
                        'display_name': 'Order Number',
                        'variable_name': 'order_number',
                        'value': order_number
                    }
                ]
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status'):
                return {
                    'authorization_url': data['data']['authorization_url'],
                    'reference': data['data']['reference'],
                    'access_code': data['data']['access_code']
                }
            else:
                raise PaystackAPIError(f"Paystack error: {data.get('message', 'Unknown error')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API request failed: {str(e)}")
            raise PaystackAPIError(f"Failed to initialize transaction: {str(e)}")
    
    def verify_transaction(self, reference):
        """Verify a Paystack transaction."""
        url = f"{self.base_url}/transaction/verify/{reference}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status'):
                return data['data']
            else:
                raise PaystackVerificationError(f"Paystack verification error: {data.get('message', 'Unknown error')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verification request failed: {str(e)}")
            raise PaystackVerificationError(f"Failed to verify transaction: {str(e)}")
    
    def verify_webhook_signature(self, payload, signature):
        """Verify webhook signature for security."""
        if not signature:
            return False
        
        # Create HMAC SHA-512 hash
        expected_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    def get_transaction_status(self, reference):
        """Get transaction status from Paystack."""
        try:
            data = self.verify_transaction(reference)
            return data.get('status', 'unknown')
        except PaystackVerificationError:
            return 'failed'
