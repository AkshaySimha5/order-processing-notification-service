from dataclasses import dataclass
from typing import List
import json
from decimal import Decimal
from pathlib import Path
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.cache import cache

from orders.models import Order, OrderItem, Product
from notifications.tasks import send_notification


User = get_user_model()


@dataclass(frozen=True)
class OrderItemRequest:
    product_id: int
    quantity: int
    product_name: str
    price: Decimal


@dataclass(frozen=True)
class OrderCreateRequest:
    user_id: int
    items: List[OrderItemRequest]
    address: str


class OrderCreationService:
    @staticmethod
    @transaction.atomic
    def create_order(request: OrderCreateRequest) -> Order:
        if not request.items:
            raise ValidationError("Order must contain at least one item.")

        # Address is required for order creation (serializer enforces this, defensive check here)
        if not request.address or not request.address.strip():
            raise ValidationError("Address is required for order creation.")

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            raise ValidationError("Invalid user_id")

        # Lock product rows to avoid race conditions when checking/decrementing inventory
        product_ids = [item.product_id for item in request.items]
        products_qs = Product.objects.select_for_update().filter(id__in=product_ids)
        products_map = {p.id: p for p in products_qs}

        missing = [pid for pid in product_ids if pid not in products_map]
        if missing:
            raise ValidationError({"invalid_product_ids": missing})

        insufficient = []
        for item in request.items:
            p = products_map[item.product_id]
            if p.inventory < item.quantity:
                insufficient.append({
                    "product_id": p.id,
                    "product_name": p.name,
                    "requested": item.quantity,
                    "available": p.inventory,
                })

        if insufficient:
            raise ValidationError({"insufficient_inventory": insufficient})

        # Decrement inventory
        for item in request.items:
            p = products_map[item.product_id]
            p.inventory -= item.quantity
            p.save(update_fields=["inventory"]) # update only inventory column

        order = Order.objects.create(user=user, address=request.address)

        for item in request.items:
            OrderItem.objects.create(
                order=order,
                product_id=item.product_id,
                product_name=item.product_name,
                price=item.price,
                quantity=item.quantity,
            )

        order.recalculate_total()

        # Enqueue notification for order created
        # try catch used to ensure order creation is not blocked by notification failures
        try:
            channels = []
            if getattr(user, 'notify_email', True) and getattr(user, 'email', None):
                channels.append('EMAIL')
            if getattr(user, 'notify_sms', False) and getattr(user, 'phone_number', None):
                channels.append('SMS')

            if channels:
                unique_key = f"order:{order.pk}:created"
                send_notification.delay(unique_key, order.id, 'order.created', channels)
        except Exception:
            # Notification failure should not block order creation
            pass

        return order


PRODUCT_MASTER_PATH = Path(__file__).resolve().parent.parent / "product_master.json"


def load_product_master() -> dict:
    cache_key = "product_master"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Prefer DB-backed product data (authoritative for name/price); fall back to JSON
    result = {}
    products = Product.objects.all()
    if products.exists():
        for p in products:
            result[p.id] = {"name": p.name, "price": p.price}
    else:
        with open(PRODUCT_MASTER_PATH) as f:
            data = json.load(f)
        for product in data["products"]:
            result[product["id"]] = {
                "name": product["name"],
                "price": Decimal(product["price"]),
            }

    cache.set(cache_key, result, 86400)  # Cache for 24 hours
    return result