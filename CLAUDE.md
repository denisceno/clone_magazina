# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Elb Ndertuesi Magazina is a Django 6.0.1-based warehouse/inventory management system for tracking inventory, fuel, expenses, and employee budgets. It uses PostgreSQL and is deployed on Railway.app.

## Common Commands

```bash
# Development server (from Elb_Ndertuesi directory)
python manage.py runserver

# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test accounts
python manage.py test inventory

# Run a single test class or method
python manage.py test accounts.tests.LoginTestCase
python manage.py test inventory.tests.ProductModelTest.test_something

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Collect static files (production)
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser
```

## Environment Setup

Required `.env` file in `Elb_Ndertuesi/`:
```
DEBUG=1
SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
POSTGRES_DB=magazina_db_clone
POSTGRES_USER=magazina_user
POSTGRES_PASSWORD=<password>
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

For production/Railway, set `DATABASE_URL` instead of individual Postgres vars.

## Architecture

### Django Apps (7 apps)

| App | Purpose |
|-----|---------|
| **accounts** | Authentication, login/logout, LoginRequiredMiddleware |
| **core** | Employee & Vehicle models, home view, error handlers |
| **management** | Admin CRUD for Employees, Vehicles, Depots, FuelTanks |
| **inventory** | Depot, Product, Withdrawal/Return tracking |
| **fuel** | FuelTank, FuelEntry (refills), FuelUsage tracking |
| **expenses** | EmployeeBudget, Expense, BudgetAdjustment |
| **audit** | AuditLog for all actions, CaptureIPMiddleware |

### Permission System

Three-tier permission model using decorators from `management/permissions.py`:
- `@admin_required` - superuser only
- `@staff_required` - superuser OR staff group
- `@employee_required` - superuser OR staff OR employee group

Global authentication enforced via `accounts.middleware.LoginRequiredMiddleware` - all pages require login except auth endpoints.

### Key Model Relationships

**Inventory flow:**
- Depot → Product (products belong to depots)
- Employee withdraws products → WithdrawalHeader + WithdrawalItems
- Employee returns items → ReturnHeader + ReturnItems (linked to original WithdrawalItems)
- `outstanding_qty` = withdrawn - returned (calculated property)

**Fuel flow:**
- FuelTank → FuelEntry (refills, only ONE can be OPEN per tank at a time)
- FuelUsage linked to open FuelEntry, tracks vehicle/operator/project
- `current_level` = total entries - total usage

**Expense flow:**
- Employee (with `have_budget=True`) → EmployeeBudget
- Budget adjusted via Expense or BudgetAdjustment records

### Middleware Stack Order

1. SecurityMiddleware
2. WhiteNoiseMiddleware (static files)
3. SessionMiddleware
4. CommonMiddleware
5. CsrfViewMiddleware
6. AuthenticationMiddleware
7. MessagesMiddleware
8. AxesMiddleware (rate limiting)
9. CaptureIPMiddleware (audit IP capture)
10. LoginRequiredMiddleware (global auth check)

### Security Features

- **django-axes**: 5 failed login attempts = 30-minute lockout
- Session timeout: 15 minutes of inactivity
- Audit logging via `audit.utils.log_action()` - call this for CREATE, UPDATE, DELETE, WITHDRAW, RETURN actions

### URL Namespaces

- `/accounts/` - login, logout
- `/home/` - dashboard (core:home)
- `/management/` - admin CRUD (employees, vehicles, depots, fuel-tanks)
- `/inventory/` - depot/product/withdrawal/return management
- `/fuel/` - fuel tank and usage tracking
- `/expenses/` - budget and expense tracking
- `/audit/` - audit log viewing
- `/admin/` - Django admin

## Code Patterns

### Forms
- Use ModelForms with custom `clean()` for business logic validation
- Albanian language labels are used in form widgets
- Dynamic querysets in `__init__` (e.g., filter active employees with budget)

### Querysets
- Use `select_related()` and `prefetch_related()` to prevent N+1 queries
- Use `@transaction.atomic` and `select_for_update()` for race condition prevention (especially fuel operations)

### Audit Logging
Always call `log_action()` from `audit.utils` when modifying data:
```python
from audit.utils import log_action
log_action(request.user, "CREATE", "Employee", employee.id, f"Created {employee.name}", get_client_ip(request))
```
