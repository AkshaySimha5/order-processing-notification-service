"""
Tests for the orders app - 20 tests.
Covers models, serializers, views, and services.
"""
import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import ValidationError

from orders.models import Order, OrderItem, Product
from orders.api.serializers import (
    OrderItemInputSerializer,
    OrderCreateSerializer,
    OrderResponseSerializer,
    ProductListSerializer,
)
from orders.services.order_creation import (
    OrderCreationService,
    OrderCreateRequest,
    OrderItemRequest,
    load_product_master,
)


User = get_user_model()


# ============================================================================
# MODEL TESTS (6 tests)
# ============================================================================

class TestOrderModel:
    """Tests for the Order model."""

    def test_order_creation_and_defaults(self, db, user):
        """Test creating an order with defaults."""
        order = Order.objects.create(user=user, address="123 Test St")
        assert order.pk is not None
        assert order.status == Order.Status.PENDING
        assert order.total_amount == Decimal("0.00")
        assert order.created_at is not None
        assert str(order) == f"Order #{order.id} - User: {user.username}"

    def test_order_status_choices(self, db, user):
        """Test all order status choices."""
        for s in [Order.Status.PENDING, Order.Status.PAID, Order.Status.PROCESSING, 
                  Order.Status.SHIPPED, Order.Status.DELIVERED, Order.Status.CANCELLED]:
            order = Order.objects.create(user=user, address="Test", status=s)
            assert order.status == s

    def test_order_recalculate_total(self, order_with_items):
        """Test recalculate_total method."""
        order_with_items.recalculate_total()
        assert order_with_items.total_amount == Decimal("249.97")


class TestOrderItemModel:
    """Tests for the OrderItem model."""

    def test_order_item_creation(self, order, product):
        """Test creating an order item."""
        item = OrderItem.objects.create(
            order=order, product_id=product.id, product_name=product.name,
            price=product.price, quantity=2,
        )
        assert item.pk is not None
        assert str(item) == f"{product.name} x 2"
        assert item.line_total == product.price * 2


class TestProductModel:
    """Tests for the Product model."""

    def test_product_creation(self, db):
        """Test creating a product."""
        product = Product.objects.create(id=10, name="Test Product", price=Decimal("25.00"), inventory=50)
        assert product.pk == 10
        assert str(product) == "Test Product (10)"
        assert product.inventory == 50

    def test_product_default_inventory(self, db):
        """Test default inventory is 0."""
        product = Product.objects.create(id=11, name="Zero Inventory", price=Decimal("10.00"))
        assert product.inventory == 0


# ============================================================================
# SERIALIZER TESTS (4 tests)
# ============================================================================

class TestOrderSerializers:
    """Tests for order serializers."""

    def test_order_item_input_valid(self, product):
        """Test OrderItemInputSerializer with valid data."""
        serializer = OrderItemInputSerializer(data={"product_id": product.id, "quantity": 2})
        assert serializer.is_valid()
        assert serializer.validated_data["product_name"] == product.name

    def test_order_item_input_invalid(self, db):
        """Test OrderItemInputSerializer with invalid product."""
        serializer = OrderItemInputSerializer(data={"product_id": 9999, "quantity": 1})
        assert not serializer.is_valid()

    def test_order_create_serializer(self, product, user):
        """Test OrderCreateSerializer validation and dataclass conversion."""
        data = {"items": [{"product_id": product.id, "quantity": 2}], "address": "456 Test Ave"}
        serializer = OrderCreateSerializer(data=data)
        assert serializer.is_valid()
        request = serializer.to_dataclass(user.id)
        assert isinstance(request, OrderCreateRequest)
        assert request.user_id == user.id

    def test_order_create_empty_items(self, db):
        """Test serializer rejects empty items."""
        serializer = OrderCreateSerializer(data={"items": [], "address": "123 Test Street"})
        assert not serializer.is_valid()


# ============================================================================
# SERVICE TESTS (5 tests)
# ============================================================================

class TestOrderCreationService:
    """Tests for OrderCreationService."""

    def test_create_order_success(self, db, user, product, mock_send_notification):
        """Test successful order creation."""
        request = OrderCreateRequest(
            user_id=user.id,
            items=[OrderItemRequest(product_id=product.id, quantity=2, product_name=product.name, price=product.price)],
            address="123 Test St",
        )
        order = OrderCreationService.create_order(request)
        assert order.pk is not None
        product.refresh_from_db()
        assert product.inventory == 98

    def test_create_order_empty_items(self, db, user):
        """Test order creation fails with empty items."""
        request = OrderCreateRequest(user_id=user.id, items=[], address="123 Test St")
        with pytest.raises(ValidationError):
            OrderCreationService.create_order(request)

    def test_create_order_invalid_user(self, db, product):
        """Test order creation fails with invalid user."""
        request = OrderCreateRequest(
            user_id=99999,
            items=[OrderItemRequest(product_id=product.id, quantity=1, product_name=product.name, price=product.price)],
            address="123 Test St",
        )
        with pytest.raises(ValidationError):
            OrderCreationService.create_order(request)

    def test_create_order_insufficient_inventory(self, db, user, product_low_inventory, mock_send_notification):
        """Test order creation fails with insufficient inventory."""
        request = OrderCreateRequest(
            user_id=user.id,
            items=[OrderItemRequest(product_id=product_low_inventory.id, quantity=100, 
                   product_name=product_low_inventory.name, price=product_low_inventory.price)],
            address="123 Test St",
        )
        with pytest.raises(ValidationError) as exc_info:
            OrderCreationService.create_order(request)
        assert "insufficient_inventory" in str(exc_info.value.detail)

    def test_load_product_master(self, products):
        """Test loading products from database."""
        cache.clear()
        result = load_product_master()
        assert 1 in result and 2 in result


# ============================================================================
# VIEW TESTS (5 tests)
# ============================================================================

class TestOrderAPIViews:
    """Tests for Order API views."""

    def test_create_order_authenticated(self, auth_client, product, mock_send_notification):
        """Test creating order as authenticated user."""
        url = reverse("create-order")
        data = {"items": [{"product_id": product.id, "quantity": 1}], "address": "123 Test Street"}
        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "order_id" in response.data

    def test_create_order_unauthenticated(self, api_client, product):
        """Test creating order without authentication fails."""
        url = reverse("create-order")
        response = api_client.post(url, {"items": [{"product_id": product.id, "quantity": 1}], "address": "Test"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_order_detail_permissions(self, auth_client, order, another_user_client):
        """Test getting own and other user's order."""
        # Own order - should succeed
        response = auth_client.get(reverse("order-detail", kwargs={"pk": order.pk}))
        assert response.status_code == status.HTTP_200_OK
        # Other user's order - should be forbidden
        response = another_user_client.get(reverse("order-detail", kwargs={"pk": order.pk}))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_orders(self, auth_client, order, order_another_user):
        """Test listing own orders only."""
        response = auth_client.get(reverse("order-list"))
        assert response.status_code == status.HTTP_200_OK
        order_ids = [o["id"] for o in response.data["results"]]
        assert order.pk in order_ids
        assert order_another_user.pk not in order_ids

    def test_list_products(self, auth_client, products):
        """Test listing products."""
        response = auth_client.get(reverse("product-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        for p in response.data["results"]:
            assert "inventory" not in p
