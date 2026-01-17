from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import ValidationError, PermissionDenied

from payments.models import Payment
from orders.models import Order, Product, OrderItem
from payments.clients.provider import PaymentProviderClient, PaymentProviderError
import json
import hashlib
import hmac
from django.utils import timezone
from payments.models import Payment
from django.conf import settings


class PaymentNotFound(Exception):
    pass


@dataclass(frozen=True)
class PaymentRequest:
    order_id: int
    user_id: int
    provider_token: str
    method: str = "card"
    currency: str = "USD"


class PaymentService:
    @staticmethod
    @transaction.atomic
    def create_payment(request: PaymentRequest) -> Payment:
        # Lock the order row so status transitions are safe
        try:
            order = (
                Order.objects.select_for_update()
                .prefetch_related("items")
                .get(id=request.order_id)
            )
        except ObjectDoesNotExist:
            raise ValidationError("Order does not exist")

        if order.user_id != request.user_id:
            raise PermissionDenied("You do not have permission to pay for this order.")

        if order.status != Order.Status.PENDING:
            raise ValidationError("Order cannot be paid in its current status.")

        amount = order.total_amount

        # create a payment record marked INITIATED; will be rolled back on failure
        payment = Payment.objects.create(order=order, amount=amount, status=Payment.Status.INITIATED)

        client = PaymentProviderClient()

        try:
            success, reference = client.charge(amount=amount, currency=request.currency, provider_token=request.provider_token)
        except PaymentProviderError as exc:
            # Any provider exception should rollback the transaction
            raise ValidationError("Payment processing failed") from exc

        if not success:
            # Treat as failure -> rollback
            raise ValidationError("Payment declined by provider")

        # Success: update payment and order status
        payment.status = Payment.Status.SUCCESS
        payment.provider_reference = reference or ""
        payment.save(update_fields=["status", "provider_reference", "updated_at"])

        order.status = Order.Status.PAID
        order.save(update_fields=["status", "updated_at"])

        return payment

    @staticmethod
    @transaction.atomic
    def generate_payment(*, user_id: int, order_id: int, vpa: str, vpaName: str, customerName: str, customerEmail: str, transactionNote: str | None = None) -> Payment:
        try:
            order = (
                Order.objects.select_for_update()
                .prefetch_related("items")
                .get(id=order_id)
            )
        except ObjectDoesNotExist:
            raise ValidationError("Order does not exist")

        if order.user_id != user_id:
            raise PermissionDenied("You do not have permission to pay for this order.")

        if order.status != Order.Status.PENDING:
            raise ValidationError("Order cannot be paid in its current status.")

        # Ensure a Payment record exists (or create)
        payment, _ = Payment.objects.get_or_create(order=order, defaults={"amount": order.total_amount, "status": Payment.Status.INITIATED})

        # Call UroPay generate
        client = PaymentProviderClient()
        amount_paise = int(order.total_amount * 100)
        merchant_order_id = f"ORDER-{order.id}"

        try:
            data = client.uropay_generate(
                vpa=vpa,
                vpaName=vpaName,
                amount_paise=amount_paise,
                merchantOrderId=merchant_order_id,
                customerName=customerName,
                customerEmail=customerEmail,
                transactionNote=transactionNote,
            )
        except PaymentProviderError as exc:
            raise ValidationError("UroPay generate failed") from exc

        # Persist returned provider data onto payment
        payment.uro_pay_order_id = data.get("uroPayOrderId")
        payment.upi_string = data.get("upiString")
        payment.qr_code = data.get("qrCode")
        payment.save(update_fields=["uro_pay_order_id", "upi_string", "qr_code", "updated_at"])

        return payment

    @staticmethod
    @transaction.atomic
    def confirm_payment(*, user_id: int, order_id: int, reference_number: str) -> Payment:
        try:
            order = (
                Order.objects.select_for_update()
                #.select_related("payment")
                .get(id=order_id)
            )
        except ObjectDoesNotExist:
            raise ValidationError("Order does not exist")

        if order.user_id != user_id:
            raise PermissionDenied("You do not have permission to pay for this order.")

        payment = getattr(order, "payment", None)
        if not payment or not payment.uro_pay_order_id:
            raise ValidationError("Payment has not been initiated for this order.")

        client = PaymentProviderClient()
        try:
            client.uropay_update(uroPayOrderId=payment.uro_pay_order_id, referenceNumber=reference_number)
        except PaymentProviderError as exc:
            raise ValidationError("UroPay update failed") from exc

        # Mark payment and order success
        payment.reference_number = reference_number
        payment.status = Payment.Status.SUCCESS
        payment.provider_reference = reference_number
        payment.save(update_fields=["reference_number", "status", "provider_reference", "updated_at"])

        order.status = Order.Status.PAID
        order.save(update_fields=["status", "updated_at"])

        return payment

    @staticmethod
    def handle_webhook(request):
        # Verify signature
        signature = request.headers.get("X-Uropay-Signature")
        webhook_id = request.headers.get("X-Uropay-Webhook-Id")
        environment = request.headers.get("X-Uropay-Environment")

        raw = request.body
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            raise ValidationError("Invalid webhook payload")

        # compute expected signature
        secret = getattr(settings, "UROPAY_SECRET", None)
        if not secret:
            raise ValidationError("Webhook secret not configured")

        # secret must be sha512-hashed before use
        hashed_secret = hashlib.sha512(secret.encode("utf-8")).hexdigest()

        # sorted transaction data
        sorted_items = dict(sorted(data.items(), key=lambda kv: kv[0]))
        payload_for_sig = {**sorted_items, "environment": environment}
        payload_str = json.dumps(payload_for_sig, separators=(",", ":"), ensure_ascii=False)

        expected = hmac.new(hashed_secret.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(expected, signature):
            raise PermissionDenied("Invalid webhook signature")

        # Idempotency: do not process duplicate webhook ids
        from payments.models import WebhookEvent

        if WebhookEvent.objects.filter(webhook_id=webhook_id).exists():
            return

        # Process basic payload keys
        ref = data.get("referenceNumber")
        amount = data.get("amount")

        # Try to find matching payment by reference_number or uro_pay_order_id
        payment = None
        if ref:
            payment = Payment.objects.filter(reference_number=ref).first()

        if not payment and data.get("uroPayOrderId"):
            payment = Payment.objects.filter(uro_pay_order_id=data.get("uroPayOrderId")).first()

        if payment:
            payment.reference_number = ref or payment.reference_number
            payment.status = Payment.Status.SUCCESS
            payment.provider_reference = ref or payment.provider_reference
            payment.save(update_fields=["reference_number", "status", "provider_reference", "updated_at"])
            order = payment.order
            order.status = Order.Status.PAID
            order.save(update_fields=["status", "updated_at"])

        # Record webhook event
        WebhookEvent.objects.create(webhook_id=webhook_id, payload=data, received_at=timezone.now())

