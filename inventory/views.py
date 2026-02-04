from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.db import transaction
from django.db.models import Sum, Q, F, IntegerField, Case, When
from django.db.models.functions import Coalesce
from django.views.decorators.cache import never_cache

from audit.utils import log_action
from audit.middleware import get_client_ip
from management.permissions import staff_required, admin_required

from core.models import Employee
from .models import Depot, Product, WithdrawalHeader, WithdrawalItem, ReturnItem, ReturnHeader
from .forms import (
    ProductForm,
    DepotForm,
    AddQuantityForm,
    WithdrawalHeaderForm,
    WithdrawalItemFormSet,
    WithdrawalItemForm,
    ReturnItemForm,
    ReturnHeaderForm,
)


@staff_required
def inventory_home(request):
    depots = Depot.objects.all()
    return render(request, "inventory/home.html", {"depots": depots})


@staff_required
def depot_detail(request, depot_id):
    depot = get_object_or_404(Depot, id=depot_id)
    search = request.GET.get("q", "")

    products = (
        Product.objects
        .filter(depot=depot)
        .annotate(
            withdrawn_sum=Coalesce(Sum("withdrawalitem__quantity"), 0),
            returned_sum=Coalesce(Sum("withdrawalitem__returnitem__quantity"), 0),
        )
        .annotate(outstanding=F("withdrawn_sum") - F("returned_sum"))
        .annotate(
            total_quantity=Case(
                When(item_type="returnable", then=F("quantity") + F("outstanding")),
                default=F("quantity"),
                output_field=IntegerField(),
            )
        )
        .order_by("name")
    )

    if search:
        products = products.filter(name__icontains=search)

    return render(request, "inventory/depot_detail.html", {
        "depot": depot,
        "products": products,
        "search": search,
    })



@staff_required
def all_products(request):
    search = request.GET.get("q", "")
    sort = request.GET.get("sort", "name")

    valid_sorts = {
        "name": "name",
        "name_desc": "-name",
        "qty": "quantity",
        "qty_desc": "-quantity",
        "depot": "depot__name",
        "depot_desc": "-depot__name",
    }
    order_by = valid_sorts.get(sort, "name")

    products = (
        Product.objects
        .select_related("depot")
        .filter(depot__is_active=True)
        .annotate(
            withdrawn_sum=Coalesce(Sum("withdrawalitem__quantity"), 0),
            returned_sum=Coalesce(Sum("withdrawalitem__returnitem__quantity"), 0),
        )
        .annotate(
            outstanding=F("withdrawn_sum") - F("returned_sum"),
        )
        .annotate(
            total_quantity=Case(
                When(item_type="returnable", then=F("quantity") + F("outstanding")),
                default=F("quantity"),
                output_field=IntegerField(),
            )
        )
        .order_by(order_by)
    )

    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    return render(request, "inventory/all_products.html", {
        "products": products,
        "search": search,
        "sort": sort,
    })



@staff_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    withdrawn_items = (
        WithdrawalItem.objects
        .filter(product=product)
        .select_related("header", "header__employee")
        .annotate(returned_sum=Coalesce(Sum("returnitem__quantity"), 0))
        .annotate(outstanding=F("quantity") - F("returned_sum"))
    )

    items_display = []
    total_taken = 0

    for w in withdrawn_items:
        if w.outstanding > 0:
            items_display.append({
                "employee": w.header.employee.name,
                "qty": w.outstanding,
                "date": w.header.date,
                "notes": w.header.notes,
            })
            total_taken += w.outstanding

    total_stock = product.quantity + total_taken

    return render(request, "inventory/product_detail.html", {
        "product": product,
        "items_display": items_display,
        "total_taken": total_taken,
        "total_stock": total_stock,
    })


# ==========================
# CREATE / UPDATE FORMS (POST) => NEVER CACHE
# ==========================

@staff_required
@never_cache
def add_product(request):
    form = ProductForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        product = form.save()

        log_action(
            user=request.user,
            action="CREATE",
            model="Product",
            object_id=str(product.id),
            description=f"Added product {product.name} to depot {product.depot.name}",
            ip_address=get_client_ip(request),
        )
        return redirect("inventory:add-product")

    return render(request, "inventory/add_product.html", {"form": form})


@staff_required
@never_cache
def add_quantity(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = AddQuantityForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        qty = form.cleaned_data["quantity"]
        product.quantity += qty
        product.save()

        log_action(
            user=request.user,
            action="ADD",
            model="Product",
            object_id=str(product.id),
            description=f"Added {qty} units to product '{product.name}' (new stock: {product.quantity})",
            ip_address=get_client_ip(request),
        )

        return redirect("inventory:product-detail", product_id=product.id)

    return render(request, "inventory/add_quantity.html", {
        "product": product,
        "form": form
    })


@admin_required
@never_cache
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = ProductForm(request.POST or None, instance=product)

    if request.method == "POST" and form.is_valid():
        form.save()

        log_action(
            user=request.user,
            action="UPDATE",
            model="Product",
            object_id=str(product.id),
            description=f"Edited product {product.name}",
            ip_address=get_client_ip(request),
        )
        return redirect("inventory:depot-detail", product.depot.id)

    return render(request, "inventory/edit_product.html", {"product": product, "form": form})


# ==========================
# DELETE PRODUCT (SAFE: POST ONLY)
# ==========================

@admin_required
@never_cache
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    depot_id = product.depot.id

    if request.method == "POST":
        log_action(
            user=request.user,
            action="DELETE",
            model="Product",
            object_id=str(product.id),
            description=f"Deleted product {product.name}",
            ip_address=get_client_ip(request),
        )
        product.delete()
        return redirect("inventory:depot-detail", depot_id)

    # GET -> confirmation page
    return render(request, "inventory/delete_product_confirm.html", {
        "product": product,
        "depot_id": depot_id,
    })


@staff_required
def employees_view(request, employee_id=None):
    employees = Employee.objects.all().order_by("name")

    selected_employee = None
    withdrawals = None

    if employee_id:
        selected_employee = get_object_or_404(Employee, id=employee_id)
        withdrawals = WithdrawalItem.objects.filter(
            header__employee=selected_employee,
            product__item_type="returnable"
        ).select_related("product")

        withdrawals = [w for w in withdrawals if w.outstanding_qty > 0]

    context = {
        "employees": employees,
        "selected_employee": selected_employee,
        "withdrawals": withdrawals,
    }

    return render(request, "inventory/employees.html", context)


@login_required
def my_returnables(request):
    employee = Employee.objects.filter(user=request.user).first()
    if not employee:
        return redirect("core:home")

    withdrawals = (
        WithdrawalItem.objects
        .select_related("product", "header")
        .filter(header__employee=employee)
        .annotate(returned_sum=Coalesce(Sum("returnitem__quantity"), 0))
        .annotate(outstanding_calc=F("quantity") - F("returned_sum"))
        .filter(outstanding_calc__gt=0)
        .order_by("-header__date")
    )

    return render(request, "inventory/my_returnables.html", {
        "selected_employee": employee,
        "withdrawals": withdrawals,
    })


@staff_required
@never_cache
def create_withdrawal(request):
    ItemFormSet = modelformset_factory(
        WithdrawalItem,
        form=WithdrawalItemForm,
        extra=1
    )

    products = Product.objects.select_related("depot").filter(depot__is_active=True).order_by("name")

    if request.method == "POST":
        header_form = WithdrawalHeaderForm(request.POST)
        formset = ItemFormSet(request.POST)

        if header_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                header = header_form.save()

                for form in formset:
                    if form.cleaned_data.get("product") and form.cleaned_data.get("quantity"):
                        item = form.save(commit=False)
                        item.header = header
                        qty = item.quantity

                        # Lock the product row to prevent race conditions
                        product = Product.objects.select_for_update().get(id=item.product_id)

                        if product.quantity < qty:
                            transaction.set_rollback(True)
                            return render(request, "inventory/withdrawal_form.html", {
                                "header_form": header_form,
                                "formset": formset,
                                "products": products,
                                "error": f"Not enough stock for {product.name}. Available: {product.quantity}",
                            })

                        item.product = product
                        item.save()
                        product.quantity -= qty
                        product.save()

                        log_action(
                            user=request.user,
                            action="WITHDRAW",
                            model="Product",
                            object_id=str(product.id),
                            description=f"Withdrawn {qty} of {product.name} by {header.employee.name}",
                            ip_address=get_client_ip(request),
                        )

                return redirect("inventory:inventory-home")

    else:
        header_form = WithdrawalHeaderForm()
        formset = ItemFormSet(queryset=WithdrawalItem.objects.none())

    return render(request, "inventory/withdrawal_form.html", {
        "header_form": header_form,
        "formset": formset,
        "products": products,
    })


 # make sure imported

@staff_required
@never_cache
def return_item(request, withdrawal_item_id):
    withdrawal_item = get_object_or_404(WithdrawalItem, id=withdrawal_item_id)
    employee = withdrawal_item.header.employee
    product = withdrawal_item.product

    if request.method == "POST":
        raw_qty = request.POST.get("quantity")

        try:
            qty = int(raw_qty or "0")
        except Exception:
            qty = 0

        if qty <= 0 or qty > withdrawal_item.outstanding_qty:
            return render(request, "inventory/return_item.html", {
                "withdrawal_item": withdrawal_item,
                "employee": employee,
                "product": product,
                "error": f"Invalid return quantity. Max: {withdrawal_item.outstanding_qty}"
            })

        with transaction.atomic():
            # Lock the product row to prevent race conditions
            product = Product.objects.select_for_update().get(id=product.id)

            # Create a return header
            return_header = ReturnHeader.objects.create(employee=employee)

            # Create return item
            ReturnItem.objects.create(
                header=return_header,
                withdrawal_item=withdrawal_item,
                quantity=qty
            )

            # Put back into stock
            product.quantity += qty
            product.save()

            log_action(
                user=request.user,
                action="RETURN",
                model="Product",
                object_id=str(product.id),
                description=f"Returned {qty} of {product.name} by {employee.name}",
                ip_address=get_client_ip(request),
            )

        return redirect("inventory:employee-detail", employee_id=employee.id)

    return render(request, "inventory/return_item.html", {
        "withdrawal_item": withdrawal_item,
        "employee": employee,
        "product": product,
    })



@staff_required
def withdraw_detail(request, id):
    item = get_object_or_404(WithdrawalItem, id=id)
    header = item.header

    return render(request, "inventory/withdraw_detail.html", {
        "item": item,
        "header": header,
    })
