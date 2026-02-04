from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

class EmployeeBudget(models.Model):
    """
    One budget per employee.
    """
    employee = models.OneToOneField(
        "core.Employee",
        on_delete=models.CASCADE,
        related_name="budget"
    )
    balance = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.name} - {self.balance}"


class Expense(models.Model):
    employee = models.ForeignKey(
        "core.Employee",
        on_delete=models.CASCADE,
        related_name="expenses"
    )
    description = models.CharField(max_length=255)
    amount = models.IntegerField()
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name} - {self.amount} on {self.date}"


class BudgetAdjustment(models.Model):
    ADD = "ADD"
    REMOVE = "REMOVE"
    TYPE_CHOICES = [
        (ADD, "Shto"),
        (REMOVE, "Zbrit"),
    ]

    employee = models.ForeignKey(
        "core.Employee",
        on_delete=models.CASCADE,
        related_name="budget_adjustments"
    )
    adjustment_type = models.CharField(max_length=10, choices=TYPE_CHOICES ,default=ADD)
    amount = models.IntegerField()
    date = models.DateField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sign = "+" if self.adjustment_type == self.ADD else "-"
        return f"{self.employee.name} {sign}{self.amount} ({self.date})"
