# management/urls.py
from django.urls import path
from . import views

app_name = "management"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Employees
    path("employees/", views.employee_list, name="employee-list"),
    path("employees/create/", views.employee_create, name="employee-create"),
    path("employees/<int:pk>/", views.employee_detail, name="employee-detail"),
    path("employees/<int:pk>/edit/", views.employee_edit, name="employee-edit"),
    path("employees/<int:pk>/delete/", views.employee_delete, name="employee-delete"),

    # Vehicles
    path("vehicles/", views.vehicle_list, name="vehicle-list"),
    path("vehicles/create/", views.vehicle_create, name="vehicle-create"),
    path("vehicles/<int:pk>/", views.vehicle_detail, name="vehicle-detail"),
    path("vehicles/<int:pk>/edit/", views.vehicle_edit, name="vehicle-edit"),
    path("vehicles/<int:pk>/delete/", views.vehicle_delete, name="vehicle-delete"),

    # Fuel Tanks
    path("tanks/", views.tank_list, name="tank-list"),
    path("tanks/create/", views.tank_create, name="tank-create"),
    path("tanks/<int:pk>/", views.tank_detail, name="tank-detail"),
    path("tanks/<int:pk>/edit/", views.tank_edit, name="tank-edit"),
    path("tanks/<int:pk>/delete/", views.tank_delete, name="tank-delete"),

    # Depots
    path("depots/", views.depot_list, name="depot-list"),
    path("depots/create/", views.depot_create, name="depot-create"),
    path("depots/<int:pk>/", views.depot_detail, name="depot-detail"),
    path("depots/<int:pk>/edit/", views.depot_edit, name="depot-edit"),
    path("depots/<int:pk>/delete/", views.depot_delete, name="depot-delete"),
]
