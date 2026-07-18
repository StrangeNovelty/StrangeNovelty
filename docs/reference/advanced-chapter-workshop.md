# Advanced Chapter Workshop

Chapter planning and Scene prose remain separate. A Chapter may combine free-form outline text with ordered `ChapterBeat` records, a one-to-one pacing profile, author-controlled checklist items, and reversible planning snapshots. Snapshots contain Chapter planning, Beats, and pacing—not Scene prose, whose history remains in immutable Scene revisions.

`SceneBrief` records describe intent for a particular immutable source revision. One Brief may be active per Scene; activating another supersedes the previous Brief, and changing the Scene revision makes the older Brief visibly stale without deleting it.

`WritingDelta` records the positive word-count difference for each accepted immutable Scene revision. Its one-to-one Revision identity prevents double counting. Series Map and Pacing Map are derived views and do not create duplicate story aggregates.

AI pacing, outline, voice, continuity, and Scene Brief tasks remain reviewed suggestions. They never overwrite planning or prose automatically.
