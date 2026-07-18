# Research and Artwork Workspace

The `library` app keeps private reference material separate from story canon. A Research Source
records provenance and optional private file metadata. A Research Note separates copied source
material, the author's interpretation, and possible story application. Artwork Assets hold visual
reference metadata and private images. Collections provide ordered mixed research folders and mood
boards.

Files use Django's configured `default` storage. Development defaults to `PRIVATE_MEDIA_ROOT`
(`.private-media`, ignored by Git). A hosted installation can replace the default storage with a
private S3-compatible or other Django storage backend. Files are delivered only through
Workspace-authorized application routes; templates never expose storage keys or host paths.

Text extraction is explicit, checksum-aware, and format-specific. Plain text, Markdown, HTML, and
DOCX embedded text are supported. PDF and image OCR are deliberately deferred. Extracted text is
provisional source material, not an approved quotation or canon claim.

Typed Library connections link Sources, Notes, Artwork, and Collections to the bounded story
domains. Selected Library records can enter AI Context Packs with citations and provenance.
Artwork contributes descriptions, alt text, palette, and mood metadata only; image bytes are not
sent to providers.

The durable distinction is:

1. source material and its provenance;
2. author interpretation and proposed story application;
3. native story records created only after explicit author review.
