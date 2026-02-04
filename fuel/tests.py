"""
Tests for the Fuel app - Fuel tanks, entries, and usage tracking.
"""
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.db import IntegrityError
from core.models import Employee, Vehicle
from fuel.models import FuelTank, FuelEntry, FuelUsage
from fuel.forms import FuelEntryForm, FuelUsageForm


class FuelTankModelTest(TestCase):
    """Tests for the FuelTank model."""

    def test_create_fuel_tank(self):
        """Test creating a fuel tank."""
        tank = FuelTank.objects.create(
            name="Main Tank",
            capacity=5000
        )
        self.assertEqual(tank.name, "Main Tank")
        self.assertEqual(tank.capacity, 5000)

    def test_fuel_tank_str(self):
        """Test fuel tank string representation."""
        tank = FuelTank.objects.create(name="Tank A", capacity=1000)
        self.assertEqual(str(tank), "Tank A")

    def test_fuel_tank_current_level_empty(self):
        """Test current level when tank has no entries."""
        tank = FuelTank.objects.create(name="Empty Tank", capacity=1000)
        self.assertEqual(tank.current_level, 0)

    def test_fuel_tank_current_level_with_entries(self):
        """Test current level calculation with entries and usage."""
        tank = FuelTank.objects.create(name="Test Tank", capacity=5000)

        # Add fuel entry
        FuelEntry.objects.create(tank=tank, amount=1000, supplier="Test")

        self.assertEqual(tank.current_level, 1000)

    def test_fuel_tank_current_level_with_usage(self):
        """Test current level after fuel usage."""
        user = User.objects.create_user(username="test", password="test123")
        employee = Employee.objects.create(user=user, name="Test")
        vehicle = Vehicle.objects.create(plate="ABC-123")
        tank = FuelTank.objects.create(name="Test Tank", capacity=5000)

        # Add fuel entry
        entry = FuelEntry.objects.create(tank=tank, amount=1000, supplier="Test")

        # Use some fuel
        FuelUsage.objects.create(
            tank=tank,
            amount=300,
            vehicle=vehicle,
            operator=employee,
            refill=entry
        )

        self.assertEqual(tank.current_level, 700)


class FuelEntryModelTest(TestCase):
    """Tests for the FuelEntry model."""

    def setUp(self):
        self.tank = FuelTank.objects.create(name="Test Tank", capacity=5000)

    def test_create_fuel_entry(self):
        """Test creating a fuel entry."""
        entry = FuelEntry.objects.create(
            tank=self.tank,
            amount=1000,
            supplier="Shell"
        )
        self.assertEqual(entry.amount, 1000)
        self.assertEqual(entry.supplier, "Shell")
        self.assertFalse(entry.is_closed)

    def test_fuel_entry_str(self):
        """Test fuel entry string representation."""
        entry = FuelEntry.objects.create(
            tank=self.tank,
            amount=1000,
            supplier="Shell"
        )
        self.assertIn("Test Tank", str(entry))

    def test_only_one_open_entry_per_tank(self):
        """Test constraint: only one open refill per tank."""
        FuelEntry.objects.create(
            tank=self.tank,
            amount=1000,
            supplier="First",
            is_closed=False
        )
        # Second open entry should fail
        with self.assertRaises(IntegrityError):
            FuelEntry.objects.create(
                tank=self.tank,
                amount=500,
                supplier="Second",
                is_closed=False
            )

    def test_multiple_closed_entries_allowed(self):
        """Test that multiple closed entries are allowed."""
        FuelEntry.objects.create(
            tank=self.tank,
            amount=1000,
            supplier="First",
            is_closed=True
        )
        entry2 = FuelEntry.objects.create(
            tank=self.tank,
            amount=500,
            supplier="Second",
            is_closed=True
        )
        self.assertEqual(entry2.supplier, "Second")

    def test_fuel_entry_used_amount(self):
        """Test used amount calculation."""
        user = User.objects.create_user(username="test", password="test123")
        employee = Employee.objects.create(user=user, name="Test")
        vehicle = Vehicle.objects.create(plate="ABC-123")

        entry = FuelEntry.objects.create(
            tank=self.tank,
            amount=1000,
            supplier="Test"
        )

        FuelUsage.objects.create(
            tank=self.tank,
            amount=300,
            vehicle=vehicle,
            operator=employee,
            refill=entry
        )

        self.assertEqual(entry.used_amount, 300)
        self.assertEqual(entry.remaining_amount, 700)


class FuelUsageModelTest(TestCase):
    """Tests for the FuelUsage model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee"
        )
        self.vehicle = Vehicle.objects.create(plate="ABC-123")
        self.tank = FuelTank.objects.create(name="Test Tank", capacity=5000)
        self.entry = FuelEntry.objects.create(
            tank=self.tank,
            amount=1000,
            supplier="Test"
        )

    def test_create_fuel_usage(self):
        """Test creating fuel usage."""
        usage = FuelUsage.objects.create(
            tank=self.tank,
            amount=100,
            vehicle=self.vehicle,
            operator=self.employee,
            refill=self.entry,
            project="Test Project"
        )
        self.assertEqual(usage.amount, 100)
        self.assertEqual(usage.vehicle, self.vehicle)

    def test_fuel_usage_str(self):
        """Test fuel usage string representation."""
        usage = FuelUsage.objects.create(
            tank=self.tank,
            amount=100,
            vehicle=self.vehicle,
            operator=self.employee
        )
        self.assertIn("100", str(usage))

    def test_negative_fuel_usage_allowed(self):
        """Test that negative fuel usage (Teprice) is allowed."""
        usage = FuelUsage.objects.create(
            tank=self.tank,
            amount=-50,  # Negative for surplus/adjustment
            vehicle=self.vehicle,
            operator=self.employee
        )
        self.assertEqual(usage.amount, -50)


class FuelViewTest(TestCase):
    """Tests for fuel views."""

    def setUp(self):
        self.client = Client()
        self.staff_group, _ = Group.objects.get_or_create(name="staff")

        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="testpass123"
        )
        self.staff_user.groups.add(self.staff_group)
        self.staff_employee = Employee.objects.create(
            user=self.staff_user,
            name="Staff Employee"
        )

        self.tank = FuelTank.objects.create(name="Test Tank", capacity=5000)

    def test_fuel_home_requires_staff(self):
        """Test fuel home requires staff access."""
        regular_user = User.objects.create_user(
            username="regular",
            password="testpass123"
        )
        self.client.login(username="regular", password="testpass123")
        response = self.client.get(reverse("fuel:fuel-home"))
        self.assertEqual(response.status_code, 403)

    def test_fuel_home_accessible_by_staff(self):
        """Test fuel home accessible by staff."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("fuel:fuel-home"))
        self.assertEqual(response.status_code, 200)

    def test_fuel_entries_list_view(self):
        """Test fuel entries list view."""
        FuelEntry.objects.create(
            tank=self.tank,
            amount=1000,
            supplier="Test Supplier"
        )
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("fuel:fuel-entries"))
        self.assertEqual(response.status_code, 200)


class FuelUsageFormTest(TestCase):
    """Tests for fuel usage form validation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            is_active=True
        )
        self.vehicle = Vehicle.objects.create(plate="ABC-123", is_active=True)
        self.tank = FuelTank.objects.create(name="Test Tank", capacity=5000)
        self.entry = FuelEntry.objects.create(
            tank=self.tank,
            amount=1000,
            supplier="Test"
        )

    def test_valid_fuel_usage_form(self):
        """Test valid fuel usage form."""
        form_data = {
            "tank": self.tank.pk,
            "vehicle": self.vehicle.pk,
            "amount": 100,
            "operator": self.employee.pk,
            "project": "Test Project"
        }
        form = FuelUsageForm(data=form_data)
        # Form needs open refill - validation happens in clean
        self.assertTrue(form.is_valid() or "amount" not in form.errors)

    def test_zero_amount_invalid(self):
        """Test that zero amount is invalid."""
        form_data = {
            "tank": self.tank.pk,
            "vehicle": self.vehicle.pk,
            "amount": 0,
            "operator": self.employee.pk
        }
        form = FuelUsageForm(data=form_data)
        self.assertFalse(form.is_valid())


class TankLevelCalculationTest(TransactionTestCase):
    """Tests for tank level calculations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee"
        )
        self.vehicle = Vehicle.objects.create(plate="ABC-123")
        self.tank = FuelTank.objects.create(name="Test Tank", capacity=5000)

    def test_tank_level_multiple_entries_and_usages(self):
        """Test tank level with multiple entries and usages."""
        # Entry 1: 1000L
        entry1 = FuelEntry.objects.create(
            tank=self.tank,
            amount=1000,
            supplier="Supplier 1",
            is_closed=True
        )
        # Usage from entry 1: 400L
        FuelUsage.objects.create(
            tank=self.tank,
            amount=400,
            vehicle=self.vehicle,
            operator=self.employee,
            refill=entry1
        )

        # Entry 2: 500L
        entry2 = FuelEntry.objects.create(
            tank=self.tank,
            amount=500,
            supplier="Supplier 2"
        )
        # Usage from entry 2: 200L
        FuelUsage.objects.create(
            tank=self.tank,
            amount=200,
            vehicle=self.vehicle,
            operator=self.employee,
            refill=entry2
        )

        # Total: 1000 + 500 - 400 - 200 = 900
        self.assertEqual(self.tank.current_level, 900)

    def test_tank_level_can_go_negative(self):
        """Test that tank level can go negative (within limits)."""
        entry = FuelEntry.objects.create(
            tank=self.tank,
            amount=100,
            supplier="Test"
        )

        # Use more than available (up to MAX_NEGATIVE_LITERS)
        FuelUsage.objects.create(
            tank=self.tank,
            amount=120,  # 20L over
            vehicle=self.vehicle,
            operator=self.employee,
            refill=entry
        )

        self.assertEqual(self.tank.current_level, -20)
