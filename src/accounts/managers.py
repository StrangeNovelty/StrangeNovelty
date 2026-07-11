from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from accounts.models import Account


class AccountManager(BaseUserManager):
    use_in_migrations = True

    @staticmethod
    def normalize_login_email(email: str) -> str:
        """Normalize the complete address for consistent login identity."""
        normalized = BaseUserManager.normalize_email(email)
        return cast(str, normalized).strip().casefold()

    def _create_user(self, email: str, password: str | None, **extra_fields: Any) -> Account:
        if not email or not email.strip():
            raise ValueError("An email address is required.")

        normalized_email = self.normalize_login_email(email)
        account = cast("Account", self.model(email=normalized_email, **extra_fields))
        account.set_password(password)
        account.save(using=self._db)
        return account

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> Account:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> Account:
        if not password:
            raise ValueError("A superuser password is required.")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        if extra_fields.get("is_active") is not True:
            raise ValueError("A superuser must have is_active=True.")

        return self._create_user(email, password, **extra_fields)
