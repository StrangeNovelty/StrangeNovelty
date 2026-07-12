from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet() -> Fernet:
    try:
        return Fernet(settings.MFA_ENCRYPTION_KEY.encode("ascii"))
    except (AttributeError, ValueError) as exc:
        raise ImproperlyConfigured("MFA encryption configuration is invalid.") from exc


def encrypt_secret(value: bytes) -> bytes:
    return _fernet().encrypt(value)


def decrypt_secret(value: bytes) -> bytes:
    try:
        return _fernet().decrypt(value)
    except InvalidToken as exc:
        raise PermissionError("Protected authentication material is unavailable.") from exc
