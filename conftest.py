"""
Shared pytest fixtures for the Order Processing Notification System.
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from orders.models import Order, OrderItem, Product
from payments.models import Payment
from notifications.models import Notification


User = get_user_model()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def user_data():
    """Return default user data for creating test users."""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpass123",
    }


@pytest.fixture
def user(db, user_data):
    """Create and return a regular test user."""
    user = User.objects.create_user(
        username=user_data["username"],
        email=user_data["email"],
        password=user_data["password"],
        notify_email=True,
        notify_sms=False,
        phone_number="+1234567890",
    )
    return user


@pytest.fixture
def user_with_sms(db, user_data):
    """Create a user with SMS notifications enabled."""
    user = User.objects.create_user(
        username="smsuser",
        email="smsuser@example.com",
        password="testpass123",
        notify_email=True,
        notify_sms=True,
        phone_number="+1234567890",
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    admin = User.objects.create_user(
        username="adminuser",
        email="admin@example.com",
        password="adminpass123",
        is_staff=True,
        is_superuser=False,
    )
    return admin


@pytest.fixture
def superuser(db):
    """Create and return a superuser."""
    superuser = User.objects.create_superuser(
        username="superuser",
        email="super@example.com",
        password="superpass123",
    )
    return superuser


@pytest.fixture
def another_user(db):
    """Create and return another test user for permission tests."""
    user = User.objects.create_user(
        username="anotheruser",
        email="another@example.com",
        password="anotherpass123",
    )
    return user


# ============================================================================
# PRODUCT FIXTURES
# ============================================================================

@pytest.fixture
def product(db):
    """Create and return a test product."""
    return Product.objects.create(
        id=1,
        name="Test Product",
        price=Decimal("99.99"),
        inventory=100,
    )


@pytest.fixture
def product2(db):
    """Create and return a second test product."""
    return Product.objects.create(
        id=2,
        name="Another Product",
        price=Decimal("49.99"),
        inventory=50,
    )


@pytest.fixture
def product_low_inventory(db):
    """Create a product with low inventory."""
    return Product.objects.create(
        id=3,
        name="Low Stock Product",
        price=Decimal("29.99"),
        inventory=2,
    )


@pytest.fixture
def products(db, product, product2):
    """Return a list of all products."""
    return [product, product2]


# ============================================================================
# ORDER FIXTURES
# ============================================================================

@pytest.fixture
def order(db, user):
    """Create and return a test order."""
    return Order.objects.create(
        user=user,
        address="123 Test Street, Test City",
        status=Order.Status.PENDING,
        total_amount=Decimal("199.98"),
    )


@pytest.fixture
def order_with_items(db, user, product, product2):
    """Create an order with order items."""
    order = Order.objects.create(
        user=user,
        address="456 Test Ave, Test City",
        status=Order.Status.PENDING,
        total_amount=Decimal("0.00"),
    )
    OrderItem.objects.create(
        order=order,
        product_id=product.id,
        product_name=product.name,
        price=product.price,
        quantity=2,
    )
    OrderItem.objects.create(
        order=order,
        product_id=product2.id,
        product_name=product2.name,
        price=product2.price,
        quantity=1,
    )
    order.recalculate_total()
    return order


@pytest.fixture
def paid_order(db, user, product):
    """Create a paid order."""
    order = Order.objects.create(
        user=user,
        address="789 Paid Street, Test City",
        status=Order.Status.PAID,
        total_amount=Decimal("99.99"),
    )
    OrderItem.objects.create(
        order=order,
        product_id=product.id,
        product_name=product.name,
        price=product.price,
        quantity=1,
    )
    return order


@pytest.fixture
def order_another_user(db, another_user, product):
    """Create an order belonging to another user."""
    order = Order.objects.create(
        user=another_user,
        address="999 Other Street, Other City",
        status=Order.Status.PENDING,
        total_amount=Decimal("99.99"),
    )
    OrderItem.objects.create(
        order=order,
        product_id=product.id,
        product_name=product.name,
        price=product.price,
        quantity=1,
    )
    return order


# ============================================================================
# PAYMENT FIXTURES
# ============================================================================

@pytest.fixture
def payment(db, order):
    """Create a payment for an order."""
    return Payment.objects.create(
        order=order,
        amount=order.total_amount,
        status=Payment.Status.INITIATED,
    )


@pytest.fixture
def payment_with_uropay(db, order):
    """Create a payment with UroPay details."""
    return Payment.objects.create(
        order=order,
        amount=order.total_amount,
        status=Payment.Status.INITIATED,
        uro_pay_order_id="UROPAY-123456",
        upi_string="upi://pay?pa=test@upi&pn=Test&am=199.98",
        qr_code="base64encodedqrcode==",
    )


@pytest.fixture
def successful_payment(db, paid_order):
    """Create a successful payment."""
    return Payment.objects.create(
        order=paid_order,
        amount=paid_order.total_amount,
        status=Payment.Status.SUCCESS,
        provider_reference="REF-123456",
    )


# ============================================================================
# NOTIFICATION FIXTURES
# ============================================================================

@pytest.fixture
def notification(db, order):
    """Create a notification."""
    return Notification.objects.create(
        order=order,
        unique_key=f"order:{order.pk}:created:EMAIL",
        channel=Notification.Channel.EMAIL,
        status=Notification.Status.PENDING,
        payload={"event": "order.created", "order_id": order.pk},
    )


@pytest.fixture
def sent_notification(db, order):
    """Create a sent notification."""
    from django.utils import timezone
    return Notification.objects.create(
        order=order,
        unique_key=f"order:{order.pk}:created:EMAIL",
        channel=Notification.Channel.EMAIL,
        status=Notification.Status.SENT,
        payload={"event": "order.created", "order_id": order.pk},
        sent_at=timezone.now(),
    )


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def auth_client(api_client, user):
    """Return an authenticated API client for the test user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def admin_client(admin_user):
    """Return an authenticated API client for the admin user."""
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def superuser_client(superuser):
    """Return an authenticated API client for the superuser."""
    client = APIClient()
    refresh = RefreshToken.for_user(superuser)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def another_user_client(another_user):
    """Return an authenticated API client for another user."""
    client = APIClient()
    refresh = RefreshToken.for_user(another_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_send_notification(mocker):
    """Mock the send_notification Celery task."""
    return mocker.patch("notifications.tasks.send_notification.delay")


@pytest.fixture
def mock_payment_provider(mocker):
    """Mock the PaymentProviderClient."""
    mock_client = mocker.patch("payments.clients.provider.PaymentProviderClient")
    instance = mock_client.return_value
    instance.charge.return_value = (True, "REF-MOCK-123")
    instance.uropay_generate.return_value = {
        "uroPayOrderId": "UROPAY-MOCK-123",
        "upiString": "upi://pay?pa=mock@upi",
        "qrCode": "mockqrcode==",
    }
    instance.uropay_update.return_value = None
    return instance


@pytest.fixture
def mock_email_backend(settings):
    """Configure email backend for testing."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# ============================================================================
# HELPER FIXTURES
# ============================================================================

@pytest.fixture
def product_master_data():
    """Return sample product master data."""
    return {
        1: {"id": 1, "name": "Test Product", "price": Decimal("99.99")},
        2: {"id": 2, "name": "Another Product", "price": Decimal("49.99")},
    }
