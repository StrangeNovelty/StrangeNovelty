import uuid
from typing import cast

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from accounts.managers import AccountManager


class Account(AbstractBaseUser, PermissionsMixin):
    """Project-owned human identity; not Workspace authorization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now, editable=False)

    objects = AccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ("email",)
        verbose_name = "account"
        verbose_name_plural = "accounts"

    def __str__(self) -> str:
        return cast(str, self.email)
