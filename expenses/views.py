from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db.models import Sum, OuterRef, Subquery
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache

from accounts.decorators import staff_or_own_employee_detail
from audit.utils import log_action
from audit.middleware import get_client_ip
from management.permissions import staff_required, employee_required
from .permissions import budget_required, is_staff_user

from core.models import Employee
from .models import EmployeeBudget, Expense, BudgetAdjustment
from .forms import ExpenseForm, BudgetAdjustmentForm


# ==========================
# HELPERS
# ==========================


def get_logged_employee(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Not logged in.")

    try:
        return request.user.employee  # OneToOne relation
    except Employee.DoesNotExist:
        raise PermissionDenied("This user is not linked to any Employee.")


def _get_or_create_budget(employee: Employee, lock: bool = False) -> EmployeeBudget:
    if lock:
        # Try to get with lock first
        budget = EmployeeBudget.objects.select_for_update().filter(employee=employee).first()
        if budget:
            return budget
    # Create if doesn't exist (or get without lock)
    budget, _ = EmployeeBudget.objects.get_or_create(
        employee=employee,
        defaults={"balance": 0},
    )
    if lock and budget:
        # Re-fetch with lock if we just created it
        budget = EmployeeBudget.objects.select_for_update().get(pk=budget.pk)
    return budget


# ==========================
# VIEWS
# ==========================

@employee_required
@budget_required
def expenses_home(request):
    # Staff mode: show all employees with their budget
    if is_staff_user(request.user):
        budget_subq = (
            EmployeeBudget.objects
            .filter(employee_id=OuterRef("pk"))
            .values("balance")[:1]
        )

        employees = (
            Employee.objects
            .filter(have_budget=True , is_active=True)
            .order_by("name")
            .annotate(balance=Subquery(budget_subq))
        )

        return render(request, "expenses/expenses-home.html", {"employees": employees})

    # Normal employee -> go to their own employee detail
    emp = get_logged_employee(request)
    return redirect("expenses:expenses-employee-detail", employee_id=emp.id)


@staff_or_own_employee_detail
@budget_required
def employee_detail(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    budget = _get_or_create_budget(employee)

    expenses = Expense.objects.filter(employee=employee).order_by("-date", "-id")
    adjustments = BudgetAdjustment.objects.filter(employee=employee).order_by("-date", "-id")

    total_expenses = expenses.aggregate(total=Sum("amount"))["total"] or 0

    can_add_expense = False
    if request.user.is_superuser:
        can_add_expense = True
    else:
        me = get_logged_employee(request)
        can_add_expense = (me.id == employee.id)

    return render(request, "expenses/employee_detail.html", {
        "employee": employee,
        "budget": budget,
        "expenses": expenses,
        "adjustments": adjustments,
        "total_expenses": total_expenses,
        "can_add_expense": can_add_expense,
    })


@staff_or_own_employee_detail
@budget_required
def budget_adjustments(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    budget = _get_or_create_budget(employee)

    adjustments = BudgetAdjustment.objects.filter(employee=employee).order_by("-date", "-id")

    return render(request, "expenses/budget_adjustments.html", {
        "employee": employee,
        "budget": budget,
        "adjustments": adjustments,
    })


@employee_required
@budget_required
@never_cache
def add_expense(request):
    # ✅ Only superuser can add expense to other employees
    admin_mode = request.user.is_superuser

    form = ExpenseForm(request.POST or None)

    # ✅ If NOT superuser (including staff): remove employee picker BEFORE validation
    if not admin_mode and "employee" in form.fields:
        form.fields.pop("employee")

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            expense = form.save(commit=False)

            if admin_mode:
                # superuser must choose employee
                if not expense.employee_id:
                    raise PermissionDenied("Employee must be selected.")
                employee = expense.employee
            else:
                # staff + employees can only add for themselves
                employee = get_logged_employee(request)
                expense.employee = employee

            # Lock budget row to prevent race conditions
            budget = _get_or_create_budget(employee, lock=True)

            expense.save()
            budget.balance = budget.balance - expense.amount
            budget.save()

            log_action(
                user=request.user,
                action="CREATE",
                model="Expense",
                object_id=str(expense.id),
                description=(
                    f"Expense {expense.amount} by {employee.name} "
                    f"(new balance: {budget.balance}) - {expense.description}"
                ),
                ip_address=get_client_ip(request),
            )

        return redirect("expenses:expenses-employee-detail", employee_id=employee.id)

    return render(request, "expenses/expense_form.html", {"form": form})



@staff_required
@never_cache
def adjust_budget(request):
    form = BudgetAdjustmentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            adj = form.save(commit=False)

            # Lock budget row to prevent race conditions
            budget = _get_or_create_budget(adj.employee, lock=True)

            if adj.adjustment_type == BudgetAdjustment.ADD:
                budget.balance = budget.balance + adj.amount
            else:
                # allow going negative
                budget.balance = budget.balance - adj.amount

            adj.save()
            budget.save()

            log_action(
                user=request.user,
                action="ADJUST",
                model="BudgetAdjustment",
                object_id=str(adj.id),
                description=(
                    f"{adj.get_adjustment_type_display()} {adj.amount} "
                    f"for {adj.employee.name} (new balance: {budget.balance})"
                ),
                ip_address=get_client_ip(request),
            )

        return redirect("expenses:expenses-employee-detail", employee_id=adj.employee.id)

    return render(request, "expenses/budget_adjust_form.html", {"form": form})
