import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from jobs.models import Job, JobAttempt
from scenes.models import MutationOperation, Scene, SceneRevision
from workspaces.models import Workspace


class AIRequest(models.Model):
    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        QUARANTINED = "quarantined", "Quarantined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="ai_requests")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ai_requests"
    )
    scene = models.ForeignKey(Scene, on_delete=models.PROTECT, related_name="ai_requests")
    source_revision = models.ForeignKey(
        SceneRevision, on_delete=models.PROTECT, related_name="ai_requests"
    )
    source_scene_version = models.PositiveBigIntegerField()
    source_content_hash = models.CharField(max_length=64)
    capability = models.CharField(max_length=32, default="scene_revision_suggestion")
    prompt_template = models.CharField(max_length=32, default="scene-review")
    prompt_template_version = models.CharField(max_length=16, default="v1")
    configuration_version = models.CharField(max_length=32, default="ai-scene-v1")
    instruction = models.TextField(max_length=1000)
    instruction_hash = models.CharField(max_length=64)
    provider = models.CharField(max_length=32, default="local_fake")
    requested_model = models.CharField(max_length=32, default="deterministic-v1")
    request_fingerprint = models.CharField(max_length=64)
    idempotency_key = models.CharField(max_length=128)
    state = models.CharField(max_length=16, choices=State.choices, default=State.QUEUED)
    job = models.OneToOneField(
        Job, on_delete=models.PROTECT, null=True, blank=True, related_name="ai_request"
    )
    maximum_output_characters = models.PositiveIntegerField(default=1_000_000)
    failure_classification = models.CharField(max_length=24, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    quarantined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "requested_by", "idempotency_key"),
                name="unique_ai_request_key",
            ),
            models.CheckConstraint(
                condition=Q(source_content_hash__regex=r"^[0-9a-f]{64}$")
                & Q(instruction_hash__regex=r"^[0-9a-f]{64}$")
                & Q(request_fingerprint__regex=r"^[0-9a-f]{64}$"),
                name="ai_request_hashes_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    capability="scene_revision_suggestion",
                    prompt_template="scene-review",
                    prompt_template_version="v1",
                    configuration_version="ai-scene-v1",
                ),
                name="ai_request_versions_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    state__in=(
                        "queued",
                        "running",
                        "completed",
                        "failed",
                        "cancelled",
                        "expired",
                        "quarantined",
                    )
                ),
                name="ai_request_state_valid",
            ),
            models.CheckConstraint(
                condition=Q(idempotency_key__regex=r"^[A-Za-z0-9._~-]{16,128}$"),
                name="ai_request_key_valid",
            ),
        ]
        indexes = [models.Index(fields=("workspace", "state"), name="ai_request_ws_state_idx")]

    def __str__(self) -> str:
        return f"AI Request {self.id}"


class AIContextManifest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.OneToOneField(
        AIRequest, on_delete=models.PROTECT, related_name="context_manifest"
    )
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ai_context_manifests"
    )
    scene = models.ForeignKey(Scene, on_delete=models.PROTECT, related_name="ai_context_manifests")
    source_revision = models.ForeignKey(
        SceneRevision, on_delete=models.PROTECT, related_name="ai_context_manifests"
    )
    source_scene_version = models.PositiveBigIntegerField()
    source_content_hash = models.CharField(max_length=64)
    capability = models.CharField(max_length=32)
    prompt_template = models.CharField(max_length=32)
    prompt_template_version = models.CharField(max_length=16)
    configuration_version = models.CharField(max_length=32)
    context_construction_version = models.CharField(max_length=32, default="single-scene-v1")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"AI Context Manifest {self.id}"


class ProviderEffect(models.Model):
    class Outcome(models.TextChoices):
        INTENDED = "intended", "Intended"
        KNOWN_SUCCESS = "known_success", "Known success"
        KNOWN_FAILURE = "known_failure", "Known failure"
        AMBIGUOUS = "ambiguous", "Ambiguous"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(
        AIRequest, on_delete=models.PROTECT, related_name="provider_effects"
    )
    job_attempt = models.ForeignKey(
        JobAttempt, on_delete=models.PROTECT, null=True, blank=True, related_name="provider_effects"
    )
    provider = models.CharField(max_length=32)
    operation_identifier = models.CharField(max_length=64, blank=True, default="")
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    ambiguity_classification = models.CharField(max_length=24, blank=True, default="")
    requested_at = models.DateTimeField()
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("request", "job_attempt"),
                condition=Q(job_attempt__isnull=False),
                name="unique_ai_effect_attempt",
            ),
            models.CheckConstraint(
                condition=Q(
                    outcome__in=(
                        "intended",
                        "known_success",
                        "known_failure",
                        "ambiguous",
                        "cancelled",
                    )
                ),
                name="provider_effect_outcome_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Provider Effect {self.id}"


class AISuggestion(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        REJECTED = "rejected", "Rejected"
        APPLIED = "applied", "Applied"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"
        QUARANTINED = "quarantined", "Quarantined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ai_suggestions"
    )
    request = models.OneToOneField(AIRequest, on_delete=models.PROTECT, related_name="suggestion")
    scene = models.ForeignKey(Scene, on_delete=models.PROTECT, related_name="ai_suggestions")
    source_revision = models.ForeignKey(
        SceneRevision, on_delete=models.PROTECT, related_name="ai_suggestions"
    )
    source_scene_version = models.PositiveBigIntegerField()
    source_content_hash = models.CharField(max_length=64)
    original_output = models.TextField(max_length=1_000_000)
    review_text = models.TextField(max_length=1_000_000)
    output_hash = models.CharField(max_length=64)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    provider = models.CharField(max_length=32)
    model_classification = models.CharField(max_length=32)
    prompt_template = models.CharField(max_length=32)
    prompt_template_version = models.CharField(max_length=16)
    provider_operation_identifier = models.CharField(max_length=64, blank=True, default="")
    input_units = models.PositiveIntegerField(default=0)
    output_units = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    quarantined_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_ai_suggestions",
    )
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="applied_ai_suggestions",
    )
    resulting_revision = models.ForeignKey(
        SceneRevision,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="applied_ai_suggestions",
    )
    resulting_scene_version = models.PositiveBigIntegerField(null=True, blank=True)
    disposition_classification = models.CharField(max_length=24, blank=True, default="")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    state__in=(
                        "pending",
                        "ready",
                        "rejected",
                        "applied",
                        "expired",
                        "failed",
                        "quarantined",
                    )
                ),
                name="ai_suggestion_state_valid",
            ),
            models.CheckConstraint(
                condition=Q(source_content_hash__regex=r"^[0-9a-f]{64}$")
                & Q(output_hash__regex=r"^[0-9a-f]{64}$"),
                name="ai_suggestion_hashes_valid",
            ),
        ]
        indexes = [models.Index(fields=("workspace", "state"), name="ai_suggestion_ws_state_idx")]

    def __str__(self) -> str:
        return f"AI Suggestion {self.id}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            original = (
                AISuggestion.objects.filter(id=self.id)
                .values_list("original_output", flat=True)
                .first()
            )
            if original != self.original_output:
                raise ValidationError("Original AI output is immutable.")
        super().save(*args, **kwargs)


class AISuggestionApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    suggestion = models.OneToOneField(
        AISuggestion, on_delete=models.PROTECT, related_name="application_provenance"
    )
    revision = models.OneToOneField(
        SceneRevision, on_delete=models.PROTECT, related_name="ai_application_provenance"
    )
    mutation_operation = models.OneToOneField(
        MutationOperation, on_delete=models.PROTECT, related_name="ai_application_provenance"
    )
    applied_text_hash = models.CharField(max_length=64)
    human_edited = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"AI Suggestion Application {self.id}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValidationError("AI application provenance is append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise ValidationError("AI application provenance cannot be deleted.")


class VoiceProfile(models.Model):
    STATUSES = (("draft", "Draft"), ("active", "Active"), ("archived", "Archived"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="voice_profiles"
    )
    work = models.ForeignKey(
        "stories.Work",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="voice_profiles",
    )
    name = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUSES, default="draft")
    source_notes = models.TextField(blank=True)
    prose_guidance = models.TextField(blank=True)
    dialogue_guidance = models.TextField(blank=True)
    sentence_rhythm = models.TextField(blank=True)
    paragraph_rhythm = models.TextField(blank=True)
    diction = models.TextField(blank=True)
    imagery = models.TextField(blank=True)
    humor = models.TextField(blank=True)
    emotional_distance = models.TextField(blank=True)
    exposition_approach = models.TextField(blank=True)
    prohibited_tendencies = models.TextField(blank=True)
    intentional_quirks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.UniqueConstraint(fields=("workspace", "name"), name="voice_ws_name_uniq")
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.work_id and self.workspace_id and self.work.workspace_id != self.workspace_id:
            raise ValidationError({"work": "Work must belong to this Workspace."})


class AIContextPack(models.Model):
    STATUSES = (("active", "Active"), ("draft", "Draft"), ("archived", "Archived"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ai_context_packs"
    )
    name = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    work = models.ForeignKey(
        "stories.Work",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ai_context_packs",
    )
    chapter = models.ForeignKey(
        "stories.Chapter",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ai_context_packs",
    )
    voice_profile = models.ForeignKey(
        VoiceProfile, null=True, blank=True, on_delete=models.PROTECT, related_name="context_packs"
    )
    status = models.CharField(max_length=16, choices=STATUSES, default="draft")
    author_instructions = models.TextField(blank=True)
    tone_guidance = models.TextField(blank=True)
    genre_guidance = models.TextField(blank=True)
    adult_audience_guidance = models.TextField(blank=True)
    exclusions = models.TextField(blank=True)
    prioritization_notes = models.TextField(blank=True)
    detail_level = models.CharField(
        max_length=16, choices=(("concise", "Concise"), ("detailed", "Detailed")), default="concise"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.UniqueConstraint(fields=("workspace", "name"), name="ai_pack_ws_name_uniq")
        ]

    def __str__(self):
        return self.name

    def clean(self):
        for name in ("work", "chapter", "voice_profile"):
            value = getattr(self, name, None)
            if value and self.workspace_id and value.workspace_id != self.workspace_id:
                raise ValidationError({name: "Selection must belong to this Workspace."})
        if self.chapter_id and self.work_id and self.chapter.work_id != self.work_id:
            raise ValidationError({"chapter": "Chapter must belong to the selected Work."})


class AIContextTypedLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack = models.ForeignKey(AIContextPack, on_delete=models.CASCADE)
    role = models.CharField(max_length=80, blank=True)
    priority = models.PositiveSmallIntegerField(default=50)
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ("priority", "order", "id")

    def __str__(self):
        return f"{self.pack}: context"

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name != "pack":
                record = getattr(self, field.name, None)
                workspace_id = (
                    getattr(record, "workspace_id", None)
                    or getattr(getattr(record, "thread", None), "workspace_id", None)
                    or getattr(getattr(record, "draw", None), "workspace_id", None)
                    or getattr(getattr(record, "deck", None), "workspace_id", None)
                    or getattr(getattr(record, "ability", None), "workspace_id", None)
                )
                if record and workspace_id != self.pack.workspace_id:
                    raise ValidationError({field.name: "Context must belong to this Workspace."})


def context_constraint(name, field):
    return [models.UniqueConstraint(fields=("pack", field), name=name)]


def context_link(name, target, field):
    meta = type(
        "Meta",
        (AIContextTypedLink.Meta,),
        {"constraints": context_constraint(f"ai_pack_{field}_uniq", field)},
    )
    model = type(
        name,
        (AIContextTypedLink,),
        {
            "__module__": __name__,
            field: models.ForeignKey(
                target, on_delete=models.PROTECT, related_name="ai_context_links"
            ),
            "Meta": meta,
        },
    )
    globals()[name] = model
    return model


AIContextVolumeLink = context_link("AIContextVolumeLink", "stories.Volume", "volume")
AIContextArcLink = context_link("AIContextArcLink", "stories.Arc", "arc")
AIContextSceneLink = context_link("AIContextSceneLink", "scenes.Scene", "scene")
AIContextCharacterLink = context_link("AIContextCharacterLink", "characters.Character", "character")
AIContextGroupLink = context_link("AIContextGroupLink", "characters.CharacterGroup", "group")
AIContextAbilityLink = context_link("AIContextAbilityLink", "characters.Ability", "ability")
AIContextLocationLink = context_link("AIContextLocationLink", "worldbuilding.Location", "location")
AIContextRegionLink = context_link("AIContextRegionLink", "worldbuilding.Region", "region")
AIContextCodexLink = context_link("AIContextCodexLink", "worldbuilding.CodexEntry", "codex")
AIContextItemLink = context_link("AIContextItemLink", "worldbuilding.WorldItem", "item")
AIContextCreatureLink = context_link("AIContextCreatureLink", "worldbuilding.Creature", "creature")
AIContextThreadLink = context_link("AIContextThreadLink", "continuity.PlotThread", "thread")
AIContextSecretLink = context_link("AIContextSecretLink", "continuity.Secret", "secret")
AIContextClueLink = context_link("AIContextClueLink", "continuity.ThreadClue", "clue")
AIContextRevealLink = context_link("AIContextRevealLink", "continuity.ThreadReveal", "reveal")
AIContextReaderKnowledgeLink = context_link(
    "AIContextReaderKnowledgeLink", "continuity.ReaderKnowledgeRecord", "reader_knowledge"
)
AIContextCharacterKnowledgeLink = context_link(
    "AIContextCharacterKnowledgeLink", "continuity.CharacterKnowledgeRecord", "character_knowledge"
)
AIContextTimelineLink = context_link("AIContextTimelineLink", "timeline.Timeline", "timeline")
AIContextTimelineEventLink = context_link(
    "AIContextTimelineEventLink", "timeline.TimelineEvent", "timeline_event"
)
AIContextDrawLink = context_link("AIContextDrawLink", "decks.SavedDraw", "draw")
AIContextInterpretationLink = context_link(
    "AIContextInterpretationLink", "decks.DrawInterpretation", "interpretation"
)
AIContextCardLink = context_link("AIContextCardLink", "decks.DeckCard", "card")
AIContextResearchSourceLink = context_link(
    "AIContextResearchSourceLink", "library.ResearchSource", "research_source"
)
AIContextResearchNoteLink = context_link(
    "AIContextResearchNoteLink", "library.ResearchNote", "research_note"
)
AIContextArtworkLink = context_link("AIContextArtworkLink", "library.ArtworkAsset", "artwork")
AIContextCollectionLink = context_link(
    "AIContextCollectionLink", "library.LibraryCollection", "collection"
)
AIContextManuscriptLink = context_link(
    "AIContextManuscriptLink", "publishing.ManuscriptProject", "manuscript"
)


class AICreativeRequest(models.Model):
    STATES = (
        ("queued", "Queued"),
        ("running", "Running"),
        ("ready", "Ready"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ai_creative_requests"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ai_creative_requests"
    )
    context_pack = models.ForeignKey(
        AIContextPack, null=True, blank=True, on_delete=models.PROTECT, related_name="requests"
    )
    task_key = models.CharField(max_length=80)
    instruction = models.TextField()
    state = models.CharField(max_length=16, choices=STATES, default="queued")
    provider = models.CharField(max_length=32)
    model_identifier = models.CharField(max_length=160)
    assembly_version = models.CharField(max_length=32, default="context-v1")
    context_snapshot = models.JSONField(default=dict)
    assembled_context = models.TextField()
    context_hash = models.CharField(max_length=64)
    omission_report = models.JSONField(default=list)
    provider_metadata = models.JSONField(default=dict)
    failure_classification = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "id")
        indexes = [models.Index(fields=("workspace", "state"), name="creative_req_ws_state_idx")]

    def __str__(self):
        return f"{self.task_key} · {self.created_at}"


class AICreativeSuggestion(models.Model):
    STATES = (
        ("ready", "Ready"),
        ("editing", "Editing"),
        ("accepted", "Accepted"),
        ("converted", "Converted"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
        ("stale", "Stale"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ai_creative_suggestions"
    )
    request = models.OneToOneField(
        AICreativeRequest, on_delete=models.PROTECT, related_name="suggestion"
    )
    original_output = models.TextField()
    reviewed_output = models.TextField()
    structured_output = models.JSONField(default=dict)
    state = models.CharField(max_length=16, choices=STATES, default="ready")
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "id")

    def __str__(self):
        return f"Creative Suggestion {self.id}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            original = (
                AICreativeSuggestion.objects.filter(id=self.id)
                .values_list("original_output", flat=True)
                .first()
            )
            if original != self.original_output:
                raise ValidationError("Original provider output is immutable.")
        super().save(*args, **kwargs)


class AIChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ai_chat_sessions"
    )
    title = models.CharField(max_length=240)
    context_pack = models.ForeignKey(
        AIContextPack, null=True, blank=True, on_delete=models.PROTECT, related_name="chat_sessions"
    )
    work = models.ForeignKey(
        "stories.Work",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ai_chat_sessions",
    )
    chapter = models.ForeignKey(
        "stories.Chapter",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ai_chat_sessions",
    )
    status = models.CharField(
        max_length=16, choices=(("active", "Active"), ("archived", "Archived")), default="active"
    )
    pinned_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")

    def __str__(self):
        return self.title


class AIChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(
        max_length=16,
        choices=(("author", "Author"), ("assistant", "Assistant"), ("system", "Context summary")),
    )
    content = models.TextField()
    provenance = models.JSONField(default=dict)
    request = models.ForeignKey(
        AICreativeRequest,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="chat_messages",
    )
    suggestion = models.ForeignKey(
        AICreativeSuggestion,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="chat_messages",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class AICreativeConversion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    suggestion = models.ForeignKey(
        AICreativeSuggestion, on_delete=models.PROTECT, related_name="conversions"
    )
    target_type = models.CharField(max_length=40)
    target_id = models.UUIDField()
    action = models.CharField(max_length=24, default="create")
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "id")

    def __str__(self):
        return f"{self.target_type} {self.target_id}"
