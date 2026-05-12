"""
Create a staff user for Zmall admin (not a superuser).
User can access /zmall-admin/ only; linked via User.businesses to Zmall RestaurantSettings.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import RestaurantSettings

User = get_user_model()

EMAIL = "info.zmallng@gmail.com"
FIRST_NAME = "Zmall"
LAST_NAME = "Admin"
DEFAULT_PASSWORD = "YNWA/cr7"


class Command(BaseCommand):
    help = "Create a staff user for Zmall admin (is_staff=True, is_superuser=False), linked to Zmall business."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Password for the user (default used if not provided).",
        )

    def handle(self, *args, **options):
        password = options["password"]

        zmall = RestaurantSettings.objects.filter(domain__icontains="zmall").first()
        if not zmall:
            self.stderr.write(
                self.style.ERROR(
                    "Zmall tenant not found. Create a RestaurantSettings with domain containing 'zmall' (e.g. zmall.ng)."
                )
            )
            return

        user, created = User.objects.get_or_create(
            email=EMAIL,
            defaults={
                "username": EMAIL,
                "first_name": FIRST_NAME,
                "last_name": LAST_NAME,
                "is_staff": True,
                "is_superuser": False,
                "is_active": True,
            },
        )
        if not created:
            user.first_name = FIRST_NAME
            user.last_name = LAST_NAME
            user.is_staff = True
            user.is_superuser = False
            user.is_active = True
            user.save(update_fields=["first_name", "last_name", "is_staff", "is_superuser", "is_active"])

        user.set_password(password)
        user.save(update_fields=["password"])

        if not user.businesses.filter(id=zmall.id).exists():
            user.businesses.add(zmall)
            self.stdout.write(self.style.SUCCESS(f"Linked user to Zmall business (id={zmall.id})."))

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Zmall admin user: {EMAIL}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated Zmall admin user: {EMAIL}"))

        self.stdout.write(f"  Login at: /zmall-admin/")
        self.stdout.write(f"  Email: {EMAIL}")
