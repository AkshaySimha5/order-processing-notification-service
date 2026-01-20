"""
Tests for the notifications app - 20 tests.
Covers models, tasks, and adapters.
"""
import pytest
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError

from orders.models import Order, OrderItem
from notifications.models import Notification
from notifications.tasks import send_notification
from notifications.adapters.email import EmailAdapter
from notifications.adapters.sms import SmsAdapter


User = get_user_model()


# ============================================================================
# MODEL TESTS (7 tests)
# ============================================================================

class TestNotificationModel:
    """Tests for the Notification model."""

    def test_notification_creation(self, order):
        """Test creating a notification with defaults."""
        notification = Notification.objects.create(
            order=order, channel=Notification.Channel.EMAIL, payload={"event": "order.created"},
        )
        assert notification.pk is not None
        assert notification.status == Notification.Status.PENDING
        assert notification.attempts == 0

    def test_notification_channel_choices(self, order):
        """Test all notification channel choices."""
        for ch in [Notification.Channel.EMAIL, Notification.Channel.SMS, Notification.Channel.WEBHOOK]:
            notification = Notification.objects.create(order=order, channel=ch, payload={})
            assert notification.channel == ch
            notification.delete()

    def test_notification_status_choices(self, order):
        """Test all notification status choices."""
        for s in [Notification.Status.PENDING, Notification.Status.SENT, Notification.Status.FAILED]:
            notification = Notification.objects.create(order=order, channel=Notification.Channel.EMAIL, status=s, payload={})
            assert notification.status == s
            notification.delete()

    def test_notification_unique_constraint(self, order):
        """Test unique_key + channel constraint."""
        Notification.objects.create(order=order, unique_key="test:key", channel=Notification.Channel.EMAIL, payload={})
        with pytest.raises(IntegrityError):
            Notification.objects.create(order=order, unique_key="test:key", channel=Notification.Channel.EMAIL, payload={})

    def test_notification_same_key_different_channel(self, order):
        """Test same unique_key with different channels is allowed."""
        Notification.objects.create(order=order, unique_key="test:key", channel=Notification.Channel.EMAIL, payload={})
        notification = Notification.objects.create(order=order, unique_key="test:key", channel=Notification.Channel.SMS, payload={})
        assert notification.pk is not None

    def test_notification_null_unique_key_allowed(self, order):
        """Test null unique_key is allowed multiple times."""
        n1 = Notification.objects.create(order=order, unique_key=None, channel=Notification.Channel.EMAIL, payload={})
        n2 = Notification.objects.create(order=order, unique_key=None, channel=Notification.Channel.EMAIL, payload={})
        assert n1.pk != n2.pk

    def test_notification_sent_at(self, sent_notification):
        """Test sent_at field on sent notification."""
        assert sent_notification.sent_at is not None
        assert sent_notification.status == Notification.Status.SENT


# ============================================================================
# EMAIL ADAPTER TESTS (4 tests)
# ============================================================================

class TestEmailAdapter:
    """Tests for the EmailAdapter."""

    def test_send_order_created(self, order_with_items, mock_email_backend):
        """Test sending order.created email."""
        adapter = EmailAdapter()
        result = adapter.send(order=order_with_items, event="order.created", payload={})
        assert f"email:{order_with_items.pk}:order.created" == result
        assert len(mail.outbox) == 1
        assert "Order" in mail.outbox[0].subject

    def test_send_payment_confirmed(self, order_with_items, mock_email_backend):
        """Test sending payment.confirmed email."""
        result = EmailAdapter().send(order=order_with_items, event="payment.confirmed", payload={})
        assert "Payment" in mail.outbox[0].subject

    def test_send_no_recipient(self, order, mock_email_backend):
        """Test sending fails when user has no email."""
        order.user.email = ""
        order.user.save()
        with pytest.raises(RuntimeError) as exc_info:
            EmailAdapter().send(order=order, event="order.created", payload={})
        assert "No email recipient" in str(exc_info.value)

    def test_email_has_html_and_text(self, order_with_items, mock_email_backend):
        """Test email has both HTML and plain text versions."""
        EmailAdapter().send(order=order_with_items, event="order.created", payload={})
        email = mail.outbox[0]
        assert email.body and email.alternatives


# ============================================================================
# SMS ADAPTER TESTS (2 tests)
# ============================================================================

class TestSmsAdapter:
    """Tests for the SmsAdapter."""

    def test_sms_adapter_initialization(self):
        """Test SMS adapter initialization."""
        adapter = SmsAdapter()
        assert adapter.provider == ""

    def test_send_no_phone_number(self, order):
        """Test sending fails when user has no phone number."""
        order.user.phone_number = None
        order.user.save()
        with pytest.raises(RuntimeError) as exc_info:
            SmsAdapter().send(order=order, event="order.created", payload={})
        assert "No phone number" in str(exc_info.value)


# ============================================================================
# TASK TESTS (7 tests)
# ============================================================================

class TestSendNotificationTask:
    """Tests for the send_notification Celery task."""

    def test_send_notification_email_success(self, db, order_with_items, mock_email_backend):
        """Test successful email notification."""
        send_notification.apply(args=["test:key", order_with_items.pk, "order.created", ["EMAIL"]])
        notification = Notification.objects.filter(order=order_with_items, channel=Notification.Channel.EMAIL).first()
        assert notification is not None
        assert notification.status == Notification.Status.SENT

    def test_send_notification_order_not_found(self, db):
        """Test task handles non-existent order gracefully."""
        send_notification.apply(args=["test:key", 99999, "order.created", ["EMAIL"]])
        assert Notification.objects.count() == 0

    def test_send_notification_idempotency(self, db, order_with_items, mock_email_backend):
        """Test notification is idempotent (sent only once)."""
        unique_key = f"idempotent:test:{order_with_items.pk}"
        send_notification.apply(args=[unique_key, order_with_items.pk, "order.created", ["EMAIL"]])
        first_count = len(mail.outbox)
        send_notification.apply(args=[unique_key, order_with_items.pk, "order.created", ["EMAIL"]])
        assert len(mail.outbox) == first_count

    def test_send_notification_multiple_channels(self, db, user_with_sms, product, mock_email_backend):
        """Test sending to multiple channels."""
        order = Order.objects.create(user=user_with_sms, address="Test Address", status=Order.Status.PENDING)
        OrderItem.objects.create(order=order, product_id=product.id, product_name=product.name, price=product.price, quantity=1)
        send_notification.apply(args=["multi:channel", order.pk, "order.created", ["EMAIL", "SMS"]])
        assert Notification.objects.filter(order=order, channel=Notification.Channel.EMAIL).exists()
        assert Notification.objects.filter(order=order, channel=Notification.Channel.SMS).exists()

    def test_send_notification_unknown_channel_skipped(self, db, order_with_items, mock_email_backend):
        """Test unknown channel is skipped."""
        send_notification.apply(args=["unknown:channel", order_with_items.pk, "order.created", ["UNKNOWN"]])
        assert Notification.objects.filter(channel="UNKNOWN").count() == 0

    def test_send_notification_updates_attempts(self, db, order_with_items, mock_email_backend):
        """Test notification attempts are updated."""
        send_notification.apply(args=["attempts:test", order_with_items.pk, "order.created", ["EMAIL"]])
        notification = Notification.objects.filter(order=order_with_items).first()
        assert notification.attempts >= 1

    def test_send_notification_sets_sent_at(self, db, order_with_items, mock_email_backend):
        """Test sent_at is set on successful send."""
        send_notification.apply(args=["sent:at:test", order_with_items.pk, "order.created", ["EMAIL"]])
        notification = Notification.objects.filter(order=order_with_items).first()
        assert notification.sent_at is not None
