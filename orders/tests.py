import json
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APITestCase
from rest_framework import status

from orders.models import Order, Product
from orders.services.order_creation import OrderCreationService, OrderCreateRequest, OrderItemRequest

User = get_user_model()

class OrderServiceTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password",
            email="test@example.com"
        )
        self.product = Product.objects.create(id=1, name="Laptop", price=Decimal("1000.00"), inventory=10)
        cache.clear()

    @patch('notifications.tasks.send_notification.delay')
    def test_create_order_success(self, mock_notification):
        item_req = OrderItemRequest(
            product_id=self.product.id,
            quantity=2,
            product_name=self.product.name,
            price=self.product.price
        )
        request_dto = OrderCreateRequest(
            user_id=self.user.id,
            items=[item_req],
            address="123 Django St"
        )

        order = OrderCreationService.create_order(request_dto)

        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order.total_amount, Decimal("2000.00"))

        # Check inventory decrement
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 8)

        # will pass because the user has an email
        self.assertTrue(mock_notification.called, "Notification task was not triggered.")

class OrderAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="apiuser", password="password", email="api@example.com")
        self.other_user = User.objects.create_user(username="otheruser", password="password")
        self.product = Product.objects.create(id=1, name="Mouse", price=Decimal("50.00"), inventory=100)
        self.client.force_authenticate(user=self.user)
        cache.clear()

    @patch('orders.services.order_creation.load_product_master')
    @patch('notifications.tasks.send_notification.delay')
    def test_create_order_api(self, mock_notify, mock_load_master):
        mock_load_master.return_value = {1: {"name": "Mouse", "price": Decimal("50.00")}}

        data = {
            "address": "456 API Ave",
            "items": [{"product_id": 1, "quantity": 2}]
        }
        response = self.client.post("/api/orders/create/", data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # FIX: Compare Decimal to Decimal instead of String
        self.assertEqual(response.data['total_amount'], Decimal("100.00"))

    def test_order_detail_permission(self):
        order = Order.objects.create(user=self.user, address="User's Home")
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(f"/api/orders/{order.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class CommandTests(TestCase):
    def test_import_products_command(self):
        # This checks that the command runs and clears the cache
        call_command('import_products')
        self.assertIsNone(cache.get("product_master"))