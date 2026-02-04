from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache


@method_decorator(never_cache, name="dispatch")
class SecureLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class SecureLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")
