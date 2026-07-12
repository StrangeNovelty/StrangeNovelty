from io import StringIO

from django.core.management import call_command
from django.test import Client


def test_health_response_is_minimal() -> None:
    response = Client().get("/health/")

    assert response.status_code == 200
    assert response.content == b"live"
    assert response.headers["Content-Type"].startswith("text/plain")


def test_django_system_checks_pass() -> None:
    output = StringIO()

    call_command("check", stdout=output, stderr=output)

    assert "no issues" in output.getvalue().casefold()
