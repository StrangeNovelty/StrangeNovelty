import hashlib
from dataclasses import dataclass

from django.apps import apps

from ai_assistance.models import AIContextPack

ASSEMBLY_VERSION = "context-v1"
MAX_CONTEXT_CHARACTERS = 60_000


@dataclass(frozen=True, slots=True)
class AssembledContext:
    text: str
    snapshot: dict
    omissions: list[str]
    context_hash: str


def _record_text(record):
    fields = []
    for field in record._meta.fields:
        if field.name in {"id", "workspace", "created_at", "updated_at"} or field.is_relation:
            continue
        value = getattr(record, field.name, "")
        if value not in (None, "", [], {}):
            fields.append(f"{field.verbose_name}: {value}")
    return "\n".join(fields)


def _label(model_name):
    if "Knowledge" in model_name:
        return "Knowledge (distinct from objective truth)"
    if model_name == "Secret":
        return "Objective Truth and Public Belief"
    if model_name == "DeckCard":
        return "Original Deck Card Material"
    if model_name == "DrawInterpretation":
        return "Author Draw Interpretation"
    if model_name in ("ResearchSource", "ResearchNote"):
        return "Research and Citations"
    if model_name in ("ArtworkAsset", "LibraryCollection"):
        return "Visual References"
    if model_name == "ManuscriptProject":
        return "Manuscript Configuration (prose included only through explicit Scene context)"
    return model_name.replace("AIContext", "").replace("Link", "")


def _character_context(record):
    lines = [_record_text(record)]
    abilities = record.abilities.order_by("name")
    if abilities:
        lines.append(
            "Individual Abilities:\n"
            + "\n".join(
                f"- {ability.name}: {ability.description}; limitations: {ability.limitations}; "
                f"costs: {ability.costs}; mastery: {ability.get_mastery_display()}"
                for ability in abilities
            )
        )
    memberships = record.group_memberships.select_related("group").order_by("group__name")
    families = [item for item in memberships if item.group.group_type == "family"]
    groups = [item for item in memberships if item.group.group_type != "family"]
    if families:
        lines.append(
            "Family:\n"
            + "\n".join(f"- {item.group.name}: {item.role}; {item.notes}" for item in families)
        )
    if groups:
        lines.append(
            "Other Groups:\n"
            + "\n".join(f"- {item.group.name}: {item.role}; {item.notes}" for item in groups)
        )
    for membership in record.mechanic_memberships.select_related("template").prefetch_related(
        "template__shared_abilities", "borrowing_log__borrowed_from"
    ):
        lines.append(
            f"Custom Mechanic: {membership.template.name}; "
            f"{membership.template.designation_label}: {membership.designation}; "
            f"rules: {membership.template.borrowing_rules}"
        )
        for ability in membership.template.shared_abilities.all():
            lines.append(
                f"Shared Ability: {ability.name}; {ability.description}; "
                f"limitations: {ability.limitations}"
            )
        for entry in membership.borrowing_log.all():
            lines.append(
                f"Borrowed Ability: {entry.ability_name} from {entry.borrowed_from.name}; "
                f"cost: {entry.cost_or_damage}; duration: {entry.duration}; "
                f"recovery: {entry.recovery}; consequence: {entry.lasting_consequence}; "
                f"continuity: {entry.continuity_implications}"
            )
    return "\n".join(lines)


def assemble_context(pack: AIContextPack | None, *, task, instruction, chat_messages=()):
    sections = [("Task", f"{task.title}\n{task.description}"), ("Author Request", instruction)]
    sources = []
    omissions = []
    if pack:
        sections.extend(
            (
                ("Author Instructions", pack.author_instructions),
                (
                    "Voice Guidance",
                    _record_text(pack.voice_profile) if pack.voice_profile_id else "",
                ),
                (
                    "Tone and Genre",
                    f"Tone: {pack.tone_guidance}\nGenre: {pack.genre_guidance}\n"
                    f"Adult-audience guidance: {pack.adult_audience_guidance}",
                ),
                ("Exclusions", pack.exclusions),
            )
        )
        for record in (pack.work, pack.chapter):
            if record:
                sections.append((record.__class__.__name__, _record_text(record)))
                sources.append(_source(record))
        for model in apps.get_models():
            if (
                model.__module__ != "ai_assistance.models"
                or not model.__name__.startswith("AIContext")
                or not model.__name__.endswith("Link")
            ):
                continue
            for link in model.objects.filter(pack=pack).order_by("priority", "order", "id"):
                field = next(
                    field
                    for field in model._meta.fields
                    if field.is_relation and field.name != "pack"
                )
                record = getattr(link, field.name)
                content = _record_text(record)
                if record.__class__.__name__ == "Character":
                    content = _character_context(record)
                if record.__class__.__name__ == "ResearchSource":
                    content += (
                        "\nSelected extracted text (unverified unless author-reviewed): "
                        f"{record.extracted_text[:4000]}"
                    )
                if record.__class__.__name__ == "Scene" and record.current_revision_id:
                    content += (
                        f"\nrevision identity: {record.current_revision_id}"
                        f"\nrevision content:\n{record.current_revision.content}"
                    )
                state = getattr(record, "status", "") or getattr(record, "canon_state", "")
                if state in ("speculative", "disputed", "deprecated", "archived"):
                    content = f"STATE: {state.upper()}\n{content}"
                sections.append(
                    (
                        _label(record.__class__.__name__),
                        f"Role: {link.role}\nPriority: {link.priority}\n{content}",
                    )
                )
                sources.append(_source(record))
    if chat_messages:
        sections.append(
            (
                "Conversation History",
                "\n".join(f"{message.role}: {message.content}" for message in chat_messages),
            )
        )
    sections.append(
        ("Requested Output Format", "\n".join(f"- {name}" for name in task.output_sections))
    )
    chunks = []
    used = 0
    for label, content in sections:
        if not content:
            continue
        chunk = f"## {label}\n{content.strip()}\n"
        if used + len(chunk) > MAX_CONTEXT_CHARACTERS:
            remaining = MAX_CONTEXT_CHARACTERS - used
            if remaining > 200:
                chunks.append(chunk[:remaining] + "\n[TRUNCATED]")
            omissions.append(f"{label} was truncated or omitted at the context boundary.")
            break
        chunks.append(chunk)
        used += len(chunk)
    text = "\n".join(chunks)
    snapshot = {
        "assembly_version": ASSEMBLY_VERSION,
        "pack_id": str(pack.id) if pack else None,
        "pack_updated_at": pack.updated_at.isoformat() if pack else None,
        "sources": sources,
        "task_key": task.key,
    }
    digest = hashlib.sha256(text.encode()).hexdigest()
    return AssembledContext(text, snapshot, omissions, digest)


def _source(record):
    value = {"type": record.__class__.__name__, "id": str(record.pk)}
    if hasattr(record, "updated_at"):
        value["updated_at"] = record.updated_at.isoformat()
    if record.__class__.__name__ == "Scene":
        value["revision_id"] = (
            str(record.current_revision_id) if record.current_revision_id else None
        )
        value["scene_version"] = record.version
    return value


def snapshot_is_stale(snapshot, workspace):
    for source in snapshot.get("sources", []):
        model = next(
            (model for model in apps.get_models() if model.__name__ == source["type"]), None
        )
        if not model:
            continue
        record = model.objects.filter(id=source["id"]).first()
        if not record:
            return True
        if getattr(record, "workspace_id", workspace.id) != workspace.id:
            return True
        if source.get("revision_id") and str(record.current_revision_id) != source["revision_id"]:
            return True
        if (
            source.get("updated_at")
            and hasattr(record, "updated_at")
            and record.updated_at.isoformat() != source["updated_at"]
        ):
            return True
    return False
