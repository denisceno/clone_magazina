"""
Test settings - uses SQLite for faster tests without needing PostgreSQL permissions.
"""
from .settings import *

# Use SQLite for testing (faster and no permission issues)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable axes for testing to avoid lockout issues
AXES_ENABLED = False

# Faster email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
