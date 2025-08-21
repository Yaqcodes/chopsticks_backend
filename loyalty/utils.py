import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings


def generate_qr_code_image(qr_code_text, size=10):
    """
    Generate a QR code image from text.
    
    Args:
        qr_code_text (str): The text to encode in the QR code
        size (int): The size of the QR code (default: 10)
    
    Returns:
        BytesIO: The QR code image as bytes
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=4,
    )
    qr.add_data(qr_code_text)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer


def generate_loyalty_card_qr_code(loyalty_card):
    """
    Generate QR code image for a loyalty card.
    
    Args:
        loyalty_card: LoyaltyCard instance
    
    Returns:
        BytesIO: The QR code image as bytes
    """
    # Create QR code text with loyalty card information
    qr_text = f"LOYALTY:{loyalty_card.qr_code}"
    
    return generate_qr_code_image(qr_text)


def create_qr_code_file(loyalty_card, filename=None):
    """
    Create a QR code image file for a loyalty card.
    
    Args:
        loyalty_card: LoyaltyCard instance
        filename (str): Optional filename for the image
    
    Returns:
        ContentFile: The QR code image as a file
    """
    if not filename:
        filename = f"loyalty_card_{loyalty_card.qr_code}.png"
    
    qr_image = generate_loyalty_card_qr_code(loyalty_card)
    
    return ContentFile(qr_image.getvalue(), filename)
