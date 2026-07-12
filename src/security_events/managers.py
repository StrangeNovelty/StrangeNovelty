from typing import Any

from django.db import models

from security_events.exceptions import ImmutableSecurityEventError


class ImmutableSecurityEventQuerySet(models.QuerySet):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ImmutableSecurityEventError("Security Events cannot be updated.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ImmutableSecurityEventError("Security Events cannot be deleted.")


class SecurityEventManager(models.Manager):
    def get_queryset(self) -> ImmutableSecurityEventQuerySet:
        return ImmutableSecurityEventQuerySet(self.model, using=self._db)
