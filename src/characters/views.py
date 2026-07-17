import uuid
from typing import cast

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, F, Prefetch, Q
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from characters.forms import (
    AbilityEventForm,
    AbilityForm,
    AbilityPredictionForm,
    AbilityStageForm,
    CharacterCreateForm,
    CharacterForm,
    CharacterGroupForm,
    CharacterGroupSearchForm,
    CharacterListSearchForm,
    CharacterRelationshipForm,
    CharacterSceneLinkForm,
    GroupMembershipForm,
    GroupRelationshipForm,
    SceneCharacterSelectorForm,
)
from characters.models import (
    Ability,
    AbilityEvent,
    AbilityPrediction,
    AbilityStage,
    Character,
    CharacterGroup,
    CharacterRelationship,
    GroupMembership,
    GroupRelationship,
)
from characters.search import search_character_groups, search_characters
from characters.services import (
    CharacterDomainError,
    CharacterInaccessible,
    create_ability,
    create_ability_event,
    create_ability_prediction,
    create_ability_stage,
    create_character,
    create_character_group,
    create_character_relationship,
    create_group_membership,
    delete_ability,
    delete_ability_event,
    delete_ability_prediction,
    delete_ability_stage,
    delete_character_group,
    delete_character_relationship,
    delete_group_membership,
    link_character_scene,
    sync_scene_characters,
    unlink_character_scene,
    update_ability,
    update_ability_event,
    update_ability_prediction,
    update_ability_stage,
    update_character,
    update_character_group,
    update_character_relationship,
    update_group_membership,
)
from scenes.models import Scene
from workspaces.models import Workspace
from workspaces.services import resolve_owner_workspace


def _see_other(location: str) -> HttpResponseRedirect:
    response = HttpResponseRedirect(location)
    response.status_code = 303
    return response


def _request_workspace(request: HttpRequest) -> Workspace:
    return resolve_owner_workspace(request.user)


def _authorized_character(request: HttpRequest, character_id: uuid.UUID) -> Character:
    workspace = _request_workspace(request)
    try:
        return cast(
            Character,
            Character.objects.prefetch_related("scenes").get(id=character_id, workspace=workspace),
        )
    except Character.DoesNotExist as exc:
        raise Http404("Character is unavailable.") from exc


def _detail_context(
    *, request: HttpRequest, character: Character, form: CharacterForm
) -> dict[str, object]:
    workspace = _request_workspace(request)
    scene_links = character.scene_links.select_related("scene").exclude(
        scene__lifecycle=Scene.Lifecycle.TRASHED
    )
    abilities = list(
        Ability.objects.filter(workspace=workspace, character=character)
        .prefetch_related(
            Prefetch(
                "stages",
                queryset=AbilityStage.objects.filter(state=AbilityStage.State.CURRENT),
                to_attr="current_stages",
            )
        )
        .order_by("name", "id")
    )
    relationships = list(
        CharacterRelationship.objects.filter(workspace=workspace)
        .filter(Q(source=character) | Q(target=character))
        .select_related("source", "target")
        .order_by("-updated_at", "id")
    )
    relationship_cards = [
        {
            "relationship": relationship,
            "other": (
                relationship.target
                if relationship.source_id == character.id
                else relationship.source
            ),
            "perspective": (
                relationship.source_perspective
                if relationship.source_id == character.id
                else relationship.target_perspective
            ),
        }
        for relationship in relationships
    ]
    memberships = list(
        GroupMembership.objects.filter(workspace=workspace, character=character)
        .select_related("group")
        .order_by("group__name", "id")
    )
    from worldbuilding.models import (
        CodexCharacterLink,
        CreatureCharacterLink,
        ItemCharacterLink,
        LocationCharacterLink,
    )

    return {
        "character": character,
        "form": form,
        "scene_links": scene_links,
        "scene_link_form": CharacterSceneLinkForm(workspace=workspace, character=character),
        "abilities": abilities,
        "ability_count": len(abilities),
        "active_ability_count": sum(
            ability.status == Ability.Status.ACTIVE for ability in abilities
        ),
        "current_stage_count": sum(bool(ability.current_stages) for ability in abilities),
        "relationship_cards": relationship_cards,
        "relationship_count": len(relationship_cards),
        "memberships": memberships,
        "group_count": len(memberships),
        "world_location_links": LocationCharacterLink.objects.filter(
            character=character
        ).select_related("location"),
        "world_item_links": ItemCharacterLink.objects.filter(character=character).select_related(
            "item"
        ),
        "world_creature_links": CreatureCharacterLink.objects.filter(
            character=character
        ).select_related("creature"),
        "world_codex_links": CodexCharacterLink.objects.filter(character=character).select_related(
            "codex"
        ),
    }


def _decorate_connection_counts(
    workspace: Workspace,
    characters: list[Character],
) -> None:
    character_ids = {character.id for character in characters}
    relationship_counts = dict.fromkeys(character_ids, 0)
    for source_id, target_id in CharacterRelationship.objects.filter(
        workspace=workspace
    ).values_list("source_id", "target_id"):
        if source_id in relationship_counts:
            relationship_counts[source_id] += 1
        if target_id in relationship_counts:
            relationship_counts[target_id] += 1
    membership_counts = {
        row["character_id"]: row["count"]
        for row in GroupMembership.objects.filter(
            workspace=workspace, character_id__in=character_ids
        )
        .values("character_id")
        .annotate(count=Count("id"))
    }
    for character in characters:
        relationship_count = relationship_counts[character.id]
        group_count = membership_counts.get(character.id, 0)
        character.relationship_count_display = relationship_count
        character.group_count_display = group_count
        character.is_unconnected = relationship_count == 0 and group_count == 0


def _authorized_ability(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
) -> Ability:
    workspace = _request_workspace(request)
    try:
        return cast(
            Ability,
            Ability.objects.select_related("character").get(
                id=ability_id,
                workspace=workspace,
                character_id=character_id,
                character__workspace=workspace,
            ),
        )
    except Ability.DoesNotExist as exc:
        raise Http404("Ability is unavailable.") from exc


def _ability_detail_context(*, ability: Ability) -> dict[str, object]:
    stages = ability.stages.order_by("order", "id")
    events = ability.events.select_related("scene").order_by(
        F("event_date").desc(nulls_last=True), "-created_at", "-id"
    )
    return {
        "ability": ability,
        "character": ability.character,
        "stages": stages,
        "current_stage": stages.filter(state=AbilityStage.State.CURRENT).first(),
        "events": events,
        "predictions": ability.predictions.order_by("-updated_at", "-id"),
    }


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_list(request: HttpRequest) -> HttpResponse:
    workspace = _request_workspace(request)
    form = CharacterListSearchForm(request.POST or None)
    searched = request.method == "POST"
    if searched and form.is_valid():
        characters = [
            result.character
            for result in search_characters(
                actor=request.user,
                workspace_id=workspace.id,
                query_text=form.cleaned_data["query"],
                limit=50,
            )
        ]
    else:
        characters = list(Character.objects.filter(workspace=workspace).order_by("-updated_at"))
    _decorate_connection_counts(workspace, characters)
    status = 422 if searched and not form.is_valid() else 200
    return render(
        request,
        "characters/list.html",
        {"characters": characters, "form": form, "searched": searched},
        status=status,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_create(request: HttpRequest) -> HttpResponse:
    workspace = _request_workspace(request)
    form = CharacterCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            character = create_character(
                actor=request.user,
                workspace_id=workspace.id,
                values=form.cleaned_data,
            )
        except CharacterDomainError:
            form.add_error(None, "The Character could not be created.")
        else:
            return _see_other(reverse("character-detail", kwargs={"character_id": character.id}))
    status = 422 if request.method == "POST" else 200
    return render(request, "characters/create.html", {"form": form}, status=status)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_detail(request: HttpRequest, character_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    character = _authorized_character(request, character_id)
    form = CharacterForm(request.POST or None, instance=character)
    if request.method == "POST" and form.is_valid():
        try:
            character = update_character(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character.id,
                values=form.cleaned_data,
            )
        except CharacterInaccessible as exc:
            raise Http404("Character is unavailable.") from exc
        except CharacterDomainError:
            form.add_error(None, "The Character could not be saved.")
        else:
            return _see_other(reverse("character-detail", kwargs={"character_id": character.id}))
    status = 422 if request.method == "POST" else 200
    return render(
        request,
        "characters/detail.html",
        _detail_context(request=request, character=character, form=form),
        status=status,
    )


@never_cache
@login_required
@require_POST
def character_scene_link(request: HttpRequest, character_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    character = _authorized_character(request, character_id)
    form = CharacterSceneLinkForm(request.POST, workspace=workspace, character=character)
    if not form.is_valid():
        raise Http404("Scene is unavailable.")
    try:
        link_character_scene(
            actor=request.user,
            workspace_id=workspace.id,
            character_id=character.id,
            scene_id=form.cleaned_data["scene"].id,
        )
    except CharacterDomainError as exc:
        raise Http404("Scene is unavailable.") from exc
    return _see_other(reverse("character-detail", kwargs={"character_id": character.id}))


@never_cache
@login_required
@require_POST
def character_scene_unlink(
    request: HttpRequest, character_id: uuid.UUID, scene_id: uuid.UUID
) -> HttpResponse:
    workspace = _request_workspace(request)
    try:
        unlink_character_scene(
            actor=request.user,
            workspace_id=workspace.id,
            character_id=character_id,
            scene_id=scene_id,
        )
    except CharacterDomainError as exc:
        raise Http404("Character and Scene link is unavailable.") from exc
    return _see_other(reverse("character-detail", kwargs={"character_id": character_id}))


@never_cache
@login_required
@require_POST
def scene_characters_update(request: HttpRequest, scene_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    try:
        scene = Scene.objects.get(id=scene_id, workspace=workspace)
    except Scene.DoesNotExist as exc:
        raise Http404("Scene is unavailable.") from exc
    if scene.lifecycle != Scene.Lifecycle.ACTIVE:
        raise Http404("Scene is unavailable.")
    form = SceneCharacterSelectorForm(request.POST, workspace=workspace)
    if not form.is_valid():
        raise Http404("One or more Characters are unavailable.")
    try:
        sync_scene_characters(
            actor=request.user,
            workspace_id=workspace.id,
            scene_id=scene.id,
            character_ids=(character.id for character in form.cleaned_data["characters"]),
        )
    except CharacterDomainError as exc:
        raise Http404("Characters could not be updated.") from exc
    return _see_other(reverse("scene-editor", kwargs={"scene_id": scene.id}))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def ability_create(request: HttpRequest, character_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    character = _authorized_character(request, character_id)
    form = AbilityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            ability = create_ability(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character.id,
                values=form.cleaned_data,
            )
        except CharacterInaccessible as exc:
            raise Http404("Character is unavailable.") from exc
        except CharacterDomainError:
            form.add_error(None, "The Ability could not be created.")
        else:
            return _see_other(_ability_url(character.id, ability.id))
    return render(
        request,
        "characters/ability_form.html",
        {"character": character, "form": form, "creating": True},
        status=422 if request.method == "POST" else 200,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def ability_detail(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    ability = _authorized_ability(request, character_id, ability_id)
    form = AbilityForm(request.POST or None, instance=ability)
    if request.method == "POST" and form.is_valid():
        try:
            ability = update_ability(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character_id,
                ability_id=ability.id,
                values=form.cleaned_data,
            )
        except CharacterInaccessible as exc:
            raise Http404("Ability is unavailable.") from exc
        except CharacterDomainError:
            form.add_error(None, "The Ability could not be saved.")
        else:
            return _see_other(_ability_url(character_id, ability.id))
    context = _ability_detail_context(ability=ability)
    context["form"] = form
    return render(
        request,
        "characters/ability_detail.html",
        context,
        status=422 if request.method == "POST" else 200,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def ability_delete_view(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    ability = _authorized_ability(request, character_id, ability_id)
    if request.method == "POST":
        try:
            delete_ability(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character_id,
                ability_id=ability.id,
            )
        except CharacterDomainError as exc:
            raise Http404("Ability is unavailable.") from exc
        return _see_other(reverse("character-detail", kwargs={"character_id": character_id}))
    return render(
        request,
        "characters/ability_delete.html",
        {"ability": ability, "character": ability.character},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def ability_stage_create(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    ability = _authorized_ability(request, character_id, ability_id)
    form = AbilityStageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_ability_stage(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character_id,
                ability_id=ability.id,
                values=form.cleaned_data,
            )
        except CharacterDomainError:
            form.add_error(None, "The progression stage could not be created.")
        else:
            return _see_other(_ability_url(character_id, ability.id))
    return _render_record_form(
        request,
        ability=ability,
        form=form,
        eyebrow="Progression stage",
        heading="Add a stage",
        support="Describe one established or possible step in this Ability’s development.",
        submit_label="Add stage",
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def ability_stage_edit(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    stage_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    ability = _authorized_ability(request, character_id, ability_id)
    stage = _authorized_stage(workspace, ability, stage_id)
    form = AbilityStageForm(request.POST or None, instance=stage)
    if request.method == "POST" and form.is_valid():
        try:
            update_ability_stage(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character_id,
                ability_id=ability.id,
                stage_id=stage.id,
                values=form.cleaned_data,
            )
        except CharacterDomainError:
            form.add_error(None, "The progression stage could not be saved.")
        else:
            return _see_other(_ability_url(character_id, ability.id))
    return _render_record_form(
        request,
        ability=ability,
        form=form,
        eyebrow="Progression stage",
        heading=f"Edit {stage.name}",
        support="Refine this step without changing the established order of other stages.",
        submit_label="Save stage",
    )


@never_cache
@login_required
@require_POST
def ability_stage_delete(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    stage_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    try:
        delete_ability_stage(
            actor=request.user,
            workspace_id=workspace.id,
            character_id=character_id,
            ability_id=ability_id,
            stage_id=stage_id,
        )
    except CharacterDomainError as exc:
        raise Http404("Progression stage is unavailable.") from exc
    return _see_other(_ability_url(character_id, ability_id))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def ability_event_create(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    ability = _authorized_ability(request, character_id, ability_id)
    form = AbilityEventForm(request.POST or None, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        try:
            create_ability_event(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character_id,
                ability_id=ability.id,
                values=form.cleaned_data,
            )
        except CharacterDomainError:
            form.add_error(None, "The progression event could not be created.")
        else:
            return _see_other(_ability_url(character_id, ability.id))
    return _render_record_form(
        request,
        ability=ability,
        form=form,
        eyebrow="Development history",
        heading="Add a progression event",
        support="Record the moment that changed what this Ability could do or cost.",
        submit_label="Add event",
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def ability_event_edit(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    event_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    ability = _authorized_ability(request, character_id, ability_id)
    event = _authorized_event(workspace, ability, event_id)
    form = AbilityEventForm(request.POST or None, workspace=workspace, instance=event)
    if request.method == "POST" and form.is_valid():
        try:
            update_ability_event(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character_id,
                ability_id=ability.id,
                event_id=event.id,
                values=form.cleaned_data,
            )
        except CharacterDomainError:
            form.add_error(None, "The progression event could not be saved.")
        else:
            return _see_other(_ability_url(character_id, ability.id))
    return _render_record_form(
        request,
        ability=ability,
        form=form,
        eyebrow="Development history",
        heading=f"Edit {event.title}",
        support=(
            "Keep the history factual to the story; future possibilities belong in Predictions."
        ),
        submit_label="Save event",
    )


@never_cache
@login_required
@require_POST
def ability_event_delete(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    event_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    try:
        delete_ability_event(
            actor=request.user,
            workspace_id=workspace.id,
            character_id=character_id,
            ability_id=ability_id,
            event_id=event_id,
        )
    except CharacterDomainError as exc:
        raise Http404("Progression event is unavailable.") from exc
    return _see_other(_ability_url(character_id, ability_id))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def ability_prediction_create(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    ability = _authorized_ability(request, character_id, ability_id)
    form = AbilityPredictionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_ability_prediction(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character_id,
                ability_id=ability.id,
                values=form.cleaned_data,
            )
        except CharacterDomainError:
            form.add_error(None, "The prediction could not be created.")
        else:
            return _see_other(_ability_url(character_id, ability.id))
    return _render_record_form(
        request,
        ability=ability,
        form=form,
        eyebrow="Speculative development",
        heading="Add a prediction",
        support=(
            "Explore a private future possibility without treating it as established story truth."
        ),
        submit_label="Add prediction",
        speculative=True,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def ability_prediction_edit(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    prediction_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    ability = _authorized_ability(request, character_id, ability_id)
    prediction = _authorized_prediction(workspace, ability, prediction_id)
    form = AbilityPredictionForm(request.POST or None, instance=prediction)
    if request.method == "POST" and form.is_valid():
        try:
            update_ability_prediction(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character_id,
                ability_id=ability.id,
                prediction_id=prediction.id,
                values=form.cleaned_data,
            )
        except CharacterDomainError:
            form.add_error(None, "The prediction could not be saved.")
        else:
            return _see_other(_ability_url(character_id, ability.id))
    return _render_record_form(
        request,
        ability=ability,
        form=form,
        eyebrow="Speculative development",
        heading=f"Edit {prediction.title}",
        support="Track how this possibility evolved without rewriting established history.",
        submit_label="Save prediction",
        speculative=True,
    )


@never_cache
@login_required
@require_POST
def ability_prediction_delete(
    request: HttpRequest,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    prediction_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    try:
        delete_ability_prediction(
            actor=request.user,
            workspace_id=workspace.id,
            character_id=character_id,
            ability_id=ability_id,
            prediction_id=prediction_id,
        )
    except CharacterDomainError as exc:
        raise Http404("Ability prediction is unavailable.") from exc
    return _see_other(_ability_url(character_id, ability_id))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_relationship_create(
    request: HttpRequest,
    character_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    character = _authorized_character(request, character_id)
    form = CharacterRelationshipForm(
        request.POST or None,
        workspace=workspace,
        current_character=character,
    )
    if request.method == "POST" and form.is_valid():
        try:
            create_character_relationship(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character.id,
                values=form.cleaned_data,
            )
        except CharacterInaccessible as exc:
            raise Http404("Relationship Character is unavailable.") from exc
        except CharacterDomainError:
            form.add_error(
                None,
                "This Character pair already has a relationship or could not be linked.",
            )
        else:
            return _see_other(reverse("character-detail", kwargs={"character_id": character.id}))
    return _render_relationship_form(
        request,
        character=character,
        form=form,
        heading="Add a relationship",
        submit_label="Add relationship",
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_relationship_edit(
    request: HttpRequest,
    character_id: uuid.UUID,
    relationship_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    character = _authorized_character(request, character_id)
    relationship = _authorized_relationship(workspace, character, relationship_id)
    form = CharacterRelationshipForm(
        request.POST or None,
        workspace=workspace,
        current_character=character,
        relationship=relationship,
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_character_relationship(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character.id,
                relationship_id=relationship.id,
                values=form.cleaned_data,
            )
        except CharacterInaccessible as exc:
            raise Http404("Character relationship is unavailable.") from exc
        except CharacterDomainError:
            form.add_error(
                None,
                "This Character pair already has a relationship or could not be updated.",
            )
        else:
            return _see_other(reverse("character-detail", kwargs={"character_id": character.id}))
    return _render_relationship_form(
        request,
        character=character,
        form=form,
        heading="Edit relationship",
        submit_label="Save relationship",
        relationship=relationship,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_relationship_delete_view(
    request: HttpRequest,
    character_id: uuid.UUID,
    relationship_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    character = _authorized_character(request, character_id)
    relationship = _authorized_relationship(workspace, character, relationship_id)
    other = relationship.target if relationship.source_id == character.id else relationship.source
    if request.method == "POST":
        try:
            delete_character_relationship(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character.id,
                relationship_id=relationship.id,
            )
        except CharacterDomainError as exc:
            raise Http404("Character relationship is unavailable.") from exc
        return _see_other(reverse("character-detail", kwargs={"character_id": character.id}))
    return render(
        request,
        "characters/relationship_delete.html",
        {"character": character, "relationship": relationship, "other": other},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_group_list(request: HttpRequest) -> HttpResponse:
    workspace = _request_workspace(request)
    form = CharacterGroupSearchForm(request.POST or None)
    searched = request.method == "POST"
    if searched and form.is_valid():
        groups = [
            result.group
            for result in search_character_groups(
                actor=request.user,
                workspace_id=workspace.id,
                query_text=form.cleaned_data["query"],
                limit=50,
            )
        ]
    else:
        groups = list(
            CharacterGroup.objects.filter(workspace=workspace)
            .annotate(member_count=Count("memberships"))
            .order_by("-updated_at", "id")
        )
    if searched:
        group_ids = [group.id for group in groups]
        counts = {
            row["group_id"]: row["count"]
            for row in GroupMembership.objects.filter(workspace=workspace, group_id__in=group_ids)
            .values("group_id")
            .annotate(count=Count("id"))
        }
        for group in groups:
            group.member_count = counts.get(group.id, 0)
    return render(
        request,
        "characters/group_list.html",
        {"groups": groups, "form": form, "searched": searched},
        status=422 if searched and not form.is_valid() else 200,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_group_create(request: HttpRequest) -> HttpResponse:
    workspace = _request_workspace(request)
    form = CharacterGroupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            group = create_character_group(
                actor=request.user,
                workspace_id=workspace.id,
                values=form.cleaned_data,
            )
        except CharacterDomainError:
            form.add_error(None, "The Group could not be created.")
        else:
            return _see_other(reverse("character-group-detail", kwargs={"group_id": group.id}))
    return render(
        request,
        "characters/group_form.html",
        {"form": form, "creating": True},
        status=422 if request.method == "POST" else 200,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_group_detail(request: HttpRequest, group_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    group = _authorized_group(workspace, group_id)
    form = CharacterGroupForm(request.POST or None, instance=group)
    if request.method == "POST" and form.is_valid():
        try:
            group = update_character_group(
                actor=request.user,
                workspace_id=workspace.id,
                group_id=group.id,
                values=form.cleaned_data,
            )
        except CharacterInaccessible as exc:
            raise Http404("Character Group is unavailable.") from exc
        except CharacterDomainError:
            form.add_error(None, "The Group could not be saved.")
        else:
            return _see_other(reverse("character-group-detail", kwargs={"group_id": group.id}))
    memberships = group.memberships.select_related("character").order_by("character__name", "id")
    group_relationships = (
        GroupRelationship.objects.filter(workspace=workspace)
        .filter(Q(source=group) | Q(target=group))
        .select_related("source", "target")
    )
    return render(
        request,
        "characters/group_detail.html",
        {
            "group": group,
            "form": form,
            "memberships": memberships,
            "group_relationships": group_relationships,
            "group_relationship_form": GroupRelationshipForm(workspace=workspace, group=group),
        },
        status=422 if request.method == "POST" else 200,
    )


@never_cache
@login_required
@require_POST
def group_relationship_create(request: HttpRequest, group_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    group = _authorized_group(workspace, group_id)
    form = GroupRelationshipForm(request.POST, workspace=workspace, group=group)
    if not form.is_valid():
        raise Http404("Group relationship is unavailable.")
    other = form.cleaned_data["other_group"]
    source, target = sorted((group, other), key=lambda item: item.id)
    current_is_source = source.id == group.id
    relationship = GroupRelationship(
        workspace=workspace,
        source=source,
        target=target,
        relationship_type=form.cleaned_data["relationship_type"],
        summary=form.cleaned_data["summary"],
        notes=form.cleaned_data["notes"],
        source_perspective=form.cleaned_data["current_perspective"]
        if current_is_source
        else form.cleaned_data["other_perspective"],
        target_perspective=form.cleaned_data["other_perspective"]
        if current_is_source
        else form.cleaned_data["current_perspective"],
    )
    try:
        relationship.full_clean()
        relationship.save()
    except ValidationError as exc:
        raise Http404("Group relationship is unavailable.") from exc
    return _see_other(reverse("character-group-detail", kwargs={"group_id": group.id}))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_group_delete_view(request: HttpRequest, group_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    group = _authorized_group(workspace, group_id)
    if request.method == "POST":
        try:
            delete_character_group(
                actor=request.user,
                workspace_id=workspace.id,
                group_id=group.id,
            )
        except CharacterDomainError as exc:
            raise Http404("Character Group is unavailable.") from exc
        return _see_other(reverse("character-group-list"))
    return render(
        request,
        "characters/group_delete.html",
        {"group": group, "membership_count": group.memberships.count()},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def group_membership_create(request: HttpRequest, group_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    group = _authorized_group(workspace, group_id)
    form = GroupMembershipForm(request.POST or None, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        try:
            create_group_membership(
                actor=request.user,
                workspace_id=workspace.id,
                group_id=group.id,
                values=form.cleaned_data,
            )
        except CharacterInaccessible as exc:
            raise Http404("Group or Character is unavailable.") from exc
        except CharacterDomainError:
            form.add_error(None, "This Character is already a member or could not be added.")
        else:
            return _see_other(reverse("character-group-detail", kwargs={"group_id": group.id}))
    return _render_membership_form(
        request,
        group=group,
        form=form,
        heading="Add a Group member",
        submit_label="Add member",
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def group_membership_edit(
    request: HttpRequest,
    group_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    group = _authorized_group(workspace, group_id)
    membership = _authorized_membership(workspace, group, membership_id)
    form = GroupMembershipForm(request.POST or None, workspace=workspace, instance=membership)
    if request.method == "POST" and form.is_valid():
        try:
            update_group_membership(
                actor=request.user,
                workspace_id=workspace.id,
                group_id=group.id,
                membership_id=membership.id,
                values=form.cleaned_data,
            )
        except CharacterInaccessible as exc:
            raise Http404("Group membership is unavailable.") from exc
        except CharacterDomainError:
            form.add_error(None, "This Character is already a member or could not be updated.")
        else:
            return _see_other(reverse("character-group-detail", kwargs={"group_id": group.id}))
    return _render_membership_form(
        request,
        group=group,
        form=form,
        heading="Edit Group membership",
        submit_label="Save membership",
        membership=membership,
    )


@never_cache
@login_required
@require_POST
def group_membership_delete(
    request: HttpRequest,
    group_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> HttpResponse:
    workspace = _request_workspace(request)
    try:
        delete_group_membership(
            actor=request.user,
            workspace_id=workspace.id,
            group_id=group_id,
            membership_id=membership_id,
        )
    except CharacterDomainError as exc:
        raise Http404("Group membership is unavailable.") from exc
    return _see_other(reverse("character-group-detail", kwargs={"group_id": group_id}))


def _authorized_relationship(
    workspace: Workspace,
    character: Character,
    relationship_id: uuid.UUID,
) -> CharacterRelationship:
    try:
        return cast(
            CharacterRelationship,
            CharacterRelationship.objects.select_related("source", "target").get(
                Q(source=character) | Q(target=character),
                id=relationship_id,
                workspace=workspace,
            ),
        )
    except CharacterRelationship.DoesNotExist as exc:
        raise Http404("Character relationship is unavailable.") from exc


def _authorized_group(workspace: Workspace, group_id: uuid.UUID) -> CharacterGroup:
    try:
        return cast(
            CharacterGroup,
            CharacterGroup.objects.get(id=group_id, workspace=workspace),
        )
    except CharacterGroup.DoesNotExist as exc:
        raise Http404("Character Group is unavailable.") from exc


def _authorized_membership(
    workspace: Workspace,
    group: CharacterGroup,
    membership_id: uuid.UUID,
) -> GroupMembership:
    try:
        return cast(
            GroupMembership,
            GroupMembership.objects.select_related("character").get(
                id=membership_id,
                workspace=workspace,
                group=group,
            ),
        )
    except GroupMembership.DoesNotExist as exc:
        raise Http404("Group membership is unavailable.") from exc


def _render_relationship_form(
    request: HttpRequest,
    *,
    character: Character,
    form: CharacterRelationshipForm,
    heading: str,
    submit_label: str,
    relationship: CharacterRelationship | None = None,
) -> HttpResponse:
    return render(
        request,
        "characters/relationship_form.html",
        {
            "character": character,
            "form": form,
            "heading": heading,
            "submit_label": submit_label,
            "relationship": relationship,
        },
        status=422 if request.method == "POST" else 200,
    )


def _render_membership_form(
    request: HttpRequest,
    *,
    group: CharacterGroup,
    form: GroupMembershipForm,
    heading: str,
    submit_label: str,
    membership: GroupMembership | None = None,
) -> HttpResponse:
    return render(
        request,
        "characters/membership_form.html",
        {
            "group": group,
            "form": form,
            "heading": heading,
            "submit_label": submit_label,
            "membership": membership,
        },
        status=422 if request.method == "POST" else 200,
    )


def _authorized_stage(
    workspace: Workspace,
    ability: Ability,
    stage_id: uuid.UUID,
) -> AbilityStage:
    try:
        return cast(
            AbilityStage,
            AbilityStage.objects.get(id=stage_id, workspace=workspace, ability=ability),
        )
    except AbilityStage.DoesNotExist as exc:
        raise Http404("Progression stage is unavailable.") from exc


def _authorized_event(
    workspace: Workspace,
    ability: Ability,
    event_id: uuid.UUID,
) -> AbilityEvent:
    try:
        return cast(
            AbilityEvent,
            AbilityEvent.objects.get(id=event_id, workspace=workspace, ability=ability),
        )
    except AbilityEvent.DoesNotExist as exc:
        raise Http404("Progression event is unavailable.") from exc


def _authorized_prediction(
    workspace: Workspace,
    ability: Ability,
    prediction_id: uuid.UUID,
) -> AbilityPrediction:
    try:
        return cast(
            AbilityPrediction,
            AbilityPrediction.objects.get(
                id=prediction_id,
                workspace=workspace,
                ability=ability,
            ),
        )
    except AbilityPrediction.DoesNotExist as exc:
        raise Http404("Ability prediction is unavailable.") from exc


def _render_record_form(
    request: HttpRequest,
    *,
    ability: Ability,
    form: AbilityStageForm | AbilityEventForm | AbilityPredictionForm,
    eyebrow: str,
    heading: str,
    support: str,
    submit_label: str,
    speculative: bool = False,
) -> HttpResponse:
    return render(
        request,
        "characters/ability_record_form.html",
        {
            "ability": ability,
            "character": ability.character,
            "form": form,
            "eyebrow": eyebrow,
            "heading": heading,
            "support": support,
            "submit_label": submit_label,
            "speculative": speculative,
        },
        status=422 if request.method == "POST" else 200,
    )


def _ability_url(character_id: uuid.UUID, ability_id: uuid.UUID) -> str:
    return reverse(
        "ability-detail",
        kwargs={"character_id": character_id, "ability_id": ability_id},
    )
