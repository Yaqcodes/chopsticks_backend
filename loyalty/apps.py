from django.apps import AppConfig


class LoyaltyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'loyalty'
    verbose_name = 'Loyalty & Rewards'
    
    def ready(self):
        """Import signals when the app is ready."""
        import loyalty.signals