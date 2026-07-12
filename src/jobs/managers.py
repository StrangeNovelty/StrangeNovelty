from typing import Any

from django.db import models

from jobs.exceptions import ImmutableJobRecord


class ProtectedOperationalQuerySet(models.QuerySet):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ImmutableJobRecord("Operational records require job services.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ImmutableJobRecord("Operational records cannot be deleted.")


class ProtectedOperationalManager(models.Manager):
    def get_queryset(self) -> ProtectedOperationalQuerySet:
        return ProtectedOperationalQuerySet(self.model, using=self._db)
