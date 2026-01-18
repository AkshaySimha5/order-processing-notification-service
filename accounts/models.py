from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model.

    Role handling:
    - Customer: is_staff=False, is_superuser=False
    - Admin: is_staff=True, is_superuser=False
    - Super Admin: is_staff=True, is_superuser=True
    """

    # username is already unique in AbstractUser
    # password handling is managed by Django

    # Contact fields and notification preferences
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)

    # Verification flags (useful to gate sending SMS/email)
    email_verified = models.BooleanField(default=False)
    sms_verified = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.username
