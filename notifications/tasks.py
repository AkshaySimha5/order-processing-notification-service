import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction, IntegrityError

from notifications.models import Notification
from orders.models import Order
from notifications.adapters.email import EmailAdapter
from notifications.adapters.sms import SmsAdapter

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def send_notification(self, unique_key: str, order_id: int, event: str, channels: list):
    """Send notification for an order for the given channels.

    - `unique_key` should be provided to make the operation idempotent per-channel.
    - `channels` is a list like ['EMAIL', 'SMS']
    """
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        logger.error('Order %s does not exist', order_id)
        return

    adapters = {
        'EMAIL': EmailAdapter(),
        'SMS': SmsAdapter(),
    }

    for channel in channels:
        adapter = adapters.get(channel)
        if not adapter:
            logger.warning('No adapter for channel %s', channel)
            continue

        # Build a per-channel unique key so uniqueness constraint is effective
        per_channel_key = f"{unique_key}:{channel}" if unique_key else None

        # Idempotent creation: if row exists and is SENT, skip
        try:
            with transaction.atomic():
                notification, created = Notification.objects.get_or_create(
                    unique_key=per_channel_key,
                    channel=channel,
                    defaults={
                        'order': order,
                        'payload': {'event': event, 'order_id': order_id},
                        'status': Notification.Status.PENDING,
                    },
                )
        except IntegrityError:
            # race condition on unique constraint — try to fetch
            notification = Notification.objects.filter(unique_key=per_channel_key, channel=channel).first()
            created = False

        if not created and notification.status == Notification.Status.SENT:
            logger.info('Notification already sent (id=%s)', notification.pk)
            continue

        # Attempt send
        try:
            notification.attempts = (notification.attempts or 0) + 1
            notification.task_id = self.request.id
            notification.save(update_fields=['attempts', 'task_id'])

            # render message; adapters implement send(order, event, payload)
            external_id = adapter.send(order=order, event=event, payload=notification.payload)

            notification.status = Notification.Status.SENT
            notification.sent_at = timezone.now()
            notification.external_id = external_id
            notification.error_message = ''
            notification.save()
        except Exception as exc:
            logger.exception('Failed to send notification for order=%s channel=%s', order_id, channel)
            notification.attempts = (notification.attempts or 0) + 0
            notification.error_message = str(exc)
            notification.save(update_fields=['attempts', 'error_message'])
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                notification.status = Notification.Status.FAILED
                notification.save(update_fields=['status'])
