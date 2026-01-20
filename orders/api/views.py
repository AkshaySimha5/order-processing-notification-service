from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from orders.services.order_creation import (
    OrderCreationService,
    OrderCreateRequest,
)
from orders.api.serializers import OrderCreateSerializer, OrderResponseSerializer, ProductListSerializer
from orders.models import Order, Product
from config.pagination import StandardResultsPagination


class CreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_request = serializer.to_dataclass(request.user.id)

        order = OrderCreationService.create_order(order_request)

        return Response(
            {
                "order_id": order.id,
                "total_amount": order.total_amount,
                "address": order.address,
            },
            status=status.HTTP_201_CREATED,
        )


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(Order, id=pk)

        if not request.user.is_superuser and order.user_id != request.user.id:
            raise PermissionDenied("You do not have permission to view this order.")

        serializer = OrderResponseSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ListOrdersAPIView(generics.ListAPIView):
    """
    List orders for the authenticated user with pagination.
    
    Query params:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 10, max: 100)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OrderResponseSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related("items")
        )


class ProductListAPIView(generics.ListAPIView):
    """
    List available products with pagination.
    Inventory information is excluded from the response.
    
    Query params:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 10, max: 100)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProductListSerializer
    pagination_class = StandardResultsPagination
    queryset = Product.objects.all()
