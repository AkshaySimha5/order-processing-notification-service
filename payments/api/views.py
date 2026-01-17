from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from payments.api.serializers import (
    PaymentGenerateSerializer,
    PaymentConfirmSerializer,
    PaymentResponseSerializer,
)
from payments.services.payment_service import PaymentService


class CreatePaymentAPIView(APIView):
    """Generate a UroPay order for an existing `Order` (two-step flow).

    Client posts order_id + payer details; we call UroPay `/order/generate`,
    persist the returned `uroPayOrderId`, `upiString`, and `qrCode` on Payment
    and return them to the client.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        payment = PaymentService.generate_payment(
            user_id=request.user.id,
            order_id=data["order_id"],
            vpa=data["vpa"],
            vpaName=data["vpaName"],
            customerName=data["customerName"],
            customerEmail=data["customerEmail"],
            transactionNote=data.get("transactionNote"),
        )

        out = PaymentResponseSerializer(payment).data
        return Response(out, status=status.HTTP_201_CREATED)


class ConfirmPaymentAPIView(APIView):
    """Confirm a payment by providing the UPI reference number obtained by the customer."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        payment = PaymentService.confirm_payment(
            user_id=request.user.id,
            order_id=data["order_id"],
            reference_number=data["referenceNumber"],
        )

        out = PaymentResponseSerializer(payment).data
        return Response(out, status=status.HTTP_200_OK)


class UroPayWebhookAPIView(APIView):
    """Endpoint for UroPay to post webhook events. Verifies signature and updates payment/order."""

    permission_classes = []

    def post(self, request):
        # Delegate to service which verifies signature and processes payload idempotently
        PaymentService.handle_webhook(request)
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
