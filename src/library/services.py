import hashlib
import html.parser
import io
import mimetypes
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_RESEARCH_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".html",
    ".htm",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
}
ALLOWED_ART_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


class TextCollector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def inspect_upload(upload, *, artwork=False):
    maximum = settings.LIBRARY_MAX_UPLOAD_BYTES
    if upload.size > maximum:
        raise ValidationError(f"File exceeds the {maximum} byte limit.")
    extension = Path(upload.name).suffix.lower()
    allowed = ALLOWED_ART_EXTENSIONS if artwork else ALLOWED_RESEARCH_EXTENSIONS
    if extension not in allowed:
        raise ValidationError("This file type is not supported.")
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    mime = (
        getattr(upload, "content_type", "")
        or mimetypes.guess_type(upload.name)[0]
        or "application/octet-stream"
    )
    width, height = image_dimensions(upload, extension) if artwork else (None, None)
    upload.seek(0)
    return {
        "original_filename": Path(upload.name).name[:255],
        "mime_type": mime[:120],
        "size": upload.size,
        "checksum": digest.hexdigest(),
        "width": width,
        "height": height,
    }


def image_dimensions(upload, extension):
    data = upload.read(32)
    if extension == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])
    if extension == ".gif" and data[:3] == b"GIF":
        return struct.unpack("<HH", data[6:10])
    if extension in {".jpg", ".jpeg"}:
        upload.seek(0)
        stream = io.BytesIO(upload.read())
        stream.read(2)
        while True:
            marker = stream.read(1)
            if not marker:
                break
            if marker != b"\xff":
                continue
            code = stream.read(1)
            if code in {bytes([v]) for v in range(0xC0, 0xC4)}:
                stream.read(3)
                height, width = struct.unpack(">HH", stream.read(4))
                return width, height
            length = stream.read(2)
            if len(length) != 2:
                break
            stream.seek(struct.unpack(">H", length)[0] - 2, 1)
    return None, None


def extract_source_text(source):
    if not source.source_file:
        raise ValidationError("This Source has no file.")
    if (
        source.extraction_checksum == source.checksum
        and source.extracted_text_status == "extracted"
    ):
        return source.extracted_text
    extension = Path(source.original_filename).suffix.lower()
    try:
        with source.source_file.open("rb") as handle:
            data = handle.read(settings.LIBRARY_MAX_EXTRACT_BYTES + 1)
        if len(data) > settings.LIBRARY_MAX_EXTRACT_BYTES:
            raise ValueError("File exceeds extraction size limit.")
        if extension in {".txt", ".md"}:
            text = data.decode("utf-8")
        elif extension in {".html", ".htm"}:
            parser = TextCollector()
            parser.feed(data.decode("utf-8", errors="replace"))
            text = "\n".join(part.strip() for part in parser.parts if part.strip())
        elif extension == ".docx":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                xml = archive.read("word/document.xml")
            root = ElementTree.fromstring(xml)
            text = "\n".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
        else:
            source.extracted_text_status = "unsupported"
            source.extraction_error = "Embedded text extraction is not available for this format."
            source.save(update_fields=("extracted_text_status", "extraction_error", "updated_at"))
            return ""
    except Exception as exc:
        source.extracted_text_status = "failed"
        source.extraction_error = f"Extraction failed: {exc.__class__.__name__}"
        source.save(update_fields=("extracted_text_status", "extraction_error", "updated_at"))
        return ""
    source.extracted_text = text[: settings.LIBRARY_MAX_EXTRACTED_TEXT_CHARS]
    source.extracted_text_status = "extracted"
    source.extraction_error = ""
    source.extraction_checksum = source.checksum
    source.save(
        update_fields=(
            "extracted_text",
            "extracted_text_status",
            "extraction_error",
            "extraction_checksum",
            "updated_at",
        )
    )
    return source.extracted_text
