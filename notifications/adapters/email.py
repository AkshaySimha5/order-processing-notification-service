from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailAdapter:
    def send(self, order, event, payload) -> str:
        recipient = getattr(order.user, 'email', None)
        if not recipient:
            logger.warning('No email recipient for order %s', order.pk)
            raise RuntimeError('No email recipient')

        # 1. Map events to specific templates
        template_map = {
            'order.created': 'notifications/order_created.html',
            'payment.confirmed': 'notifications/payment_confirmed.html',
        }
        template_name = template_map.get(event, 'notifications/default.html')

        # 2. Define subjects based on event
        subject_map = {
            'order.created': f"Confirming your Order #{order.id}",
            'payment.confirmed': f"Payment Received for Order #{order.id}",
        }
        subject = subject_map.get(event, f"Update on Order #{order.id}")

        # 3. Render HTML and create a plain-text fallback
        context = {'order': order, 'payload': payload}
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content) # Fallback for old email clients

        # 4. Use EmailMultiAlternatives for better delivery
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [recipient]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return f"email:{order.pk}:{event}"