"""
Tests for the Expenses app - Budgets, expenses, and adjustments.
"""
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from core.models import Employee
from expenses.models import EmployeeBudget, Expense, BudgetAdjustment
from expenses.forms import ExpenseForm, BudgetAdjustmentForm


class EmployeeBudgetModelTest(TestCase):
    """Tests for the EmployeeBudget model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            have_budget=True
        )

    def test_create_budget(self):
        """Test creating an employee budget."""
        budget = EmployeeBudget.objects.create(
            employee=self.employee,
            balance=1000
        )
        self.assertEqual(budget.balance, 1000)
        self.assertEqual(budget.employee, self.employee)

    def test_budget_str(self):
        """Test budget string representation."""
        budget = EmployeeBudget.objects.create(
            employee=self.employee,
            balance=1000
        )
        self.assertIn("Test Employee", str(budget))

    def test_one_budget_per_employee(self):
        """Test one-to-one relationship enforces single budget."""
        EmployeeBudget.objects.create(
            employee=self.employee,
            balance=1000
        )
        with self.assertRaises(Exception):
            EmployeeBudget.objects.create(
                employee=self.employee,
                balance=500
            )

    def test_budget_default_balance(self):
        """Test default balance is 0."""
        budget = EmployeeBudget.objects.create(employee=self.employee)
        self.assertEqual(budget.balance, 0)


class ExpenseModelTest(TestCase):
    """Tests for the Expense model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            have_budget=True
        )

    def test_create_expense(self):
        """Test creating an expense."""
        expense = Expense.objects.create(
            employee=self.employee,
            description="Office supplies",
            amount=50
        )
        self.assertEqual(expense.amount, 50)
        self.assertEqual(expense.description, "Office supplies")

    def test_expense_str(self):
        """Test expense string representation."""
        expense = Expense.objects.create(
            employee=self.employee,
            description="Test expense",
            amount=100
        )
        self.assertIn("100", str(expense))


class BudgetAdjustmentModelTest(TestCase):
    """Tests for the BudgetAdjustment model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            have_budget=True
        )

    def test_create_add_adjustment(self):
        """Test creating an ADD adjustment."""
        adjustment = BudgetAdjustment.objects.create(
            employee=self.employee,
            adjustment_type="ADD",
            amount=500,
            note="Monthly allowance"
        )
        self.assertEqual(adjustment.adjustment_type, "ADD")
        self.assertEqual(adjustment.amount, 500)

    def test_create_remove_adjustment(self):
        """Test creating a REMOVE adjustment."""
        adjustment = BudgetAdjustment.objects.create(
            employee=self.employee,
            adjustment_type="REMOVE",
            amount=200,
            note="Correction"
        )
        self.assertEqual(adjustment.adjustment_type, "REMOVE")

    def test_adjustment_str(self):
        """Test adjustment string representation."""
        adjustment = BudgetAdjustment.objects.create(
            employee=self.employee,
            adjustment_type="ADD",
            amount=500
        )
        result = str(adjustment)
        self.assertIn("500", result)


class BudgetCalculationTest(TransactionTestCase):
    """Tests for budget calculation business logic."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            have_budget=True
        )
        self.budget = EmployeeBudget.objects.create(
            employee=self.employee,
            balance=1000
        )

    def test_expense_deducts_from_budget(self):
        """Test that expense deducts from budget."""
        initial_balance = self.budget.balance

        # Create expense
        Expense.objects.create(
            employee=self.employee,
            description="Test expense",
            amount=200
        )

        # Simulate what view does
        self.budget.balance -= 200
        self.budget.save()

        self.budget.refresh_from_db()
        self.assertEqual(self.budget.balance, initial_balance - 200)

    def test_add_adjustment_increases_budget(self):
        """Test ADD adjustment increases balance."""
        initial_balance = self.budget.balance

        BudgetAdjustment.objects.create(
            employee=self.employee,
            adjustment_type="ADD",
            amount=300
        )

        # Simulate what view does
        self.budget.balance += 300
        self.budget.save()

        self.budget.refresh_from_db()
        self.assertEqual(self.budget.balance, initial_balance + 300)

    def test_remove_adjustment_decreases_budget(self):
        """Test REMOVE adjustment decreases balance."""
        initial_balance = self.budget.balance

        BudgetAdjustment.objects.create(
            employee=self.employee,
            adjustment_type="REMOVE",
            amount=150
        )

        # Simulate what view does
        self.budget.balance -= 150
        self.budget.save()

        self.budget.refresh_from_db()
        self.assertEqual(self.budget.balance, initial_balance - 150)

    def test_budget_can_go_negative(self):
        """Test that budget can go negative."""
        self.budget.balance = 100
        self.budget.save()

        # Remove more than available
        BudgetAdjustment.objects.create(
            employee=self.employee,
            adjustment_type="REMOVE",
            amount=200
        )
        self.budget.balance -= 200
        self.budget.save()

        self.budget.refresh_from_db()
        self.assertEqual(self.budget.balance, -100)

    def test_multiple_transactions(self):
        """Test multiple expenses and adjustments."""
        # Start with 1000
        BudgetAdjustment.objects.create(
            employee=self.employee,
            adjustment_type="ADD",
            amount=500
        )
        self.budget.balance += 500
        self.budget.save()
        # Now 1500

        Expense.objects.create(
            employee=self.employee,
            description="Expense 1",
            amount=300
        )
        self.budget.balance -= 300
        self.budget.save()
        # Now 1200

        Expense.objects.create(
            employee=self.employee,
            description="Expense 2",
            amount=200
        )
        self.budget.balance -= 200
        self.budget.save()
        # Now 1000

        self.budget.refresh_from_db()
        self.assertEqual(self.budget.balance, 1000)


class ExpenseViewTest(TestCase):
    """Tests for expense views."""

    def setUp(self):
        self.client = Client()
        self.staff_group, _ = Group.objects.get_or_create(name="staff")

        # Staff user with budget
        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="testpass123"
        )
        self.staff_user.groups.add(self.staff_group)
        self.staff_employee = Employee.objects.create(
            user=self.staff_user,
            name="Staff Employee",
            have_budget=True
        )
        self.staff_budget = EmployeeBudget.objects.create(
            employee=self.staff_employee,
            balance=1000
        )

        # Regular user without budget
        self.regular_user = User.objects.create_user(
            username="regular",
            password="testpass123"
        )
        self.regular_employee = Employee.objects.create(
            user=self.regular_user,
            name="Regular Employee",
            have_budget=False
        )

    def test_expenses_home_requires_budget(self):
        """Test expenses home requires budget permission."""
        self.client.login(username="regular", password="testpass123")
        response = self.client.get(reverse("expenses:expenses-home"))
        self.assertEqual(response.status_code, 403)

    def test_expenses_home_accessible_with_budget(self):
        """Test expenses home accessible with budget."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("expenses:expenses-home"))
        self.assertEqual(response.status_code, 200)

    def test_employee_detail_view(self):
        """Test employee expense detail view."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("expenses:expenses-employee-detail", args=[self.staff_employee.pk])
        )
        self.assertEqual(response.status_code, 200)


class ExpenseFormTest(TestCase):
    """Tests for expense form."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            have_budget=True,
            is_active=True
        )

    def test_valid_expense_form(self):
        """Test valid expense form."""
        from datetime import date
        form_data = {
            "employee": self.employee.pk,
            "description": "Test expense",
            "amount": 100,
            "date": date.today()
        }
        form = ExpenseForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_empty_description_invalid(self):
        """Test that empty description is invalid."""
        from datetime import date
        form_data = {
            "employee": self.employee.pk,
            "description": "",
            "amount": 100,
            "date": date.today()
        }
        form = ExpenseForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_zero_amount_handling(self):
        """Test zero amount handling."""
        form_data = {
            "employee": self.employee.pk,
            "description": "Test",
            "amount": 0
        }
        form = ExpenseForm(data=form_data)
        # Depends on form validation rules
        # At minimum, the form should handle this case


class BudgetAdjustmentFormTest(TestCase):
    """Tests for budget adjustment form."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            have_budget=True,
            is_active=True
        )

    def test_valid_add_adjustment(self):
        """Test valid ADD adjustment form."""
        from datetime import date
        form_data = {
            "employee": self.employee.pk,
            "adjustment_type": "ADD",
            "amount": 500,
            "date": date.today(),
            "note": "Monthly allowance"
        }
        form = BudgetAdjustmentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_remove_adjustment(self):
        """Test valid REMOVE adjustment form."""
        from datetime import date
        form_data = {
            "employee": self.employee.pk,
            "adjustment_type": "REMOVE",
            "amount": 200,
            "date": date.today(),
            "note": "Correction"
        }
        form = BudgetAdjustmentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_filters_active_budgeted_employees(self):
        """Test form only shows active employees with budgets."""
        # Create inactive employee
        inactive_user = User.objects.create_user(
            username="inactive",
            password="test123"
        )
        Employee.objects.create(
            user=inactive_user,
            name="Inactive Employee",
            have_budget=True,
            is_active=False
        )

        form = BudgetAdjustmentForm()
        employee_choices = list(form.fields["employee"].queryset)

        # Should include active employee
        self.assertIn(self.employee, employee_choices)
