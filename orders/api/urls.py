from django.urls import path
from .views import CreateOrderAPIView, OrderDetailAPIView

urlpatterns = [
    path("create/", CreateOrderAPIView.as_view(), name="create-order"),
    path("<int:pk>/", OrderDetailAPIView.as_view(), name="order-detail"),
]
