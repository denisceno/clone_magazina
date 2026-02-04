"""
Tests for the Audit app - Action logging and compliance.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from audit.models import AuditLog
from audit.utils import log_action


class AuditLogModelTest(TestCase):
    """Tests for the AuditLog model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

    def test_create_audit_log(self):
        """Test creating an audit log entry."""
        log = AuditLog.objects.create(
            user=self.user,
            action="CREATE",
            model="Product",
            object_id=1,
            description="Created product: Test Product",
            ip_address="127.0.0.1"
        )
        self.assertEqual(log.action, "CREATE")
        self.assertEqual(log.model, "Product")

    def test_audit_log_str(self):
        """Test audit log string representation."""
        log = AuditLog.objects.create(
            user=self.user,
            action="UPDATE",
            model="Employee",
            object_id=1,
            description="Updated employee"
        )
        result = str(log)
        self.assertIn("UPDATE", result)

    def test_audit_log_actions(self):
        """Test various audit log actions."""
        actions = [
            "CREATE", "UPDATE", "DELETE", "ADD",
            "WITHDRAW", "RETURN", "EXPORT", "LOGIN", "LOGOUT"
        ]
        for action in actions:
            log = AuditLog.objects.create(
                user=self.user,
                action=action,
                model="Test",
                description=f"Test {action}"
            )
            self.assertEqual(log.action, action)

    def test_audit_log_timestamp_auto(self):
        """Test that timestamp is automatically set."""
        log = AuditLog.objects.create(
            user=self.user,
            action="CREATE",
            model="Test",
            description="Test"
        )
        self.assertIsNotNone(log.timestamp)

    def test_audit_log_without_user(self):
        """Test audit log can be created without user (system actions)."""
        log = AuditLog.objects.create(
            user=None,
            action="CREATE",
            model="System",
            description="System action"
        )
        self.assertIsNone(log.user)


class LogActionUtilityTest(TestCase):
    """Tests for the log_action utility function."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

    def test_log_action_creates_entry(self):
        """Test that log_action creates an audit log entry."""
        initial_count = AuditLog.objects.count()

        log_action(
            user=self.user,
            action="CREATE",
            model="Product",
            object_id=1,
            description="Created product",
            ip_address="192.168.1.1"
        )

        self.assertEqual(AuditLog.objects.count(), initial_count + 1)

    def test_log_action_stores_correct_data(self):
        """Test that log_action stores correct data."""
        log_action(
            user=self.user,
            action="UPDATE",
            model="Employee",
            object_id=42,
            description="Updated employee details",
            ip_address="10.0.0.1"
        )

        log = AuditLog.objects.latest("timestamp")
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, "UPDATE")
        self.assertEqual(log.model, "Employee")
        self.assertEqual(str(log.object_id), "42")
        self.assertEqual(log.ip_address, "10.0.0.1")

    def test_log_action_without_object_id(self):
        """Test log_action without object_id."""
        log_action(
            user=self.user,
            action="EXPORT",
            model="Report",
            description="Exported report"
        )

        log = AuditLog.objects.latest("timestamp")
        self.assertIsNone(log.object_id)


class AuditDashboardViewTest(TestCase):
    """Tests for the audit dashboard view."""

    def setUp(self):
        self.client = Client()

        # Regular user
        self.regular_user = User.objects.create_user(
            username="regular",
            password="testpass123"
        )

        # Staff user
        self.staff_group, _ = Group.objects.get_or_create(name="staff")
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

        # Create some audit logs
        for i in range(5):
            AuditLog.objects.create(
                user=self.superuser,
                action="CREATE",
                model="Product",
                object_id=i,
                description=f"Created product {i}"
            )

    def test_audit_dashboard_requires_admin(self):
        """Test audit dashboard requires admin access."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("audit:audit-dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_audit_dashboard_accessible_by_superuser(self):
        """Test audit dashboard accessible by superuser."""
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("audit:audit-dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_audit_dashboard_shows_logs(self):
        """Test audit dashboard displays log entries."""
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("audit:audit-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CREATE")

    def test_audit_dashboard_filter_by_action(self):
        """Test filtering audit logs by action."""
        # Create a different action log
        AuditLog.objects.create(
            user=self.superuser,
            action="DELETE",
            model="Product",
            description="Deleted product"
        )

        self.client.login(username="admin", password="testpass123")
        response = self.client.get(
            reverse("audit:audit-dashboard") + "?action=DELETE"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DELETE")

    def test_audit_dashboard_filter_by_model(self):
        """Test filtering audit logs by model."""
        AuditLog.objects.create(
            user=self.superuser,
            action="CREATE",
            model="Employee",
            description="Created employee"
        )

        self.client.login(username="admin", password="testpass123")
        response = self.client.get(
            reverse("audit:audit-dashboard") + "?model=Employee"
        )
        self.assertEqual(response.status_code, 200)


class AuditLogIntegrationTest(TestCase):
    """Integration tests for audit logging throughout the app."""

    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username="admin",
            password="testpass123"
        )

    def test_login_creates_audit_log(self):
        """Test that login creates an audit log entry."""
        initial_count = AuditLog.objects.filter(action="LOGIN").count()

        self.client.post(reverse("accounts:login"), {
            "username": "admin",
            "password": "testpass123"
        })

        # Login signal should create audit log
        final_count = AuditLog.objects.filter(action="LOGIN").count()
        self.assertEqual(final_count, initial_count + 1)

    def test_logout_creates_audit_log(self):
        """Test that logout creates an audit log entry."""
        self.client.login(username="admin", password="testpass123")
        initial_count = AuditLog.objects.filter(action="LOGOUT").count()

        self.client.post(reverse("accounts:logout"))

        final_count = AuditLog.objects.filter(action="LOGOUT").count()
        self.assertEqual(final_count, initial_count + 1)


class AuditLogQueryTest(TestCase):
    """Tests for querying audit logs."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            password="test123"
        )
        self.user2 = User.objects.create_user(
            username="user2",
            password="test123"
        )

        # Create logs for user1
        for i in range(3):
            AuditLog.objects.create(
                user=self.user1,
                action="CREATE",
                model="Product",
                description=f"User1 action {i}"
            )

        # Create logs for user2
        for i in range(2):
            AuditLog.objects.create(
                user=self.user2,
                action="UPDATE",
                model="Employee",
                description=f"User2 action {i}"
            )

    def test_filter_by_user(self):
        """Test filtering logs by user."""
        user1_logs = AuditLog.objects.filter(user=self.user1)
        self.assertEqual(user1_logs.count(), 3)

    def test_filter_by_action(self):
        """Test filtering logs by action."""
        create_logs = AuditLog.objects.filter(action="CREATE")
        self.assertEqual(create_logs.count(), 3)

    def test_filter_by_model(self):
        """Test filtering logs by model."""
        product_logs = AuditLog.objects.filter(model="Product")
        self.assertEqual(product_logs.count(), 3)

    def test_ordering_by_timestamp(self):
        """Test logs are ordered by timestamp."""
        logs = AuditLog.objects.all().order_by("-timestamp")
        # Most recent should be first
        self.assertTrue(logs[0].timestamp >= logs[1].timestamp)
