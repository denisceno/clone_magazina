from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.login_path = reverse("accounts:login")
        self.logout_path = reverse("accounts:logout")

    def __call__(self, request):
        path = request.path

        # Allow admin + static/media
        if path.startswith("/admin/") or path.startswith("/static/") or path.startswith("/media/"):
            return self.get_response(request)

        # Allow favicon
        if path == "/favicon.ico":
            return self.get_response(request)

        # Allow auth endpoints
        if path in (self.login_path, self.logout_path):
            return self.get_response(request)

        # If not logged in -> send to login
        if not request.user.is_authenticated:
            return redirect("accounts:login")

        return self.get_response(request)
