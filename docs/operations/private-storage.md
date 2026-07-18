# Private Hosted Storage

Strange Novelty keeps relational metadata in PostgreSQL and stores uploaded Research files,
Artwork, and generated manuscript exports through Django's storage abstraction. Files remain
private application content: browser access always passes through an authenticated,
Workspace-scoped application route.

## Development backend

`PRIVATE_STORAGE_BACKEND=filesystem` is the default. The `private` and `exports` storage
aliases use `PRIVATE_MEDIA_ROOT`, which defaults to the repository-excluded
`.private-media` directory. This backend is convenient for local development but is not
durable hosted storage.

## S3-compatible backend

Set `PRIVATE_STORAGE_BACKEND=s3` to use a private S3-compatible object store. The runtime
then requires:

- `PRIVATE_STORAGE_BUCKET`
- `PRIVATE_STORAGE_ENDPOINT_URL`
- `PRIVATE_STORAGE_ACCESS_KEY_ID`
- `PRIVATE_STORAGE_SECRET_ACCESS_KEY`

Optional provider-neutral settings are:

- `PRIVATE_STORAGE_REGION`
- `PRIVATE_STORAGE_CUSTOM_DOMAIN`
- `PRIVATE_STORAGE_ADDRESSING_STYLE` (`auto`, `path`, or `virtual`)
- `PRIVATE_STORAGE_SIGNATURE_VERSION` (`s3v4` by default)
- `PRIVATE_STORAGE_UPLOAD_PREFIX` (`uploads` by default)
- `PRIVATE_STORAGE_EXPORT_PREFIX` (`exports` by default)

The application configures no public ACL, requests signed access from the backend, disables
object overwrites, and stores uploads and exports under separate aliases and prefixes. The
bucket itself must have public access disabled. Access credentials must remain in the hosted
environment and must never enter Git, logs, Jobs, rendered HTML, or test snapshots.

## Delivery and temporary files

Research downloads, Artwork previews, and export downloads are streamed only after normal
Workspace authorization. Templates do not use storage URLs or reveal filesystem paths or
object keys. Missing local or remote objects return the existing unavailable-file response.

Text extraction reads source objects through `FieldFile.open()`. DOCX and PDF generation is
performed in memory by the current generators, and completed export bytes are saved through
the `exports` alias. If a future format requires a temporary local file, it must use a bounded
temporary directory and remove the file after success or failure before saving the completed
artifact through Django storage.

Database backups and object-store backups are complementary. A complete recovery requires
both relational metadata and the referenced private objects.
