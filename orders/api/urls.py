from django.urls import path
from .views import CreateOrderAPIView, OrderDetailAPIView, ListOrdersAPIView, ProductListAPIView

urlpatterns = [
    path("create/", CreateOrderAPIView.as_view(), name="create-order"),
    path("", ListOrdersAPIView.as_view(), name="order-list"),
    path("<int:pk>/", OrderDetailAPIView.as_view(), name="order-detail"),
    path("products/", ProductListAPIView.as_view(), name="product-list"),
]
