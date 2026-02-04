"""
Tests for the Accounts app - Authentication and Authorization.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from core.models import Employee


class AuthenticationTest(TestCase):
    """Tests for login/logout functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")

    def test_login_page_accessible(self):
        """Test login page is accessible without authentication."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_successful_login(self):
        """Test successful login redirects to home."""
        response = self.client.post(self.login_url, {
            "username": "testuser",
            "password": "testpass123"
        })
        self.assertEqual(response.status_code, 302)

    def test_failed_login(self):
        """Test failed login shows error."""
        response = self.client.post(self.login_url, {
            "username": "testuser",
            "password": "wrongpassword"
        })
        self.assertEqual(response.status_code, 200)  # Stays on login page

    def test_logout(self):
        """Test logout redirects to login."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_redirected_from_login(self):
        """Test that authenticated users are redirected from login page."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)


class GroupsTest(TestCase):
    """Tests for user groups creation."""

    def test_employee_group_exists(self):
        """Test that employee group is created by signals."""
        Group.objects.get_or_create(name="employee")
        self.assertTrue(Group.objects.filter(name="employee").exists())

    def test_staff_group_exists(self):
        """Test that staff group is created by signals."""
        Group.objects.get_or_create(name="staff")
        self.assertTrue(Group.objects.filter(name="staff").exists())


class StaffRequiredDecoratorTest(TestCase):
    """Tests for staff_required decorator."""

    def setUp(self):
        self.client = Client()
        self.staff_group, _ = Group.objects.get_or_create(name="staff")
        self.employee_group, _ = Group.objects.get_or_create(name="employee")

        # Regular user (no groups)
        self.regular_user = User.objects.create_user(
            username="regular",
            password="testpass123"
        )

        # Staff user
        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="testpass123"
        )
        self.staff_user.groups.add(self.staff_group)

        # Superuser
        self.superuser = User.objects.create_superuser(
            username="admin",
            password="testpass123"
        )

    def test_superuser_can_access_staff_views(self):
        """Test that superuser can access staff-protected views."""
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("inventory:inventory-home"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_staff_views(self):
        """Test that staff group members can access staff views."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("inventory:inventory-home"))
        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_access_staff_views(self):
        """Test that regular users cannot access staff-protected views."""
        self.client.login(username="regular", password="testpass123")
        response = self.client.get(reverse("inventory:inventory-home"))
        self.assertEqual(response.status_code, 403)


class AdminRequiredDecoratorTest(TestCase):
    """Tests for admin_required decorator."""

    def setUp(self):
        self.client = Client()
        self.staff_group, _ = Group.objects.get_or_create(name="staff")

        # Staff user (not superuser)
        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="testpass123"
        )
        self.staff_user.groups.add(self.staff_group)

        # Superuser
        self.superuser = User.objects.create_superuser(
            username="admin",
            password="testpass123"
        )

    def test_superuser_can_access_admin_views(self):
        """Test that superuser can access admin-protected views."""
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("management:employee-list"))
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_access_admin_views(self):
        """Test that staff cannot access admin-only views."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("management:employee-list"))
        self.assertEqual(response.status_code, 403)


class LoginRequiredMiddlewareTest(TestCase):
    """Tests for LoginRequiredMiddleware."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

    def test_unauthenticated_redirect_to_login(self):
        """Test unauthenticated users are redirected to login."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_login_page_accessible_without_auth(self):
        """Test login page doesn't require authentication."""
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
