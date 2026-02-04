from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.contrib.auth.views import redirect_to_login

def staff_required(view_func=None, *, raise_exception=False):
    """
    Allow only staff or superuser.
    - raise_exception=False -> redirects to login page (default Django behavior)
    - raise_exception=True  -> returns 403 (PermissionDenied) if logged in but not allowed
    """

    def check(user):
        return user.is_authenticated and (user.is_staff or user.is_superuser)

    decorator = user_passes_test(check)

    if raise_exception:
        # if user is logged in but not allowed -> 403 instead of redirect loop
        def _wrapped(view):
            def inner(request, *args, **kwargs):
                if not request.user.is_authenticated:
                    return decorator(view)(request, *args, **kwargs)
                if not check(request.user):
                    raise PermissionDenied
                return view(request, *args, **kwargs)
            return inner
        return _wrapped(view_func) if view_func else _wrapped

    return decorator(view_func) if view_func else decorator




def staff_or_own_employee_detail(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        # staff/superuser can see any employee
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        employee_id = kwargs.get("employee_id")
        if employee_id is None:
            raise PermissionDenied("Missing employee_id")

        # regular user must be linked to an Employee
        if not hasattr(request.user, "employee") or request.user.employee is None:
            raise PermissionDenied("User is not linked to an Employee.")

        # allow only if it's their own employee page
        if int(employee_id) != int(request.user.employee.id):
            raise PermissionDenied("You can only view your own page.")

        return view_func(request, *args, **kwargs)

    return _wrapped