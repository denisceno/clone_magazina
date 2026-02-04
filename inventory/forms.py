from django import forms
from .models import Product, Depot, WithdrawalHeader, WithdrawalItem, ReturnHeader, ReturnItem
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from core.models import Employee


class DepotForm(forms.ModelForm):
    class Meta:
        model = Depot
        fields = ["name", "description", "is_active"]
        labels = {
            "name": "Emri i Magazinës",
            "description": "Përshkrimi",
            "is_active": "Aktive"
        }
        widgets = {
            "description": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Përshkrimi i magazinës (opsionale)",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            })
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "depot",
            "name",
            "description",
            "date",
            "item_type",
            "quantity",
            "unit",
            "price"
        ]
        labels = {
            "depot": "Magazina",
            "name": "Emri",
            "description": "Përshkrimi",
            "date": "Data",
            "item_type": "Kategoria",
            "quantity": "Sasia",
            "unit": "Njësia",
            "price": "Çmimi"
        }

    def clean(self):
        cleaned = super().clean()
        depot = cleaned.get("depot")
        name = cleaned.get("name")

        if depot and name:
            qs = Product.objects.filter(depot=depot, name__iexact=name)

            # allow editing the same product without triggering duplicate
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                # show message under the "name" field
                self.add_error(
                    "name",
                    "Ky produkt ekziston tashmë në këtë magazinë."
                )

        return cleaned




class AddQuantityForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        label="Sasia"
    )


class WithdrawalHeaderForm(forms.ModelForm):
    class Meta:
        model = WithdrawalHeader
        fields = ["employee", "date", "notes"]
        widgets = {
            "employee": forms.Select(attrs={
                "class": "form-control"
            }),
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Shënime"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ ONLY active employees
        self.fields["employee"].queryset = (
            Employee.objects
            .filter(is_active=True)
            .order_by("name")
        )

        # ✅ placeholder option
        self.fields["employee"].empty_label = "Punonjësi"



class WithdrawalItemForm(forms.ModelForm):
    class Meta:
        model = WithdrawalItem
        fields = ["product", "quantity"]

        widgets = {
            "product": forms.Select(
                attrs={
                    "class": "product-select",
                    "data-desc": "",   # dynamic description (we will fill it in template)
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "placeholder": "Quantity",   # placeholder INSIDE input
                    "class": "quantity-input"
                }
            ),
        }

        # REMOVE LABELS ABOVE FIELDS
        labels = {
            "product": "",
            "quantity": "",
        }

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity")

        if product and quantity:
            if quantity <= 0:
                raise ValidationError("Quantity must be greater than zero.")

            if quantity > product.quantity:
                raise ValidationError(
                    f"Not enough stock for {product.name}. Available: {product.quantity}"
                )

        return cleaned_data



WithdrawalItemFormSet = inlineformset_factory(
    WithdrawalHeader,
    WithdrawalItem,
    form=WithdrawalItemForm,
    extra=1,
    can_delete=True
)


class ReturnHeaderForm(forms.ModelForm):
    class Meta:
        model = ReturnHeader
        fields = ["employee", "date", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"})
        }


class ReturnItemForm(forms.ModelForm):
    class Meta:
        model = ReturnItem
        fields = ["withdrawal_item", "quantity"]

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop("employee", None)
        super().__init__(*args, **kwargs)

        # Only returnable items held by this employee
        if employee:
            self.fields["withdrawal_item"].queryset = WithdrawalItem.objects.filter(
                header__employee=employee,
                product__item_type="returnable"
            ).select_related("product")
