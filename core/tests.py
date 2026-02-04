"""
Tests for the Core app - Employee and Vehicle models.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from core.models import Employee, Vehicle
from datetime import date, timedelta


class EmployeeModelTest(TestCase):
    """Tests for the Employee model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

    def test_create_employee(self):
        """Test creating an employee."""
        employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            position="Developer",
            phone="123456789",
            have_budget=True,
            is_active=True
        )
        self.assertEqual(employee.name, "Test Employee")
        self.assertEqual(employee.user, self.user)
        self.assertTrue(employee.have_budget)
        self.assertTrue(employee.is_active)

    def test_employee_str(self):
        """Test employee string representation."""
        employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            position="Developer"
        )
        self.assertEqual(str(employee), "Test Employee")

    def test_employee_user_relationship(self):
        """Test one-to-one relationship with User."""
        employee = Employee.objects.create(
            user=self.user,
            name="Test Employee"
        )
        self.assertEqual(self.user.employee, employee)

    def test_employee_default_values(self):
        """Test default values for employee fields."""
        employee = Employee.objects.create(
            user=self.user,
            name="Test Employee"
        )
        self.assertFalse(employee.have_budget)
        self.assertTrue(employee.is_active)


class VehicleModelTest(TestCase):
    """Tests for the Vehicle model."""

    def test_create_vehicle(self):
        """Test creating a vehicle."""
        vehicle = Vehicle.objects.create(
            plate="ABC-123",
            chassis="VIN123456789",
            description="Test Vehicle"
        )
        self.assertEqual(vehicle.plate, "ABC-123")
        self.assertEqual(vehicle.chassis, "VIN123456789")
        self.assertTrue(vehicle.is_active)

    def test_vehicle_str(self):
        """Test vehicle string representation."""
        vehicle = Vehicle.objects.create(
            plate="ABC-123",
            description="Test Vehicle"
        )
        self.assertEqual(str(vehicle), "ABC-123")

    def test_vehicle_unique_plate(self):
        """Test that plate must be unique."""
        Vehicle.objects.create(plate="ABC-123")
        with self.assertRaises(Exception):
            Vehicle.objects.create(plate="ABC-123")

    def test_vehicle_date_fields(self):
        """Test vehicle date fields."""
        future_date = date.today() + timedelta(days=365)
        vehicle = Vehicle.objects.create(
            plate="ABC-123",
            insurance=future_date,
            yearly_taxes=future_date,
            periodic_inspection=future_date
        )
        self.assertEqual(vehicle.insurance, future_date)
        self.assertEqual(vehicle.yearly_taxes, future_date)


class HomeViewTest(TestCase):
    """Tests for the home page view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

    def test_home_requires_login(self):
        """Test that home page requires authentication."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 302)

    def test_home_accessible_when_logged_in(self):
        """Test home page is accessible when logged in."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)


class ErrorHandlersTest(TestCase):
    """Tests for custom error handlers."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

    def test_404_handler(self):
        """Test 404 error handler."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/nonexistent-page/")
        self.assertEqual(response.status_code, 404)
