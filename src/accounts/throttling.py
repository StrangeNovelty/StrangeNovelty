import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import AuthenticationThrottle


def throttle_digest(scope: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), scope.encode(), hashlib.sha256).hexdigest()


@transaction.atomic
def register_failure(category: str, scope: str) -> bool:
    now = timezone.now()
    digest = throttle_digest(scope)
    row, _ = AuthenticationThrottle.objects.select_for_update().get_or_create(
        keyed_digest=digest, category=category, defaults={"window_started_at": now}
    )
    if row.window_started_at < now - timedelta(seconds=settings.AUTH_THROTTLE_WINDOW_SECONDS):
        row.window_started_at, row.attempt_count, row.blocked_until = now, 0, None
    row.attempt_count += 1
    if row.attempt_count >= settings.AUTH_THROTTLE_MAX_ATTEMPTS:
        row.blocked_until = now + timedelta(seconds=settings.AUTH_THROTTLE_BLOCK_SECONDS)
    row.save()
    return bool(row.blocked_until and row.blocked_until > now)


def is_blocked(category: str, scope: str) -> bool:
    return bool(
        AuthenticationThrottle.objects.filter(
            keyed_digest=throttle_digest(scope), category=category, blocked_until__gt=timezone.now()
        ).exists()
    )


def clear_failures(category: str, scope: str) -> None:
    AuthenticationThrottle.objects.filter(
        keyed_digest=throttle_digest(scope), category=category
    ).delete()
