from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group

from audit.utils import log_action


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(post_migrate)
def ensure_default_groups(sender, **kwargs):
    if sender.name != "accounts":
        return
    Group.objects.get_or_create(name="employee")
    Group.objects.get_or_create(name="staff")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    log_action(
        user=user,
        action="LOGIN",
        model="User",
        ip_address=get_client_ip(request),
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user is None:
        return
    log_action(
        user=user,
        action="LOGOUT",
        model="User",
        ip_address=get_client_ip(request),
    )
