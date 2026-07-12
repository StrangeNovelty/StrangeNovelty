from typing import Any

from django.db import models

from scenes.exceptions import ImmutableMutationOperationError, ImmutableRevisionError


class ImmutableRevisionQuerySet(models.QuerySet):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ImmutableRevisionError("Scene Revisions cannot be updated.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ImmutableRevisionError("Scene Revisions cannot be deleted.")


class SceneRevisionManager(models.Manager):
    def get_queryset(self) -> ImmutableRevisionQuerySet:
        return ImmutableRevisionQuerySet(self.model, using=self._db)


class ImmutableMutationOperationQuerySet(models.QuerySet):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ImmutableMutationOperationError("Mutation Operations cannot be updated.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ImmutableMutationOperationError("Mutation Operations cannot be deleted.")


class MutationOperationManager(models.Manager):
    def get_queryset(self) -> ImmutableMutationOperationQuerySet:
        return ImmutableMutationOperationQuerySet(self.model, using=self._db)
