from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


def send_order_confirmation_email(order):
    """Send order confirmation email to customer."""
    
    subject = f"Order Confirmation - {order.order_number}"
    
    # Prepare email context
    context = {
        'order': order,
        'customer_name': order.get_customer_name(),
        'order_number': order.order_number,
        'total_amount': order.total_amount,
        'delivery_address': order.delivery_address or 'No address provided',
        'items': order.items.all()
    }
    
    # Render email templates
    html_message = render_to_string('emails/order_confirmation.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    recipient_email = order.get_customer_email()
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send order confirmation email: {str(e)}")
        return False


def send_order_status_update_email(order, new_status):
    """Send order status update email to customer."""
    
    subject = f"Order Status Update - {order.order_number}"
    
    context = {
        'order': order,
        'customer_name': order.get_customer_name(),
        'order_number': order.order_number,
        'new_status': new_status,
        'status_display': dict(order.STATUS_CHOICES).get(new_status, new_status)
    }
    
    html_message = render_to_string('emails/order_status_update.html', context)
    plain_message = strip_tags(html_message)
    
    recipient_email = order.get_customer_email()
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send order status update email: {str(e)}")
        return False


def send_password_reset_email(user, reset_url):
    """Send password reset email to user."""
    
    subject = "Password Reset Request - Chopsticks and Bowls"
    
    context = {
        'user': user,
        'reset_url': reset_url,
        'expiry_hours': 24
    }
    
    html_message = render_to_string('emails/password_reset.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")
        return False


def send_welcome_email(user):
    """Send welcome email to new user."""
    
    subject = "Welcome to Chopsticks and Bowls!"
    
    context = {
        'user': user,
        'referral_code': user.referral_code
    }
    
    html_message = render_to_string('emails/welcome.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send welcome email: {str(e)}")
        return False


def send_points_earned_email(user, points_earned, reason):
    """Send points earned notification email."""
    
    subject = f"You earned {points_earned} points!"
    
    context = {
        'user': user,
        'points_earned': points_earned,
        'reason': reason,
        'total_points': user.points.balance if hasattr(user, 'points') else 0
    }
    
    html_message = render_to_string('emails/points_earned.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send points earned email: {str(e)}")
        return False


def send_reward_redemption_email(user, reward):
    """Send reward redemption confirmation email."""
    
    subject = f"Reward Redeemed: {reward.name}"
    
    context = {
        'user': user,
        'reward': reward,
        'points_spent': reward.points_required
    }
    
    html_message = render_to_string('emails/reward_redemption.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send reward redemption email: {str(e)}")
        return False
