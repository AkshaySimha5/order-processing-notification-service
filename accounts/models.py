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

    def __str__(self) -> str:
        return self.username
