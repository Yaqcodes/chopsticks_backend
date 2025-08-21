from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import LoyaltyCard


@receiver(post_save, sender=LoyaltyCard)
def loyalty_card_post_save(sender, instance, created, **kwargs):
    """Automatically handle loyalty card activation/deactivation based on user assignment."""
    if created:
        # New card created
        if instance.user:
            # If user is assigned during creation, activate the card
            instance.is_active = True
            instance.save(update_fields=['is_active'])
    else:
        # Existing card updated
        if instance.user and not instance.is_active:
            # If user is assigned but card is inactive, activate it
            instance.is_active = True
            instance.save(update_fields=['is_active'])
        elif not instance.user and instance.is_active:
            # If user is unassigned but card is active, deactivate it
            instance.is_active = False
            instance.save(update_fields=['is_active'])


@receiver(post_delete, sender=LoyaltyCard)
def loyalty_card_post_delete(sender, instance, **kwargs):
    """Handle cleanup when loyalty card is deleted."""
    # Any additional cleanup logic can be added here
    pass
