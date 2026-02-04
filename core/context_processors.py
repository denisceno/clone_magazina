def employee_flags(request):
    user = request.user

    if not user.is_authenticated:
        return {}

    employee = getattr(user, "employee", None)

    return {
        "user_has_budget": getattr(employee, "have_budget", False)
    }
