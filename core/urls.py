from django.urls import path
from . import views
from django.views.generic import RedirectView
from django.templatetags.static import static

app_name = "core"

urlpatterns = [
    path('',views.home,name='home'),
    path("favicon.ico", RedirectView.as_view(url=static("core/favicon.ico"))),
]