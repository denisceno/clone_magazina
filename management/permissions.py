# management/permissions.py
from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

STAFF_GROUP = "staff"
EMPLOYEE_GROUP = "employee"


def _in_group(user, name):
    return user.groups.filter(name=name).exists()


def _deny_or_login(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    raise PermissionDenied("You do not have permission to access this page.")


def admin_required(view_func):
    """
    Admin = superuser only
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return _deny_or_login(request)
    return _wrapped


def staff_required(view_func):
    """
    Staff = superuser OR member of 'staff' group
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if (
            user.is_authenticated and
            (user.is_superuser or _in_group(user, STAFF_GROUP))
        ):
            return view_func(request, *args, **kwargs)
        return _deny_or_login(request)
    return _wrapped


def employee_required(view_func):
    """
    Employee = superuser OR staff OR employee group
    (staff can always see employee pages)
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if (
            user.is_authenticated and (
                user.is_superuser or
                _in_group(user, STAFF_GROUP) or
                _in_group(user, EMPLOYEE_GROUP)
            )
        ):
            return view_func(request, *args, **kwargs)
        return _deny_or_login(request)
    return _wrapped
