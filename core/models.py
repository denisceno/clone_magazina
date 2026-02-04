from django.db import models
from django.conf import settings

# Create your models here.

class Employee(models.Model):
    user = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="employee"
    )
    name = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    phone = models.CharField(max_length=50,blank=True)

    have_budget = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    

class Vehicle(models.Model):
    plate = models.CharField(max_length=50, unique=True)
    chassis = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=100,blank=True)

    insurance = models.DateField(blank=True, null=True)
    yearly_taxes = models.DateField(blank=True, null=True)
    periodic_inspection = models.DateField(blank=True, null=True)

    municipal_tax = models.DateField(blank=True, null=True)
    tachograph = models.DateField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.plate
