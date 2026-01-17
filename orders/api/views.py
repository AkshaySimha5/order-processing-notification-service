from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from orders.services.order_creation import (
    OrderCreationService,
    OrderCreateRequest,
)
from orders.api.serializers import OrderCreateSerializer, OrderResponseSerializer
from orders.models import Order


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


class ListOrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders_qs = (
            Order.objects.filter(user=request.user)
            .prefetch_related("items")
        )
        serializer = OrderResponseSerializer(orders_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
