from django.contrib import admin
from .models import FuelEntry, FuelUsage, FuelTank 

admin.site.register(FuelTank)
admin.site.register(FuelEntry)
admin.site.register(FuelUsage)
