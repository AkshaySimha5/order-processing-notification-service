from django.db import models
from orders.models import Order


class Payment(models.Model):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INITIATED,
    )
    provider_reference = models.CharField(max_length=255, blank=True, null=True)
    # UroPay fields
    uro_pay_order_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    upi_string = models.TextField(blank=True, null=True)
    qr_code = models.TextField(blank=True, null=True)
    reference_number = models.CharField(max_length=64, blank=True, null=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Order #{self.order.id}"


class WebhookEvent(models.Model):
    webhook_id = models.CharField(max_length=255, unique=True)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - tiny helper
        return f"WebhookEvent {self.webhook_id}"
