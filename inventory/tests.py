"""
Tests for the Inventory app - Products, Withdrawals, Returns.
"""
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from core.models import Employee
from inventory.models import (
    Depot, Product, WithdrawalHeader, WithdrawalItem,
    ReturnHeader, ReturnItem
)
from inventory.forms import ProductForm, AddQuantityForm


class DepotModelTest(TestCase):
    """Tests for the Depot model."""

    def test_create_depot(self):
        """Test creating a depot."""
        depot = Depot.objects.create(
            name="Main Warehouse",
            description="Primary storage"
        )
        self.assertEqual(depot.name, "Main Warehouse")
        self.assertTrue(depot.is_active)

    def test_depot_str(self):
        """Test depot string representation."""
        depot = Depot.objects.create(name="Warehouse A")
        self.assertEqual(str(depot), "Warehouse A")

    def test_depot_unique_name(self):
        """Test depot name must be unique."""
        Depot.objects.create(name="Warehouse")
        with self.assertRaises(Exception):
            Depot.objects.create(name="Warehouse")


class ProductModelTest(TestCase):
    """Tests for the Product model."""

    def setUp(self):
        self.depot = Depot.objects.create(name="Test Depot")

    def test_create_product(self):
        """Test creating a product."""
        product = Product.objects.create(
            depot=self.depot,
            name="Test Product",
            quantity=100,
            price=50,
            unit="pcs",
            item_type="consumable"
        )
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.quantity, 100)

    def test_product_str(self):
        """Test product string representation."""
        product = Product.objects.create(
            depot=self.depot,
            name="Hammer",
            quantity=10,
            unit="pcs",
            item_type="consumable"
        )
        self.assertIn("Hammer", str(product))

    def test_product_unique_per_depot(self):
        """Test product name must be unique per depot."""
        Product.objects.create(
            depot=self.depot,
            name="Screwdriver",
            quantity=5,
            unit="pcs",
            item_type="consumable"
        )
        with self.assertRaises(Exception):
            Product.objects.create(
                depot=self.depot,
                name="Screwdriver",
                quantity=10,
                unit="pcs",
                item_type="consumable"
            )

    def test_same_product_name_different_depots(self):
        """Test same product name allowed in different depots."""
        depot2 = Depot.objects.create(name="Second Depot")
        Product.objects.create(
            depot=self.depot,
            name="Wrench",
            quantity=5,
            unit="pcs",
            item_type="consumable"
        )
        product2 = Product.objects.create(
            depot=depot2,
            name="Wrench",
            quantity=10,
            unit="pcs",
            item_type="consumable"
        )
        self.assertEqual(product2.name, "Wrench")

    def test_product_item_types(self):
        """Test product item types."""
        returnable = Product.objects.create(
            depot=self.depot,
            name="Drill",
            quantity=5,
            unit="pcs",
            item_type="returnable"
        )
        consumable = Product.objects.create(
            depot=self.depot,
            name="Nails",
            quantity=100,
            unit="pcs",
            item_type="consumable"
        )
        self.assertEqual(returnable.item_type, "returnable")
        self.assertEqual(consumable.item_type, "consumable")


class WithdrawalModelTest(TestCase):
    """Tests for Withdrawal models."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee"
        )
        self.depot = Depot.objects.create(name="Test Depot")
        self.product = Product.objects.create(
            depot=self.depot,
            name="Test Product",
            quantity=100,
            item_type="returnable"
        )

    def test_create_withdrawal(self):
        """Test creating a withdrawal."""
        header = WithdrawalHeader.objects.create(
            employee=self.employee,
            notes="Test withdrawal"
        )
        item = WithdrawalItem.objects.create(
            header=header,
            product=self.product,
            quantity=10
        )
        self.assertEqual(item.quantity, 10)
        self.assertEqual(item.header.employee, self.employee)

    def test_withdrawal_item_outstanding_qty(self):
        """Test outstanding quantity calculation."""
        header = WithdrawalHeader.objects.create(employee=self.employee)
        item = WithdrawalItem.objects.create(
            header=header,
            product=self.product,
            quantity=10
        )
        # No returns yet - outstanding should equal withdrawn
        self.assertEqual(item.outstanding_qty, 10)

    def test_withdrawal_item_returned_qty(self):
        """Test returned quantity calculation."""
        header = WithdrawalHeader.objects.create(employee=self.employee)
        item = WithdrawalItem.objects.create(
            header=header,
            product=self.product,
            quantity=10
        )
        # Create a return
        return_header = ReturnHeader.objects.create(employee=self.employee)
        ReturnItem.objects.create(
            header=return_header,
            withdrawal_item=item,
            quantity=3
        )
        self.assertEqual(item.returned_qty, 3)
        self.assertEqual(item.outstanding_qty, 7)


class ReturnModelTest(TestCase):
    """Tests for Return models."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee"
        )
        self.depot = Depot.objects.create(name="Test Depot")
        self.product = Product.objects.create(
            depot=self.depot,
            name="Test Product",
            quantity=100,
            item_type="returnable"
        )
        # Create withdrawal first
        self.withdrawal_header = WithdrawalHeader.objects.create(
            employee=self.employee
        )
        self.withdrawal_item = WithdrawalItem.objects.create(
            header=self.withdrawal_header,
            product=self.product,
            quantity=10
        )

    def test_create_return(self):
        """Test creating a return."""
        return_header = ReturnHeader.objects.create(employee=self.employee)
        return_item = ReturnItem.objects.create(
            header=return_header,
            withdrawal_item=self.withdrawal_item,
            quantity=5
        )
        self.assertEqual(return_item.quantity, 5)

    def test_multiple_partial_returns(self):
        """Test multiple partial returns."""
        return_header1 = ReturnHeader.objects.create(employee=self.employee)
        ReturnItem.objects.create(
            header=return_header1,
            withdrawal_item=self.withdrawal_item,
            quantity=3
        )

        return_header2 = ReturnHeader.objects.create(employee=self.employee)
        ReturnItem.objects.create(
            header=return_header2,
            withdrawal_item=self.withdrawal_item,
            quantity=4
        )

        self.assertEqual(self.withdrawal_item.returned_qty, 7)
        self.assertEqual(self.withdrawal_item.outstanding_qty, 3)


class InventoryViewTest(TestCase):
    """Tests for inventory views."""

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

        self.depot = Depot.objects.create(name="Test Depot")
        self.product = Product.objects.create(
            depot=self.depot,
            name="Test Product",
            quantity=100
        )

    def test_inventory_home_requires_staff(self):
        """Test inventory home requires staff access."""
        regular_user = User.objects.create_user(
            username="regular",
            password="testpass123"
        )
        self.client.login(username="regular", password="testpass123")
        response = self.client.get(reverse("inventory:inventory-home"))
        self.assertEqual(response.status_code, 403)

    def test_inventory_home_accessible_by_staff(self):
        """Test inventory home accessible by staff."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("inventory:inventory-home"))
        self.assertEqual(response.status_code, 200)

    def test_depot_detail_shows_products(self):
        """Test depot detail view shows products."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("inventory:depot-detail", args=[self.depot.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")

    def test_product_detail_view(self):
        """Test product detail view."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("inventory:product-detail", args=[self.product.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_all_products_view(self):
        """Test all products view."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("inventory:all-products"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")

    def test_all_products_search(self):
        """Test product search functionality."""
        Product.objects.create(
            depot=self.depot,
            name="Hammer",
            quantity=50,
            unit="pcs",
            item_type="consumable"
        )
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("inventory:all-products") + "?q=Hammer"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hammer")


class StockManagementTest(TransactionTestCase):
    """Tests for stock management business logic."""

    def setUp(self):
        self.staff_group, _ = Group.objects.get_or_create(name="staff")
        self.user = User.objects.create_user(
            username="staffuser",
            password="testpass123"
        )
        self.user.groups.add(self.staff_group)
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            is_active=True
        )
        self.depot = Depot.objects.create(name="Test Depot")
        self.product = Product.objects.create(
            depot=self.depot,
            name="Test Product",
            quantity=100,
            item_type="returnable"
        )

    def test_withdrawal_reduces_stock(self):
        """Test that withdrawal reduces product stock."""
        initial_qty = self.product.quantity
        withdrawal_qty = 10

        header = WithdrawalHeader.objects.create(employee=self.employee)
        WithdrawalItem.objects.create(
            header=header,
            product=self.product,
            quantity=withdrawal_qty
        )
        # Simulate what view does
        self.product.quantity -= withdrawal_qty
        self.product.save()

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, initial_qty - withdrawal_qty)

    def test_return_increases_stock(self):
        """Test that return increases product stock."""
        # First create withdrawal
        header = WithdrawalHeader.objects.create(employee=self.employee)
        item = WithdrawalItem.objects.create(
            header=header,
            product=self.product,
            quantity=10
        )
        self.product.quantity -= 10
        self.product.save()

        # Now return
        return_qty = 5
        return_header = ReturnHeader.objects.create(employee=self.employee)
        ReturnItem.objects.create(
            header=return_header,
            withdrawal_item=item,
            quantity=return_qty
        )
        self.product.quantity += return_qty
        self.product.save()

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 95)  # 100 - 10 + 5

    def test_outstanding_quantity_tracking(self):
        """Test outstanding quantity is properly tracked."""
        header = WithdrawalHeader.objects.create(employee=self.employee)
        item = WithdrawalItem.objects.create(
            header=header,
            product=self.product,
            quantity=10
        )

        self.assertEqual(item.outstanding_qty, 10)

        # Partial return
        return_header = ReturnHeader.objects.create(employee=self.employee)
        ReturnItem.objects.create(
            header=return_header,
            withdrawal_item=item,
            quantity=3
        )

        self.assertEqual(item.outstanding_qty, 7)

        # Full return of remaining
        return_header2 = ReturnHeader.objects.create(employee=self.employee)
        ReturnItem.objects.create(
            header=return_header2,
            withdrawal_item=item,
            quantity=7
        )

        self.assertEqual(item.outstanding_qty, 0)


class AddQuantityFormTest(TestCase):
    """Tests for add quantity form."""

    def test_valid_quantity(self):
        """Test valid quantity."""
        form = AddQuantityForm(data={"quantity": 50})
        self.assertTrue(form.is_valid())

    def test_zero_quantity_invalid(self):
        """Test zero quantity is invalid."""
        form = AddQuantityForm(data={"quantity": 0})
        self.assertFalse(form.is_valid())

    def test_negative_quantity_invalid(self):
        """Test negative quantity is invalid."""
        form = AddQuantityForm(data={"quantity": -10})
        self.assertFalse(form.is_valid())
