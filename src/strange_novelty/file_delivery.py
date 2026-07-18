"""Storage-neutral opening of private objects for authenticated delivery."""

from botocore.exceptions import BotoCoreError, ClientError


class PrivateObjectUnavailable(Exception):
    """A private object cannot be read from its configured storage backend."""


def open_private_object(field_file):
    try:
        return field_file.open("rb")
    except (OSError, BotoCoreError, ClientError) as exc:
        raise PrivateObjectUnavailable from exc
