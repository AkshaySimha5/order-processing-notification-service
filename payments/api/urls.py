from django.urls import path
from payments.api.views import CreatePaymentAPIView, ConfirmPaymentAPIView, UroPayWebhookAPIView

urlpatterns = [
    path("create/", CreatePaymentAPIView.as_view(), name="payment-create"),
    path("confirm/", ConfirmPaymentAPIView.as_view(), name="payment-confirm"),
    path("webhook/", UroPayWebhookAPIView.as_view(), name="payment-webhook"),
]
