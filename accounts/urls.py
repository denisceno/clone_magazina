from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import SecureLoginView, SecureLogoutView

app_name = "accounts"

urlpatterns = [
    path("login/", SecureLoginView.as_view(), name="login"),
    path("logout/", SecureLogoutView.as_view(), name="logout"),

    path(
        "password/change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            success_url=reverse_lazy("accounts:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password/change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html",
        ),
        name="password_change_done",
    ),
]
