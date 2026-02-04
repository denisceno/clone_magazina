from django.db import models
from django.utils import timezone
from django.db.models import Sum
from django.core.validators import MinValueValidator
from decimal import Decimal

# Create your models here.


class Depot(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    depot = models.ForeignKey(
        Depot,
        on_delete=models.CASCADE,
        related_name="products"
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField(default=0)
    date = models.DateField(
        default=timezone.now,

    )

    RETURNABLE = "returnable"
    CONSUMABLE = "consumable"

    ITEM_TYPE_CHOICES = [
        (RETURNABLE, "Rikthyeshëm"),
        (CONSUMABLE, "Konsumueshëm"),
    ]

    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES
    )

    quantity = models.PositiveIntegerField()

    UNIT_CHOICES = [
        ("pcs", "Copë"),
        ("m", "m"),
        ("kg", "kg"),
        ("L", "L"),
        ("other", "Tjetër"),
    ]

    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["depot", "name"], name="unique_product_name_per_depot")
        ]
        
    def __str__(self):
        unit_display = "" if self.unit == "pcs" else f" {self.unit}"
        return f"{self.name} ({self.quantity}{unit_display})"


class WithdrawalHeader(models.Model):
    employee = models.ForeignKey('core.Employee', on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employee.name} - {self.date}"

class WithdrawalItem(models.Model):
    header = models.ForeignKey(
        WithdrawalHeader,
        related_name="items",
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    @property
    def returned_qty(self):
        total = ReturnItem.objects.filter(withdrawal_item=self).aggregate(
            total=Sum("quantity")
        )["total"]
        return total or 0

    @property
    def outstanding_qty(self):
        return self.quantity - self.returned_qty

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


class ReturnHeader(models.Model):
    employee = models.ForeignKey('core.Employee', on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Return by {self.employee.name} on {self.date}"


class ReturnItem(models.Model):
    header = models.ForeignKey(ReturnHeader, on_delete=models.CASCADE, related_name="items")
    withdrawal_item = models.ForeignKey(WithdrawalItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"Return {self.quantity} of {self.withdrawal_item.product.name}"
