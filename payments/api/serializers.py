from rest_framework import serializers
from decimal import Decimal


class PaymentGenerateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(min_value=1)
    vpa = serializers.CharField(required=True)
    vpaName = serializers.CharField(required=True)
    customerName = serializers.CharField(required=True)
    customerEmail = serializers.EmailField(required=True)
    transactionNote = serializers.CharField(required=False, allow_blank=True)


class PaymentConfirmSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(min_value=1)
    referenceNumber = serializers.CharField(required=True)


class PaymentResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    provider_reference = serializers.CharField(allow_null=True, allow_blank=True)
    uro_pay_order_id = serializers.CharField(allow_null=True, allow_blank=True)
    upi_string = serializers.CharField(allow_null=True, allow_blank=True)
    qr_code = serializers.CharField(allow_null=True, allow_blank=True)
    reference_number = serializers.CharField(allow_null=True, allow_blank=True)
    created_at = serializers.DateTimeField()
