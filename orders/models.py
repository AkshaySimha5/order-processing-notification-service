from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class Order(models.Model):
    """
    Represents a customer order.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        default=Decimal("0.00"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Order #{self.id} - User: {self.user.username}"

    def recalculate_total(self) -> None:
        """
        Recalculate and persist the total order amount.
        """
        total = sum(
            (item.price * item.quantity) for item in self.items.all()
        )
        self.total_amount = total
        self.save(update_fields=["total_amount"])


class OrderItem(models.Model):
    """
    Represents a product inside an order.
    Product data is denormalized from master JSON data.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product_id = models.PositiveIntegerField()
    product_name = models.CharField(max_length=255)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    class Meta:
        unique_together = ("order", "product_id")
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["product_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.product_name} x {self.quantity}"

    @property
    def line_total(self) -> Decimal:
        return self.price * self.quantity


class Product(models.Model):
    """
    Master product stored in the DB so inventory can be managed atomically.
    The `id` corresponds to the product id from product_master.json.
    """

    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    inventory = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"
