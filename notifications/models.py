from django.db import models
from orders.models import Order


class Notification(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        SMS = "SMS", "SMS"
        WEBHOOK = "WEBHOOK", "Webhook"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    # Optional unique key used to ensure idempotency for a given channel
    unique_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payload = models.JSONField()
    error_message = models.TextField(blank=True, null=True)
    attempts = models.IntegerField(default=0)
    task_id = models.CharField(max_length=200, blank=True, null=True)
    external_id = models.CharField(max_length=200, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.channel} | {self.order.order_number}"

    class Meta:
        # combination of unique_key + channel enforces idempotency per-channel
        constraints = [
            models.UniqueConstraint(fields=["unique_key", "channel"], name="unique_notification_per_channel", condition=models.Q(unique_key__isnull=False)),
        ]
