"""
Tests for the payments app - 20 tests.
Covers models, serializers, views, services, and provider client.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied

from orders.models import Order
from payments.models import Payment, WebhookEvent
from payments.api.serializers import (
    PaymentGenerateSerializer,
    PaymentConfirmSerializer,
    PaymentResponseSerializer,
)
from payments.services.payment_service import PaymentService, PaymentRequest
from payments.clients.provider import PaymentProviderClient, PaymentProviderError


User = get_user_model()


# ============================================================================
# MODEL TESTS (5 tests)
# ============================================================================

class TestPaymentModel:
    """Tests for the Payment model."""

    def test_payment_creation_and_defaults(self, order):
        """Test creating a payment with defaults."""
        payment = Payment.objects.create(order=order, amount=Decimal("10.00"))
        assert payment.pk is not None
        assert payment.status == Payment.Status.INITIATED
        assert payment.created_at is not None
        assert str(payment) == f"Payment for Order #{order.id}"

    def test_payment_status_choices(self, order):
        """Test all payment status choices."""
        for s in [Payment.Status.INITIATED, Payment.Status.SUCCESS, Payment.Status.FAILED]:
            payment = Payment.objects.create(order=order, amount=Decimal("10.00"), status=s)
            assert payment.status == s
            payment.delete()

    def test_payment_uropay_fields(self, payment_with_uropay):
        """Test UroPay-specific fields."""
        assert payment_with_uropay.uro_pay_order_id == "UROPAY-123456"
        assert payment_with_uropay.upi_string is not None


class TestWebhookEventModel:
    """Tests for the WebhookEvent model."""

    def test_webhook_event_creation(self, db):
        """Test creating a webhook event."""
        event = WebhookEvent.objects.create(webhook_id="WEBHOOK-123", payload={"test": "data"})
        assert event.pk is not None
        assert "WEBHOOK-123" in str(event)

    def test_webhook_id_unique(self, db):
        """Test webhook_id uniqueness."""
        WebhookEvent.objects.create(webhook_id="UNIQUE-ID", payload={})
        with pytest.raises(Exception):
            WebhookEvent.objects.create(webhook_id="UNIQUE-ID", payload={})


# ============================================================================
# SERIALIZER TESTS (4 tests)
# ============================================================================

class TestPaymentSerializers:
    """Tests for payment serializers."""

    def test_payment_generate_valid(self, db):
        """Test PaymentGenerateSerializer with valid data."""
        data = {"order_id": 1, "vpa": "test@upi", "vpaName": "Test", "customerName": "Test", "customerEmail": "test@example.com"}
        serializer = PaymentGenerateSerializer(data=data)
        assert serializer.is_valid()

    def test_payment_generate_invalid(self, db):
        """Test PaymentGenerateSerializer validation errors."""
        # Invalid order_id
        assert not PaymentGenerateSerializer(data={"order_id": 0, "vpa": "test@upi", "vpaName": "Test", "customerName": "Test", "customerEmail": "test@example.com"}).is_valid()
        # Invalid email
        assert not PaymentGenerateSerializer(data={"order_id": 1, "vpa": "test@upi", "vpaName": "Test", "customerName": "Test", "customerEmail": "invalid"}).is_valid()

    def test_payment_confirm_serializer(self, db):
        """Test PaymentConfirmSerializer."""
        assert PaymentConfirmSerializer(data={"order_id": 1, "referenceNumber": "REF-123"}).is_valid()
        assert not PaymentConfirmSerializer(data={"order_id": 1}).is_valid()

    def test_payment_response_serializer(self, payment_with_uropay):
        """Test PaymentResponseSerializer."""
        data = PaymentResponseSerializer(payment_with_uropay).data
        assert data["id"] == payment_with_uropay.pk
        assert data["uro_pay_order_id"] == payment_with_uropay.uro_pay_order_id


# ============================================================================
# SERVICE TESTS (6 tests)
# ============================================================================

class TestPaymentService:
    """Tests for PaymentService methods."""

    def test_create_payment_success(self, db, order, user, mock_payment_provider):
        """Test successful payment creation."""
        request = PaymentRequest(order_id=order.id, user_id=user.id, provider_token="valid-token")
        with patch("payments.services.payment_service.PaymentProviderClient") as MockClient:
            MockClient.return_value = mock_payment_provider
            payment = PaymentService.create_payment(request)
            assert payment.status == Payment.Status.SUCCESS
            order.refresh_from_db()
            assert order.status == Order.Status.PAID

    def test_create_payment_invalid_order(self, db, user):
        """Test payment creation with invalid order."""
        with pytest.raises(ValidationError):
            PaymentService.create_payment(PaymentRequest(order_id=99999, user_id=user.id, provider_token="token"))

    def test_create_payment_wrong_user(self, db, order, another_user):
        """Test payment creation by wrong user."""
        with pytest.raises(PermissionDenied):
            PaymentService.create_payment(PaymentRequest(order_id=order.id, user_id=another_user.id, provider_token="token"))

    def test_generate_payment_success(self, db, order, user, mock_payment_provider):
        """Test successful payment generation."""
        with patch("payments.services.payment_service.PaymentProviderClient") as MockClient:
            MockClient.return_value = mock_payment_provider
            payment = PaymentService.generate_payment(
                user_id=user.id, order_id=order.id, vpa="test@upi", vpaName="Test",
                customerName="Test Customer", customerEmail="test@example.com",
            )
            assert payment.uro_pay_order_id == "UROPAY-MOCK-123"

    def test_confirm_payment_success(self, db, order, user, payment_with_uropay, mock_payment_provider):
        """Test successful payment confirmation."""
        payment_with_uropay.order = order
        payment_with_uropay.save()
        with patch("payments.services.payment_service.PaymentProviderClient") as MockClient:
            MockClient.return_value = mock_payment_provider
            payment = PaymentService.confirm_payment(user_id=user.id, order_id=order.id, reference_number="UTR123456")
            assert payment.status == Payment.Status.SUCCESS

    def test_confirm_payment_no_initiated(self, db, order, user):
        """Test confirmation without initiated payment."""
        with pytest.raises(ValidationError):
            PaymentService.confirm_payment(user_id=user.id, order_id=order.id, reference_number="UTR123456")


# ============================================================================
# PROVIDER CLIENT TESTS (3 tests)
# ============================================================================

class TestPaymentProviderClient:
    """Tests for PaymentProviderClient."""

    def test_client_initialization(self, settings):
        """Test client initialization."""
        settings.PAYMENT_PROVIDER_API_KEY = "test-key"
        settings.PAYMENT_PROVIDER_BASE_URL = "https://api.test.com"
        client = PaymentProviderClient()
        assert client.api_key == "test-key"

    def test_uropay_headers(self, settings):
        """Test UroPay headers generation."""
        settings.UROPAY_API_KEY = "uro-api-key"
        settings.UROPAY_SECRET = "uro-secret"
        client = PaymentProviderClient()
        headers = client._uropay_headers()
        assert headers["X-API-KEY"] == "uro-api-key"

    @patch("payments.clients.provider.requests.request")
    def test_uropay_generate_success(self, mock_request, settings):
        """Test successful UroPay generate."""
        settings.UROPAY_API_KEY = "uro-key"
        settings.UROPAY_SECRET = "uro-secret"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"uroPayOrderId": "URO-123", "upiString": "upi://pay", "qrCode": "qrcode"}}
        mock_request.return_value = mock_response
        result = PaymentProviderClient().uropay_generate(
            vpa="test@upi", vpaName="Test", amount_paise=10000,
            merchantOrderId="ORDER-1", customerName="Test", customerEmail="test@example.com",
        )
        assert result["uroPayOrderId"] == "URO-123"


# ============================================================================
# VIEW TESTS (2 tests)
# ============================================================================

class TestPaymentAPIViews:
    """Tests for Payment API views."""

    def test_create_payment_authenticated(self, auth_client, order, mock_payment_provider):
        """Test creating payment as authenticated user."""
        with patch("payments.services.payment_service.PaymentProviderClient") as MockClient:
            MockClient.return_value = mock_payment_provider
            response = auth_client.post(
                reverse("payment-create"),
                {"order_id": order.id, "vpa": "test@upi", "vpaName": "Test", "customerName": "Test", "customerEmail": "test@example.com"},
                format="json",
            )
            assert response.status_code == status.HTTP_201_CREATED

    def test_confirm_payment_authenticated(self, auth_client, order, payment_with_uropay, mock_payment_provider):
        """Test confirming payment."""
        payment_with_uropay.order = order
        payment_with_uropay.save()
        with patch("payments.services.payment_service.PaymentProviderClient") as MockClient:
            MockClient.return_value = mock_payment_provider
            response = auth_client.post(
                reverse("payment-confirm"),
                {"order_id": order.id, "referenceNumber": "UTR123456"},
                format="json",
            )
            assert response.status_code == status.HTTP_200_OK
