from django.shortcuts import render
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache

from management.permissions import admin_required
from .models import AuditLog

LOGS_PER_PAGE = 50


@admin_required
@never_cache
def audit_dashboard(request):
    module = request.GET.get("module", "all")
    action = request.GET.get("action", "all")

    logs = AuditLog.objects.select_related("user").order_by("-timestamp")

    # MODULE FILTER
    if module == "inventory":
        logs = logs.filter(model__in=[
            "Depot",
            "Product",
            "WithdrawalItem",
            "ReturnItem",
            "WithdrawalHeader",
            "ReturnHeader",
        ])

    elif module == "fuel":
        logs = logs.filter(model__in=[
            "FuelEntry",
            "FuelUsage",
            "FuelTank",
            "Vehicle",
        ])

    elif module == "core":
        logs = logs.filter(model__in=[
            "Employee",
            "Vehicle",
        ])

    elif module == "expenses":
        logs = logs.filter(model__in=[
            "EmployeeBudget",
            "Expense",
            "BudgetAdjustment",
        ])

    elif module == "management":
        logs = logs.filter(model__in=[
            "Employee",
            "Vehicle",
            "FuelTank",
            "Depot",
        ])

    # ACTION FILTER
    if action != "all":
        logs = logs.filter(action=action)

    # PAGINATION
    paginator = Paginator(logs, LOGS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "audit/dashboard.html", {
        "logs": page_obj,
        "page_obj": page_obj,
        "module": module,
        "action": action,
    })
