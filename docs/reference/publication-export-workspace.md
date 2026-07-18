# Publication and Manuscript Export Workspace

The `publishing` app assembles existing Work structure and immutable Scene Revisions into private,
versioned reading copies. A Manuscript Project stores selection and presentation intent; it does not
create a second copy of story prose. Ordered entries represent headings, selected Chapters and
Scenes, front or back matter, and explicit glossary material.

Every Scene entry resolves to one immutable Scene Revision. Latest selections can be refreshed
deliberately, while locked selections remain stable and display a warning when a newer Revision
exists. Approved Projects are never silently repopulated or refreshed. Compilation is deterministic
and produces a structured intermediate document, source snapshot, warnings, counts, and checksum
without mutating story records.

Formatting profiles are versioned product behavior. The initial profiles cover prose, web serial,
archive, screenplay, and comic-script foundations without claiming full typesetting or structured
script parsing. Plain text, Markdown, standalone HTML, DOCX, and PDF generators consume the same
compiled document.

Export files use Django's private storage abstraction and opaque keys. Downloads are mediated by
Workspace authorization. Local development uses the ignored private media root; hosted deployments
may configure any private Django storage backend. Generated files, manuscript content, storage
keys, and private Artwork are never committed or exposed through public static paths.

Publication Entries track plans and recorded public outcomes only. They do not publish externally.
At publication time, the selected Chapter's Scene Revision identities are snapshotted so later
changes can be reported deterministically.

AI publication tasks operate on an explicitly selected Manuscript context. They create reviewable
suggestions and never mutate a Manuscript, Work, Chapter, or Scene automatically.
