import hashlib
import unicodedata

from scenes.exceptions import InvalidSceneContent

CONTENT_FORMAT_VERSION = "plain-text-v1"
NORMALIZATION_VERSION = "plain-text-nfc-lf-v1"
MAX_CONTENT_CHARACTERS = 1_000_000


def normalize_scene_content(value: str) -> str:
    """Produce the deterministic Version 1 authoritative plain-text value."""
    if not isinstance(value, str):
        raise InvalidSceneContent("Scene content must be text.")
    if "\x00" in value:
        raise InvalidSceneContent("Scene content contains a prohibited NUL character.")
    if len(value) > MAX_CONTENT_CHARACTERS:
        raise InvalidSceneContent("Scene content exceeds the supported character limit.")

    line_normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", line_normalized)


def content_sha256(value: str) -> str:
    """Hash an already normalized authoritative value as UTF-8."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
