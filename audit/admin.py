from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "user",
        "action",
        "model",
        "object_id",
        "ip_address",
    )
    list_filter = ("action", "model")
    search_fields = ("user__username", "description")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
