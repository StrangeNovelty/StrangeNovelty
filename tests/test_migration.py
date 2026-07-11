from importlib import import_module

from django.db.migrations.operations.models import CreateModel


def test_initial_accounts_migration_creates_custom_account() -> None:
    migration_module = import_module("accounts.migrations.0001_initial")
    migration = migration_module.Migration("0001_initial", "accounts")

    created_models = {
        operation.name for operation in migration.operations if isinstance(operation, CreateModel)
    }

    assert migration.initial is True
    assert created_models == {"Account"}
    assert ("auth", "0012_alter_user_first_name_max_length") in migration.dependencies
