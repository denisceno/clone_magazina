from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.views.decorators.cache import never_cache

from core.models import Employee, Vehicle
from fuel.models import FuelTank
from inventory.models import Depot

from .forms import EmployeeCreateForm, EmployeeEditForm, VehicleForm, FuelTankForm, DepotForm
from .permissions import admin_required

from audit.utils import log_action
from audit.middleware import get_client_ip


@admin_required
def dashboard(request):
    return render(request, "management/dashboard.html")


# ==========================
# EMPLOYEES
# ==========================

@admin_required
def employee_list(request):
    employees = Employee.objects.order_by("-is_active", "name")
    return render(request, "management/employees/list.html", {"employees": employees})


User = get_user_model()


@admin_required
@never_cache
def employee_create(request):
    if request.method == "POST":
        form = EmployeeCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # 1) Create user
                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password1"],
                )

                # 2) Assign groups
                employee_group, _ = Group.objects.get_or_create(name="employee")
                user.groups.add(employee_group)

                if form.cleaned_data.get("make_staff", False):
                    staff_group, _ = Group.objects.get_or_create(name="staff")
                    user.groups.add(staff_group)
                    user.is_staff = True  # optional but recommended

                user.save()

                # 3) Create employee linked to that user
                employee = form.save(commit=False)
                employee.user = user
                employee.save()

                log_action(
                    user=request.user,
                    action="CREATE",
                    model="Employee",
                    object_id=str(employee.id),
                    description=f"Employee created and linked to user {user.username}",
                    ip_address=get_client_ip(request),
                )

            return redirect("management:employee-list")
    else:
        form = EmployeeCreateForm()

    return render(request, "management/employees/form.html", {"form": form})


@admin_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    return render(request, "management/employees/detail.html", {"employee": employee})


@admin_required
@never_cache
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeEditForm(request.POST or None, instance=employee)

    if request.method == "POST" and form.is_valid():
        emp = form.save()
        log_action(
            user=request.user,
            action="UPDATE",
            model="Employee",
            object_id=str(emp.pk),
            description=f"Updated employee: {emp.name}",
            ip_address=get_client_ip(request),
        )
        return redirect("management:employee-detail", pk=emp.pk)

    return render(request, "management/employees/form.html", {"form": form, "employee": employee})


@admin_required
@never_cache
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == "POST":
        name = employee.name
        pos = employee.position
        emp_pk = employee.pk
        linked_user = employee.user

        with transaction.atomic():
            employee.delete()
            # Also delete the linked user account to avoid orphans
            if linked_user:
                linked_user.delete()

        log_action(
            user=request.user,
            action="DELETE",
            model="Employee",
            object_id=str(emp_pk),
            description=f"Deleted employee: {name} ({pos})" + (f" and user: {linked_user.username}" if linked_user else ""),
            ip_address=get_client_ip(request),
        )

        return redirect("management:employee-list")

    return render(request, "management/employees/confirm_delete.html", {"employee": employee})


# ==========================
# VEHICLES
# ==========================

@admin_required
def vehicle_list(request):
    vehicles = Vehicle.objects.order_by("-is_active", "plate")
    return render(request, "management/vehicles/list.html", {"vehicles": vehicles})


@admin_required
@never_cache
def vehicle_create(request):
    form = VehicleForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        v = form.save()

        log_action(
            user=request.user,
            action="CREATE",
            model="Vehicle",
            object_id=str(v.pk),
            description=f"Created vehicle: {v.plate}",
            ip_address=get_client_ip(request),
        )

        return redirect("management:vehicle-detail", pk=v.pk)

    return render(request, "management/vehicles/form.html", {"form": form})


@admin_required
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    return render(request, "management/vehicles/detail.html", {"vehicle": vehicle})


@admin_required
@never_cache
def vehicle_edit(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    form = VehicleForm(request.POST or None, instance=vehicle)

    if request.method == "POST" and form.is_valid():
        v = form.save()

        log_action(
            user=request.user,
            action="UPDATE",
            model="Vehicle",
            object_id=str(v.pk),
            description=f"Updated vehicle: {v.plate}",
            ip_address=get_client_ip(request),
        )

        return redirect("management:vehicle-detail", pk=v.pk)

    return render(request, "management/vehicles/form.html", {"form": form, "vehicle": vehicle})


@admin_required
@never_cache
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)

    if request.method == "POST":
        plate = vehicle.plate
        v_pk = vehicle.pk
        vehicle.delete()

        log_action(
            user=request.user,
            action="DELETE",
            model="Vehicle",
            object_id=str(v_pk),
            description=f"Deleted vehicle: {plate}",
            ip_address=get_client_ip(request),
        )

        return redirect("management:vehicle-list")

    return render(request, "management/vehicles/confirm_delete.html", {"vehicle": vehicle})


# ==========================
# FUEL TANKS
# ==========================

@admin_required
def tank_list(request):
    tanks = FuelTank.objects.order_by("name")
    return render(request, "management/tanks/list.html", {"tanks": tanks})


@admin_required
@never_cache
def tank_create(request):
    form = FuelTankForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        tank = form.save()

        log_action(
            user=request.user,
            action="CREATE",
            model="FuelTank",
            object_id=str(tank.pk),
            description=f"Created fuel tank: {tank.name} (Capacity: {tank.capacity}L)",
            ip_address=get_client_ip(request),
        )

        return redirect("management:tank-detail", pk=tank.pk)

    return render(request, "management/tanks/form.html", {"form": form})


@admin_required
def tank_detail(request, pk):
    tank = get_object_or_404(FuelTank, pk=pk)
    return render(request, "management/tanks/detail.html", {"tank": tank})


@admin_required
@never_cache
def tank_edit(request, pk):
    tank = get_object_or_404(FuelTank, pk=pk)
    old_name = tank.name
    form = FuelTankForm(request.POST or None, instance=tank)

    if request.method == "POST" and form.is_valid():
        tank = form.save()

        log_action(
            user=request.user,
            action="UPDATE",
            model="FuelTank",
            object_id=str(tank.pk),
            description=f"Updated fuel tank: {old_name} → {tank.name} (Capacity: {tank.capacity}L)",
            ip_address=get_client_ip(request),
        )

        return redirect("management:tank-detail", pk=tank.pk)

    return render(request, "management/tanks/form.html", {"form": form, "tank": tank})


@admin_required
@never_cache
def tank_delete(request, pk):
    tank = get_object_or_404(FuelTank, pk=pk)

    if request.method == "POST":
        name = tank.name
        t_pk = tank.pk
        tank.delete()

        log_action(
            user=request.user,
            action="DELETE",
            model="FuelTank",
            object_id=str(t_pk),
            description=f"Deleted fuel tank: {name}",
            ip_address=get_client_ip(request),
        )

        return redirect("management:tank-list")

    return render(request, "management/tanks/confirm_delete.html", {"tank": tank})


# ==========================
# DEPOTS
# ==========================

@admin_required
def depot_list(request):
    depots = Depot.objects.order_by("name")
    return render(request, "management/depots/list.html", {"depots": depots})


@admin_required
@never_cache
def depot_create(request):
    form = DepotForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        depot = form.save()

        log_action(
            user=request.user,
            action="CREATE",
            model="Depot",
            object_id=str(depot.pk),
            description=f"Created depot: {depot.name}",
            ip_address=get_client_ip(request),
        )

        return redirect("management:depot-detail", pk=depot.pk)

    return render(request, "management/depots/form.html", {"form": form})


@admin_required
def depot_detail(request, pk):
    depot = get_object_or_404(Depot, pk=pk)
    return render(request, "management/depots/detail.html", {"depot": depot})


@admin_required
@never_cache
def depot_edit(request, pk):
    depot = get_object_or_404(Depot, pk=pk)
    old_name = depot.name
    form = DepotForm(request.POST or None, instance=depot)

    if request.method == "POST" and form.is_valid():
        depot = form.save()

        log_action(
            user=request.user,
            action="UPDATE",
            model="Depot",
            object_id=str(depot.pk),
            description=f"Updated depot: {old_name} → {depot.name}",
            ip_address=get_client_ip(request),
        )

        return redirect("management:depot-detail", pk=depot.pk)

    return render(request, "management/depots/form.html", {"form": form, "depot": depot})


@admin_required
@never_cache
def depot_delete(request, pk):
    depot = get_object_or_404(Depot, pk=pk)

    if request.method == "POST":
        name = depot.name
        d_pk = depot.pk
        depot.delete()

        log_action(
            user=request.user,
            action="DELETE",
            model="Depot",
            object_id=str(d_pk),
            description=f"Deleted depot: {name}",
            ip_address=get_client_ip(request),
        )

        return redirect("management:depot-list")

    return render(request, "management/depots/confirm_delete.html", {"depot": depot})
