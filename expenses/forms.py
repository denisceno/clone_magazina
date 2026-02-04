from django import forms
from .models import Expense, BudgetAdjustment
from core.models import Employee

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["employee", "description", "amount", "date"]
        labels = {
            "employee": "Emri",
            "description": "Përshkrimi",
            "amount": "Shuma",
            "date": "Data",
        }
        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Show only active employees with budget access
        self.fields["employee"].queryset = (
            Employee.objects.filter(is_active=True, have_budget=True).order_by("name")
        )

        # Placeholder option at top
        self.fields["employee"].empty_label = "Zgjidh punonjësin"


class BudgetAdjustmentForm(forms.ModelForm):
    class Meta:
        model = BudgetAdjustment
        fields = ["employee", "adjustment_type", "amount", "date", "note"]

        labels = {
            "employee": "Emri",
            "adjustment_type": "Shto / Zbrit",
            "amount": "Shuma",
            "date": "Data",
            "note": "Shënime",
        }

        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
            "adjustment_type": forms.Select(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "note": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only active employees with budget access
        self.fields["employee"].queryset = (
            Employee.objects.filter(is_active=True, have_budget=True).order_by("name")
        )

        # Placeholder
        self.fields["employee"].empty_label = "Zgjidh punonjësin"

