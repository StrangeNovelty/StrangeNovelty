from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import HttpRequest, HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


def database_ready() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        return not executor.migration_plan(targets)
    except Exception:
        return False


@never_cache
@require_GET
def liveness(request: HttpRequest) -> HttpResponse:
    del request
    return HttpResponse("live", content_type="text/plain")


@never_cache
@require_GET
def readiness(request: HttpRequest) -> HttpResponse:
    del request
    ready = not settings.MAINTENANCE_MODE and settings.SERVICE_ROLE == "web" and database_ready()
    return HttpResponse(
        "ready" if ready else "not-ready",
        status=200 if ready else 503,
        content_type="text/plain",
    )
