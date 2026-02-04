from .models import AuditLog

def log_action(
    *,
    user,
    action,
    model,
    object_id=None,
    description="",
    ip_address=None
):
    AuditLog.objects.create(
        user=user,
        action=action,
        model=model,
        object_id=object_id,
        description=description,
        ip_address=ip_address,
    )
