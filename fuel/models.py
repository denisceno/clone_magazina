
from django.db import models
from django.utils.timezone import now


class FuelTank(models.Model):
    name = models.CharField(max_length=50, default='Tank 1')
    capacity = models.PositiveIntegerField()

    def __str__(self):
        return self.name

    @property
    def current_level(self):
        entries_total = self.entries.aggregate(total=models.Sum('amount'))['total'] or 0
        usage_total = self.fuelusage_set.aggregate(total=models.Sum('amount'))['total'] or 0
        return entries_total - usage_total

    

class FuelEntry(models.Model):
    tank = models.ForeignKey(
        "fuel.FuelTank",
        on_delete=models.CASCADE,
        related_name="entries",
    )

    date = models.DateField(default=now)

    # Sa litra u futën në refill
    amount = models.PositiveIntegerField()

    supplier = models.CharField(max_length=100)

    # Status i refill-it
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            # ✅ Lejo vetëm 1 refill OPEN për çdo tank
            models.UniqueConstraint(
                fields=["tank"],
                condition=models.Q(is_closed=False),
                name="unique_open_refill_per_tank",
            )
        ]

    def __str__(self):
        status = "CLOSED" if self.is_closed else "OPEN"
        return f"Refill {self.amount}L — {self.tank} — {self.date} ({status})"

    @property
    def used_amount(self) -> int:
        # ✅ total liters used that are linked to THIS refill
        # relies on FuelUsage.refill ForeignKey with related_name="usages" (recommended)
        if hasattr(self, "usages"):
            total = self.usages.aggregate(total=models.Sum("amount"))["total"] or 0
            return int(total)

        # fallback if you didn't add related_name on FuelUsage.refill
        total = self.fuelusage_set.aggregate(total=models.Sum("amount"))["total"] or 0
        return int(total)

    @property
    def remaining_amount(self) -> int:
        # remaining for this refill (never below 0)
        return max(int(self.amount) - int(self.used_amount), 0)


class FuelUsage(models.Model):
    tank = models.ForeignKey(FuelTank, on_delete=models.CASCADE)
    date = models.DateField(default=now)
    amount = models.IntegerField()
    vehicle = models.ForeignKey('core.Vehicle', on_delete=models.PROTECT)

    refill = models.ForeignKey(FuelEntry, on_delete=models.SET_NULL, null=True, blank=True,related_name="usages")  # NEW

    project = models.CharField(max_length=100, blank=True)
    operator = models.ForeignKey('core.Employee', on_delete=models.PROTECT)
    def __str__(self):
        return f"Used {self.amount} L on {self.date}"


