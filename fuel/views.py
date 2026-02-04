from collections import defaultdict, OrderedDict
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Prefetch

from audit.utils import log_action
from audit.middleware import get_client_ip
from management.permissions import staff_required

from .models import FuelTank, FuelUsage, FuelEntry
from core.models import Vehicle, Employee
from .forms import FuelEntryForm, FuelUsageForm


@staff_required
def fuel_home(request):
    # Prefetch open refills in a single query
    open_refills_prefetch = Prefetch(
        "entries",
        queryset=FuelEntry.objects.filter(is_closed=False).order_by("-date", "-id"),
        to_attr="open_refills"
    )
    tanks = FuelTank.objects.prefetch_related(open_refills_prefetch).all()
    usages = FuelUsage.objects.order_by("-date")

    # Attach open_refill from prefetched data
    for tank in tanks:
        tank.open_refill = tank.open_refills[0] if tank.open_refills else None

    return render(request, "fuel/fuel-home.html", {
        "tanks": tanks,
        "usages": usages,
    })


@staff_required
@never_cache
def add_entry(request):
    form = FuelEntryForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        entry = form.save()

        log_action(
            user=request.user,
            action="CREATE",
            model="FuelEntry",
            object_id=str(entry.pk),
            description=(
                f"Fuel refill added: {entry.amount}L to tank {entry.tank} "
                f"(Supplier: {getattr(entry, 'supplier', None) or 'N/A'})"
            ),
            ip_address=get_client_ip(request),
        )

        return redirect("fuel:fuel-home")

    return render(request, "fuel/form.html", {
    "form": form,
    "page_title": "Furnizim i Depozitës"
})


@staff_required
def existing_refill_dates(request, tank_id):
    dates = list(
        FuelEntry.objects.filter(
            tank_id=tank_id).values_list("date", flat=True)
    )
    return JsonResponse({"dates": dates})


@staff_required
@never_cache
@transaction.atomic
def add_usage(request):
    form = FuelUsageForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        usage = form.save(commit=False)

        # Lock the tank's entries to prevent race conditions
        open_refill = (
            FuelEntry.objects
            .select_for_update()
            .filter(tank=usage.tank, is_closed=False)
            .order_by("-date", "-id")
            .first()
        )

        if not open_refill:
            return render(request, "fuel/form.html", {
                "form": form,
                "page_title": "Dalje Karburanti",
                "error": "Nuk ka refill aktiv (OPEN) për këtë depo."
            })

        # Re-check tank level inside transaction to prevent overdraw race condition
        entries_total = FuelEntry.objects.filter(tank=usage.tank).aggregate(
            total=Sum("amount"))["total"] or 0
        usage_total = FuelUsage.objects.filter(tank=usage.tank).aggregate(
            total=Sum("amount"))["total"] or 0
        tank_level = entries_total - usage_total
        projected_level = tank_level - usage.amount

        if projected_level < -FuelUsageForm.MAX_NEGATIVE_LITERS:
            return render(request, "fuel/form.html", {
                "form": form,
                "page_title": "Dalje Karburanti",
                "error": f"Depozita do shkojë në {projected_level} L. Limiti: -{FuelUsageForm.MAX_NEGATIVE_LITERS} L."
            })

        usage.refill = open_refill
        usage.save()

        log_action(
            user=request.user,
            action="CREATE",
            model="FuelUsage",
            object_id=str(usage.pk),
            description=(
                f"Fuel usage: {usage.amount}L from tank {usage.tank} "
                f"for vehicle {usage.vehicle} (refill #{open_refill.id})"
            ),
            ip_address=get_client_ip(request),
        )

        return redirect("fuel:fuel-home")

    return render(request, "fuel/form.html", {
    "form": form,
    "page_title": "Dalje Karburanti"
})


@staff_required
@transaction.atomic
def close_refill(request, id):
    entry = get_object_or_404(FuelEntry.objects.select_for_update(), id=id)

    if request.method != "POST":
        return redirect("fuel:fuel-home")

    if entry.is_closed:
        return redirect("fuel:fuel-home")

    tank = entry.tank

    # ✅ Make tank go to 0 => consume all current_level as "Teprica"
    entries = FuelEntry.objects.filter(tank=tank).aggregate(total=Sum("amount"))["total"] or 0
    usage = FuelUsage.objects.filter(tank=tank).aggregate(total=Sum("amount"))["total"] or 0
    teprica_amount = entries - usage

    if teprica_amount != 0:
        # ✅ operator: try SYSTEM first, else fallback to first employee
        operator = Employee.objects.filter(name__iexact="SYSTEM").first()
        if operator is None:
            operator = Employee.objects.order_by("id").first()

        # ✅ vehicle: try TEPRICA plate first, else fallback to first vehicle
        teprica_vehicle = Vehicle.objects.filter(
            plate__iexact="DIFERENCE").first()
        if teprica_vehicle is None:
            teprica_vehicle = Vehicle.objects.order_by("id").first()

        # If you have NO employees or vehicles, stop with a friendly error
        if operator is None:
            messages.error(request, "Nuk mund të mbyllet furnizimi: mungon punonjësi 'SYSTEM'.")
            return redirect("fuel:fuel-home")
        if teprica_vehicle is None:
            messages.error(request, "Nuk mund të mbyllet furnizimi: mungon mjeti 'DIFERENCE'.")
            return redirect("fuel:fuel-home")

        FuelUsage.objects.create(
            tank=tank,
            date=timezone.now().date(),
            amount=teprica_amount,        # ✅ may be negative
            vehicle=teprica_vehicle,
            refill=entry,
            project = "Teprice" if teprica_amount < 0 else "Mungese",
            operator=operator,
        )

    # ✅ Close refill
    entry.is_closed = True
    entry.closed_at = timezone.now()
    entry.save(update_fields=["is_closed", "closed_at"])

    log_action(
        user=request.user,
        action="UPDATE",
        model="FuelEntry",
        object_id=str(entry.pk),
        description=(
            f"Fuel refill CLOSED: entry #{entry.id} ({entry.amount}L) tank {entry.tank}. "
            f"Teprica usage created: {teprica_amount}L."
        ),
        ip_address=get_client_ip(request),
    )

    return redirect("fuel:fuel-home")


@staff_required
def vehicle_usage(request):
    vehicles = Vehicle.objects.order_by("-is_active", "plate")
    selected_vehicle = request.GET.get("vehicle")

    usage_groups = OrderedDict()
    selected_vehicle_obj = None

    if selected_vehicle:
        selected_vehicle_obj = get_object_or_404(Vehicle, id=selected_vehicle)

        # ✅ load usages + refill info
        usages = (
            FuelUsage.objects
            .filter(vehicle=selected_vehicle_obj)
            .select_related("refill", "operator")
            .order_by("-refill__date", "-refill__id", "-date", "-id")
        )

        for u in usages:
            refill = u.refill  # FuelEntry or None

            # Optional: group old rows that have no refill
            if refill is None:
                key = "NO_REFILL"
                if key not in usage_groups:
                    usage_groups[key] = {"usages": [], "total": 0}
                usage_groups[key]["usages"].append(u)
                usage_groups[key]["total"] += u.amount
                continue

            if refill not in usage_groups:
                usage_groups[refill] = {"usages": [], "total": 0}

            usage_groups[refill]["usages"].append(u)
            usage_groups[refill]["total"] += u.amount

    return render(request, "fuel/vehicle_usage.html", {
        "vehicles": vehicles,
        "selected_vehicle": int(selected_vehicle) if selected_vehicle else None,
        "selected_vehicle_obj": selected_vehicle_obj,
        "usage_groups": usage_groups,
    })


@staff_required
def fuel_entries_list(request):
    entries = FuelEntry.objects.select_related("tank").order_by("-date", "-id")
    return render(request, "fuel/fuel_entries_list.html", {"entries": entries})


@staff_required
def fuel_entry_detail(request, id):
    entry = get_object_or_404(FuelEntry, id=id)

    usages = FuelUsage.objects.filter(refill=entry).select_related(
        "vehicle").order_by("-date", "-id")

    vehicle_report = defaultdict(lambda: {"total": 0, "count": 0})
    for u in usages:
        vehicle_report[u.vehicle]["total"] += u.amount
        vehicle_report[u.vehicle]["count"] += 1

    vehicle_report_list = list(vehicle_report.items())

    return render(request, "fuel/fuel_entry_detail.html", {
        "entry": entry,
        "usages": usages,
        "vehicle_report": vehicle_report_list,
    })
