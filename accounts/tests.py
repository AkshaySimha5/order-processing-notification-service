from django.urls import reverse # to look up URL paths by name
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .serializers import UserRegistrationSerializer

User = get_user_model()

# Model tests
class UserModelTest(TestCase):
    def test_create_user_with_custom_fields(self):
        user = User.objects.create_user(
            username="testuser",
            password="password123",
        )
        self.assertFalse(user.email_verified)

# Serializers tests
class SerializerTest(TestCase):
    def test_password_min_length_validation(self):
        """too short password"""
        data = {"username": "short", "password": "123"}
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

# API integration tests
class AuthAPITests(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.user_payload = {"username": "apiuser", "email": "apiuser@example.com", "password": "securepassword123"}

    def test_registration_and_token_generation(self):
        """Test registration and getting tokens back."""
        response = self.client.post(self.register_url, self.user_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify the tokens are in the response (if you updated your serializer)
        self.assertIn('tokens', response.data)

    def test_login_flow(self):
        """Test if a registered user can log in and get a JWT."""
        User.objects.create_user(**self.user_payload)
        login_data = {"username": self.user_payload["username"], "password": self.user_payload["password"]}
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)