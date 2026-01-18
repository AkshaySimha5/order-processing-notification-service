import os
import logging

logger = logging.getLogger(__name__)


class SmsAdapter:
    def __init__(self):
        # Placeholder for provider setup (e.g., Twilio)
        self.provider = os.getenv('SMS_PROVIDER', '')

    def send(self, order, event, payload) -> str:
        """Send an SMS. This is a minimal provider-agnostic stub.

        If `SMS_PROVIDER` and credentials are configured, integrate a real client.
        """
        phone = getattr(order.user, 'phone_number', None)
        if not phone:
            logger.warning('No phone number for order %s', order.pk)
            raise RuntimeError('No phone number')

        message = f"[{event}] Order {order.order_number}"

        # If no provider configured, just log (useful in development)
        if not self.provider:
            logger.info('SMS stub send to %s: %s', phone, message)
            return f"sms:stub:{order.pk}:{event}"

        # Example: integrate Twilio here using env vars if provider == 'twilio'
        if self.provider == 'twilio':
            try:
                from twilio.rest import Client

                account_sid = os.getenv('TWILIO_ACCOUNT_SID')
                auth_token = os.getenv('TWILIO_AUTH_TOKEN')
                from_number = os.getenv('TWILIO_FROM')
                client = Client(account_sid, auth_token)
                resp = client.messages.create(body=message, from_=from_number, to=phone)
                return str(resp.sid)
            except Exception as exc:
                logger.exception('Twilio send failed')
                raise

        # Unknown provider configured
        logger.error('Unknown SMS_PROVIDER configured: %s', self.provider)
        raise RuntimeError('Unknown SMS provider')
