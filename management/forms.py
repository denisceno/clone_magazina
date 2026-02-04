# management/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from core.models import Employee, Vehicle
from fuel.models import FuelTank
from inventory.models import Depot


User = get_user_model()


class EmployeeCreateForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Konfirmo Password")
    make_staff = forms.BooleanField(required=False)

    class Meta:
        model = Employee
        fields = ["name", "position", "phone", "have_budget", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
            "position": forms.TextInput(attrs={"autocomplete": "off"}),
            "phone": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ky username ekziston.")
        return username

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Password-et nuk përputhen.")
        return cleaned


class EmployeeEditForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["name", "position", "phone", "have_budget", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
            "position": forms.TextInput(attrs={"autocomplete": "off"}),
            "phone": forms.TextInput(attrs={"autocomplete": "off"}),
        }




class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "plate",
            "chassis",
            "description",
            "insurance",
            "yearly_taxes",
            "periodic_inspection",
            "municipal_tax",
            "tachograph",
            "is_active",
        ]
        widgets = {
            "plate": forms.TextInput(attrs={"autocomplete": "off"}),
            "chassis": forms.TextInput(attrs={"autocomplete": "off"}),
            "description": forms.TextInput(attrs={"autocomplete": "off"}),
            "insurance": forms.DateInput(attrs={"type": "date"}),
            "yearly_taxes": forms.DateInput(attrs={"type": "date"}),
            "periodic_inspection": forms.DateInput(attrs={"type": "date"}),
            "municipal_tax": forms.DateInput(attrs={"type": "date"}),
            "tachograph": forms.DateInput(attrs={"type": "date"}),
        }

class FuelTankForm(forms.ModelForm):
    class Meta:
        model = FuelTank
        fields = ["name", "capacity"]


class DepotForm(forms.ModelForm):
    class Meta:
        model = Depot
        fields = ["name", "description", "is_active"]
        labels = {
            "name": "Emri i Magazinës",
            "description": "Përshkrimi",
            "is_active": "Magazina aktive",
        }
