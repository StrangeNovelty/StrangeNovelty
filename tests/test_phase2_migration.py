from importlib import import_module

from django.db.migrations.operations.models import CreateModel
from django.db.migrations.operations.special import RunPython


def test_workspace_initial_migration_contains_only_schema_operations() -> None:
    migration_module = import_module("workspaces.migrations.0001_initial")
    migration = migration_module.Migration("0001_initial", "workspaces")

    created_models = {
        operation.name for operation in migration.operations if isinstance(operation, CreateModel)
    }

    assert migration.initial is True
    assert created_models == {"Workspace", "WorkspaceGrant", "OwnerBootstrap"}
    assert not any(isinstance(operation, RunPython) for operation in migration.operations)
