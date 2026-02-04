from django.urls import path
from . import views

app_name = "expenses"

urlpatterns = [
    path("", views.expenses_home, name="expenses-home"),

    path(
        "employee/<int:employee_id>/",
        views.employee_detail,
        name="expenses-employee-detail",
    ),

    path(
        "employee/<int:employee_id>/adjustments/",
        views.budget_adjustments,
        name="expenses-budget-adjustments",
    ),

    path("add/", views.add_expense, name="expenses-add-expense"),

    path("adjust-budget/", views.adjust_budget, name="expenses-adjust-budget"),
]
