import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_phone_number(value):
    """Validate phone number format."""
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', value)
    
    # Check if it's a valid Nigerian phone number
    if len(digits_only) == 11 and digits_only.startswith('0'):
        # Convert to international format
        return '+234' + digits_only[1:]
    elif len(digits_only) == 13 and digits_only.startswith('234'):
        return '+' + digits_only
    elif len(digits_only) == 10 and digits_only.startswith('234'):
        return '+' + digits_only
    else:
        raise ValidationError(_('Please enter a valid Nigerian phone number.'))


def validate_nigerian_address(value):
    """Validate Nigerian address format."""
    
    # Basic validation - check for common Nigerian address components
    nigerian_indicators = [
        'street', 'avenue', 'road', 'close', 'drive', 'lane', 'way',
        'abuja', 'lagos', 'kano', 'ibadan', 'port harcourt', 'kaduna',
        'maiduguri', 'zaria', 'benin city', 'ilorin', 'oyo', 'jos',
        'calabar', 'enugu', 'katsina', 'akure', 'bauchi', 'gombe',
        'jalingo', 'damaturu', 'yola', 'birnin kebbi', 'sokoto',
        'minna', 'lokoja', 'markurdi', 'makurdi', 'otukpo', 'gboko'
    ]
    
    value_lower = value.lower()
    has_indicator = any(indicator in value_lower for indicator in nigerian_indicators)
    
    if not has_indicator:
        raise ValidationError(_('Please enter a valid Nigerian address.'))
    
    return value


def validate_postal_code(value):
    """Validate Nigerian postal code format."""
    
    # Nigerian postal codes are 6 digits
    if not re.match(r'^\d{6}$', value):
        raise ValidationError(_('Please enter a valid 6-digit postal code.'))
    
    return value


def validate_referral_code(value):
    """Validate referral code format."""
    
    # Referral codes should be 8 characters, alphanumeric
    if not re.match(r'^[A-Z0-9]{8}$', value):
        raise ValidationError(_('Referral code must be 8 characters long and contain only uppercase letters and numbers.'))
    
    return value


def validate_menu_item_name(value):
    """Validate menu item name."""
    
    # Check for minimum and maximum length
    if len(value) < 3:
        raise ValidationError(_('Menu item name must be at least 3 characters long.'))
    
    if len(value) > 100:
        raise ValidationError(_('Menu item name cannot exceed 100 characters.'))
    
    # Check for inappropriate content
    inappropriate_words = ['spam', 'test', 'demo', 'example']
    value_lower = value.lower()
    
    for word in inappropriate_words:
        if word in value_lower:
            raise ValidationError(_('Menu item name contains inappropriate content.'))
    
    return value


def validate_price(value):
    """Validate price value."""
    
    if value <= 0:
        raise ValidationError(_('Price must be greater than zero.'))
    
    if value > 10000:
        raise ValidationError(_('Price cannot exceed ₦10,000.'))
    
    return value


def validate_order_quantity(value):
    """Validate order item quantity."""
    
    if value < 1:
        raise ValidationError(_('Quantity must be at least 1.'))
    
    if value > 50:
        raise ValidationError(_('Quantity cannot exceed 50.'))
    
    return value


def validate_delivery_instructions(value):
    """Validate delivery instructions."""
    
    if len(value) > 500:
        raise ValidationError(_('Delivery instructions cannot exceed 500 characters.'))
    
    return value


def validate_customer_name(value):
    """Validate customer name."""
    
    # Check for minimum and maximum length
    if len(value) < 2:
        raise ValidationError(_('Name must be at least 2 characters long.'))
    
    if len(value) > 100:
        raise ValidationError(_('Name cannot exceed 100 characters.'))
    
    # Check for valid characters (letters, spaces, hyphens, apostrophes)
    if not re.match(r'^[a-zA-Z\s\'-]+$', value):
        raise ValidationError(_('Name can only contain letters, spaces, hyphens, and apostrophes.'))
    
    return value


def validate_email_domain(value):
    """Validate email domain for business use."""
    
    # Extract domain from email
    domain = value.split('@')[1].lower()
    
    # List of common free email providers
    free_email_providers = [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'aol.com', 'icloud.com', 'protonmail.com', 'tutanota.com'
    ]
    
    if domain in free_email_providers:
        # Allow free email providers but log for business accounts
        return value
    
    return value


def validate_promo_code(value):
    """Validate promotional code format."""
    
    # Promo codes should be 4-20 characters, alphanumeric
    if not re.match(r'^[A-Z0-9]{4,20}$', value):
        raise ValidationError(_('Promotional code must be 4-20 characters long and contain only uppercase letters and numbers.'))
    
    return value


def validate_points_amount(value):
    """Validate points amount."""
    
    if value < 0:
        raise ValidationError(_('Points amount cannot be negative.'))
    
    if value > 10000:
        raise ValidationError(_('Points amount cannot exceed 10,000.'))
    
    return value
