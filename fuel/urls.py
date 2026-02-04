from django.urls import path
from . import views

app_name = "fuel"

urlpatterns = [
    path('', views.fuel_home, name='fuel-home'),
    path('entry/', views.add_entry, name='fuel-add-entry'),
    path('usage/', views.add_usage, name='fuel-add-usage'),
    path("vehicle-usage/", views.vehicle_usage, name="vehicle-usage"),
    path("fuel-entries/", views.fuel_entries_list, name="fuel-entries"),
    
    path("entries/<int:id>/close/", views.close_refill, name="fuel-entry-close"),
    path("entries/<int:id>/", views.fuel_entry_detail, name="fuel-entry-detail"),

    path("furnizimi/<int:id>/", views.fuel_entry_detail, name="fuel-entry-detail-alt"),
    path("ajax/refill-dates/<int:tank_id>/", views.existing_refill_dates, name="existing-refill-dates"),
]