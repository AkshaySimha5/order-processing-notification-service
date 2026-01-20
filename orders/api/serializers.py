from decimal import Decimal
from rest_framework import serializers

from orders.models import Order, OrderItem, Product
from orders.services.order_creation import (
    OrderCreateRequest,
    OrderItemRequest,
    load_product_master,
)


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        product_master = load_product_master()
        product = product_master.get(attrs["product_id"])
        if not product:
            raise serializers.ValidationError({"product_id": "Invalid product_id."})
        attrs["product_name"] = product["name"]
        attrs["price"] = product["price"]
        return attrs


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True)
    address = serializers.CharField(required=True, allow_blank=False)
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must contain at least one item.")
        return value

    def to_dataclass(self, user_id: int) -> OrderCreateRequest:
        return OrderCreateRequest( # DTO conversion
            user_id=user_id,
            items=[
                OrderItemRequest(
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    product_name=item["product_name"],
                    price=item["price"],
                )
                for item in self.validated_data["items"]
            ],
            address=self.validated_data["address"],
        )


class OrderItemResponseSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField()
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2)


class OrderResponseSerializer(serializers.ModelSerializer):
    items = OrderItemResponseSerializer(many=True)

    class Meta:
        model = Order
        fields = ["id", "total_amount", "created_at", "items", "address"]


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing products.
    Excludes inventory information for security/business reasons.
    """

    class Meta:
        model = Product
        fields = ["id", "name", "price"]
