from functools import wraps
from django.core.exceptions import PermissionDenied
from core.models import Employee


def is_staff_user(user) -> bool:
    """RBAC staff: superuser OR in group 'staff'."""
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name="staff").exists()
    )


def budget_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user

        # Superuser or staff always allowed
        if is_staff_user(user):
            return view_func(request, *args, **kwargs)

        # Must have Employee + have_budget=True
        employee = Employee.objects.filter(user=user, is_active=True).first()
        if not employee:
            raise PermissionDenied("This user is not linked to any Employee.")
        if not employee.have_budget:
            raise PermissionDenied("This employee has no budget access.")

        return view_func(request, *args, **kwargs)
    return _wrapped
