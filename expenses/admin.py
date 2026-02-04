from django.contrib import admin
from .models import EmployeeBudget , Expense ,BudgetAdjustment

# Register your models here.

admin.site.register(EmployeeBudget)
admin.site.register(Expense)
admin.site.register(BudgetAdjustment)