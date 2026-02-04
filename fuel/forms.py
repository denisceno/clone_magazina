# fuel/forms.py
from django import forms
from .models import FuelEntry, FuelUsage, FuelTank
from core.models import Vehicle , Employee
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce


class FuelEntryForm(forms.ModelForm):
    class Meta:
        model = FuelEntry
        fields = ['tank', 'date', 'amount', 'supplier']
        labels = {
            'tank': 'Depozita',
            'date': 'Data',
            'amount': 'Sasia',
            'supplier': 'Kompania'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        first_tank = FuelTank.objects.first()
        if first_tank:
            self.fields['tank'].initial = first_tank


class FuelUsageForm(forms.ModelForm):
    MAX_NEGATIVE_LITERS = 50

    class Meta:
        model = FuelUsage
        fields = ["tank", "date", "vehicle", "amount","operator", "project"]
        labels = {
            "tank": "Depozita",
            "date": "Data",
            "vehicle": "Mjeti",
            "amount": "Sasia (L)",
            "operator": "Operatori",
            "project": "Shënime",

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # dropdowns të pastër
        if "vehicle" in self.fields:
            self.fields["vehicle"].queryset = Vehicle.objects.filter(is_active=True).order_by("plate")

        if "operator" in self.fields:
            self.fields["operator"].queryset = Employee.objects.filter(is_active=True).order_by("name")

        # default tank (opsionale)
        if "tank" in self.fields:
            first_tank = FuelTank.objects.first()
            if first_tank:
                self.fields["tank"].initial = first_tank

    def clean(self):
        cleaned_data = super().clean()
        tank = cleaned_data.get("tank")
        amount = cleaned_data.get("amount")

        if not tank or amount is None:
            return cleaned_data

        if amount <= 0:
            raise forms.ValidationError("Sasia duhet të jetë më e madhe se 0.")

        # ✅ open refill
        open_refill = (
            FuelEntry.objects
            .filter(tank=tank, is_closed=False)
            .order_by("-date", "-id")
            .first()
        )
        if not open_refill:
            raise forms.ValidationError(
                "Nuk ka refill aktiv (OPEN) për këtë depo. "
                "Shto një furnizim të ri dhe provo përsëri."
            )

        # calculate tank level
        entries_total = FuelEntry.objects.filter(tank=tank).aggregate(
            total=Coalesce(Sum("amount"), Value(0))
        )["total"]

        usage_total = FuelUsage.objects.filter(tank=tank).aggregate(
            total=Coalesce(Sum("amount"), Value(0))
        )["total"]

        tank_level = entries_total - usage_total

        projected_level = tank_level - amount
        if projected_level < -self.MAX_NEGATIVE_LITERS:
            raise forms.ValidationError(
                f"Kjo dalje e çon depozitën në {projected_level} L. "
                f"Limiti i lejuar është deri në -{self.MAX_NEGATIVE_LITERS} L."
            )

        return cleaned_data