"""
Tests for the accounts app - 20 tests.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from accounts.serializers import UserRegistrationSerializer


User = get_user_model()


# ============================================================================
# MODEL TESTS (5 tests)
# ============================================================================

class TestUserModel:
    """Tests for the custom User model."""

    def test_create_user(self, db):
        """Test creating a regular user with all attributes."""
        user = User.objects.create_user(
            username="newuser",
            email="newuser@example.com",
            password="password123",
        )
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("password123")
        assert str(user) == user.username

    def test_user_notification_defaults(self, db):
        """Test default notification preferences and verification flags."""
        user = User.objects.create_user(
            username="defaultuser",
            email="default@example.com",
            password="password123",
        )
        assert user.notify_email is True
        assert user.notify_sms is False
        assert user.email_verified is False
        assert user.sms_verified is False

    def test_user_phone_number(self, user):
        """Test user phone number field."""
        assert user.phone_number == "+1234567890"

    def test_create_superuser(self, db):
        """Test creating a superuser."""
        superuser = User.objects.create_superuser(
            username="super",
            email="super@example.com",
            password="superpass123",
        )
        assert superuser.is_staff is True
        assert superuser.is_superuser is True

    def test_user_roles(self, user, admin_user, superuser):
        """Test different user roles."""
        # Customer role
        assert user.is_staff is False and user.is_superuser is False
        # Admin role
        assert admin_user.is_staff is True and admin_user.is_superuser is False
        # Super admin role
        assert superuser.is_staff is True and superuser.is_superuser is True


# ============================================================================
# SERIALIZER TESTS (5 tests)
# ============================================================================

class TestUserRegistrationSerializer:
    """Tests for UserRegistrationSerializer."""

    def test_valid_registration_data(self, db):
        """Test serializer with valid data."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()

    def test_password_write_only(self, db):
        """Test that password is not included in representation."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        }
        serializer = UserRegistrationSerializer(data=data)
        serializer.is_valid()
        user = serializer.save()
        representation = serializer.to_representation(user)
        assert "password" not in representation

    def test_tokens_included_in_response(self, db):
        """Test that tokens are included in serializer response."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        }
        serializer = UserRegistrationSerializer(data=data)
        serializer.is_valid()
        user = serializer.save()
        representation = serializer.to_representation(user)
        assert "tokens" in representation
        assert "access" in representation["tokens"]
        assert "refresh" in representation["tokens"]

    def test_password_min_length(self, db):
        """Test password minimum length validation."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "short",
        }
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "password" in serializer.errors

    def test_missing_required_fields(self, db):
        """Test serializer with missing required fields."""
        data = {"username": "newuser"}
        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "email" in serializer.errors
        assert "password" in serializer.errors


# ============================================================================
# VIEW TESTS (10 tests)
# ============================================================================

class TestUserRegistrationView:
    """Tests for the user registration endpoint."""

    def test_register_user_success(self, api_client, db):
        """Test successful user registration."""
        url = reverse("register")
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "tokens" in response.data
        assert User.objects.filter(username="newuser").exists()

    def test_register_user_missing_password(self, api_client, db):
        """Test registration fails without password."""
        url = reverse("register")
        data = {"username": "newuser", "email": "newuser@example.com"}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_username(self, api_client, user):
        """Test registration fails with duplicate username."""
        url = reverse("register")
        data = {"username": user.username, "email": "different@example.com", "password": "password123"}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_short_password(self, api_client, db):
        """Test registration fails with short password."""
        url = reverse("register")
        data = {"username": "newuser", "email": "newuser@example.com", "password": "short"}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLoginView:
    """Tests for the login endpoint."""

    def test_login_success(self, api_client, user, user_data):
        """Test successful login returns tokens."""
        url = reverse("login")
        data = {"username": user_data["username"], "password": user_data["password"]}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client, user, user_data):
        """Test login fails with wrong password."""
        url = reverse("login")
        data = {"username": user_data["username"], "password": "wrongpassword"}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client, db):
        """Test login fails for nonexistent user."""
        url = reverse("login")
        data = {"username": "nonexistent", "password": "password123"}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    def test_token_refresh_success(self, api_client, user):
        """Test successful token refresh."""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        url = reverse("token_refresh")
        response = api_client.post(url, {"refresh": str(refresh)}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_token_refresh_invalid_token(self, api_client, db):
        """Test token refresh fails with invalid token."""
        url = reverse("token_refresh")
        response = api_client.post(url, {"refresh": "invalid-token"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_user_serializer(self, db):
        """Test that serializer creates user correctly."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        }
        serializer = UserRegistrationSerializer(data=data)
        serializer.is_valid()
        user = serializer.save()
        assert User.objects.filter(username="newuser").exists()
        assert user.check_password("password123")
