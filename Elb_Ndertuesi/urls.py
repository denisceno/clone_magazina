"""
URL configuration for Elb_Ndertuesi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path ,include
from django.shortcuts import redirect

handler403 = "core.views.permission_denied_view"
handler404 = "core.views.page_not_found_view"
handler500 = "core.views.server_error_view"



def root_redirect(request):
    return redirect("core:home")


urlpatterns = [
    path("", root_redirect, name="root"),
    path('admin/', admin.site.urls),
    
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("management/", include(("management.urls", "management"), namespace="management")),
    path("audit/", include(("audit.urls", "audit"), namespace="audit")),
    path("home/", include(("core.urls", "core"), namespace="core")),
    path("inventory/", include(("inventory.urls", "inventory"), namespace="inventory")),
    path("expenses/", include(("expenses.urls", "expenses"), namespace="expenses")),
    path("fuel/", include(("fuel.urls", "fuel"), namespace="fuel")),
]
