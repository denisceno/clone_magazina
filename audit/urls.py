from django.urls import path
from .views import audit_dashboard

app_name = "audit"

urlpatterns = [
    path("", audit_dashboard, name="audit-dashboard"),
]
