import logging

from django.shortcuts import render
from django.views.decorators.cache import never_cache

logger = logging.getLogger("django.security.csrf")


def csrf_failure(request, reason=""):
    logger.warning(
        "CSRF FAIL path=%s referer=%s reason=%s",
        request.path,
        request.META.get("HTTP_REFERER"),
        reason,
    )
    return render(request, "core/csrf_failed.html", {"reason": reason}, status=403)

def permission_denied_view(request, exception=None):
    return render(request, "core/403.html", status=403)

def page_not_found_view(request, exception=None):
    return render(request, "core/404.html", status=404)

def server_error_view(request):
    return render(request, "core/500.html", status=500)


@never_cache
def home(request):
    return render(request, "core/home.html")
