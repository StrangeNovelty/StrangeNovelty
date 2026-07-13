import uuid
from collections.abc import Iterable
from typing import cast

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone

from accounts.models import Account
from characters.models import (
    Ability,
    AbilityEvent,
    AbilityPrediction,
    AbilityStage,
    Character,
    CharacterScene,
)
from scenes.models import Scene
from workspaces.models import Workspace
from workspaces.services import get_authorized_workspace


class CharacterDomainError(Exception):
    pass


class CharacterInaccessible(CharacterDomainError):
    pass


def create_character(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    values: dict[str, object],
) -> Character:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            character = Character(workspace=workspace, **values)
            character.full_clean()
            character.save()
    except (IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Character could not be created.") from exc
    return character


def update_character(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    values: dict[str, object],
) -> Character:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            character = cast(
                Character,
                Character.objects.select_for_update().get(id=character_id, workspace=workspace),
            )
            for field, value in values.items():
                setattr(character, field, value)
            character.full_clean()
            character.save()
    except Character.DoesNotExist as exc:
        raise CharacterInaccessible("Character is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Character could not be updated.") from exc
    return character


def link_character_scene(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    scene_id: uuid.UUID,
) -> CharacterScene:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            character = Character.objects.select_for_update().get(
                id=character_id, workspace=workspace
            )
            scene = Scene.objects.get(
                id=scene_id,
                workspace=workspace,
                lifecycle=Scene.Lifecycle.ACTIVE,
            )
            link, _ = CharacterScene.objects.get_or_create(
                workspace=workspace,
                character=character,
                scene=scene,
            )
            link.full_clean()
            Character.objects.filter(id=character.id).update(updated_at=timezone.now())
            return link
    except (Character.DoesNotExist, Scene.DoesNotExist) as exc:
        raise CharacterInaccessible("Character or Scene is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Character and Scene could not be linked.") from exc


def unlink_character_scene(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    scene_id: uuid.UUID,
) -> None:
    workspace = _authorized_workspace(actor, workspace_id)
    with transaction.atomic():
        try:
            character = Character.objects.select_for_update().get(
                id=character_id, workspace=workspace
            )
            link = CharacterScene.objects.get(
                workspace=workspace,
                character=character,
                scene_id=scene_id,
                scene__workspace=workspace,
                scene__lifecycle=Scene.Lifecycle.ACTIVE,
            )
        except (Character.DoesNotExist, CharacterScene.DoesNotExist) as exc:
            raise CharacterInaccessible("Character and Scene link is unavailable.") from exc
        link.delete()
        Character.objects.filter(id=character.id).update(updated_at=timezone.now())


def sync_scene_characters(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    scene_id: uuid.UUID,
    character_ids: Iterable[uuid.UUID],
) -> None:
    workspace = _authorized_workspace(actor, workspace_id)
    requested_ids = set(character_ids)
    with transaction.atomic():
        try:
            scene = Scene.objects.select_for_update().get(id=scene_id, workspace=workspace)
        except Scene.DoesNotExist as exc:
            raise CharacterInaccessible("Scene is unavailable.") from exc
        if scene.lifecycle != Scene.Lifecycle.ACTIVE:
            raise CharacterInaccessible("Scene is unavailable.")
        characters = list(Character.objects.filter(workspace=workspace, id__in=requested_ids))
        if {character.id for character in characters} != requested_ids:
            raise CharacterInaccessible("One or more Characters are unavailable.")
        existing = {
            link.character_id: link
            for link in CharacterScene.objects.filter(workspace=workspace, scene=scene)
        }
        for character_id, link in existing.items():
            if character_id not in requested_ids:
                link.delete()
        now = timezone.now()
        for character in characters:
            if character.id not in existing:
                link = CharacterScene(
                    workspace=workspace,
                    character=character,
                    scene=scene,
                )
                link.full_clean()
                link.save()
        changed_ids = requested_ids.symmetric_difference(existing)
        if changed_ids:
            Character.objects.filter(workspace=workspace, id__in=changed_ids).update(updated_at=now)


def _authorized_workspace(actor: Account | AnonymousUser, workspace_id: uuid.UUID) -> Workspace:
    try:
        return get_authorized_workspace(actor, workspace_id)
    except Http404 as exc:
        raise CharacterInaccessible("Workspace is unavailable.") from exc


def create_ability(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    values: dict[str, object],
) -> Ability:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            character = Character.objects.select_for_update().get(
                id=character_id, workspace=workspace
            )
            ability = Ability(workspace=workspace, character=character, **values)
            ability.full_clean()
            ability.save()
            _touch_character(character.id)
            return ability
    except Character.DoesNotExist as exc:
        raise CharacterInaccessible("Character is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Ability could not be created.") from exc


def update_ability(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    values: dict[str, object],
) -> Ability:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            for field, value in values.items():
                setattr(ability, field, value)
            ability.full_clean()
            ability.save()
            _touch_character(ability.character_id)
            return ability
    except Ability.DoesNotExist as exc:
        raise CharacterInaccessible("Ability is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Ability could not be updated.") from exc


def delete_ability(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
) -> None:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            character_id = ability.character_id
            ability.delete()
            _touch_character(character_id)
    except Ability.DoesNotExist as exc:
        raise CharacterInaccessible("Ability is unavailable.") from exc


def create_ability_stage(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    values: dict[str, object],
) -> AbilityStage:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            if values.get("state") == AbilityStage.State.CURRENT:
                ability.stages.filter(state=AbilityStage.State.CURRENT).update(
                    state=AbilityStage.State.PAST,
                    updated_at=timezone.now(),
                )
            stage = AbilityStage(workspace=workspace, ability=ability, **values)
            stage.full_clean()
            stage.save()
            _touch_ability(ability)
            return stage
    except Ability.DoesNotExist as exc:
        raise CharacterInaccessible("Ability is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Progression stage could not be created.") from exc


def update_ability_stage(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    stage_id: uuid.UUID,
    values: dict[str, object],
) -> AbilityStage:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            stage = AbilityStage.objects.select_for_update().get(
                id=stage_id,
                workspace=workspace,
                ability=ability,
            )
            if values.get("state") == AbilityStage.State.CURRENT:
                ability.stages.filter(state=AbilityStage.State.CURRENT).exclude(id=stage.id).update(
                    state=AbilityStage.State.PAST,
                    updated_at=timezone.now(),
                )
            for field, value in values.items():
                setattr(stage, field, value)
            stage.full_clean()
            stage.save()
            _touch_ability(ability)
            return stage
    except (Ability.DoesNotExist, AbilityStage.DoesNotExist) as exc:
        raise CharacterInaccessible("Progression stage is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Progression stage could not be updated.") from exc


def delete_ability_stage(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    stage_id: uuid.UUID,
) -> None:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            stage = AbilityStage.objects.get(id=stage_id, workspace=workspace, ability=ability)
            stage.delete()
            _touch_ability(ability)
    except (Ability.DoesNotExist, AbilityStage.DoesNotExist) as exc:
        raise CharacterInaccessible("Progression stage is unavailable.") from exc


def create_ability_event(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    values: dict[str, object],
) -> AbilityEvent:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            _validate_event_scene(workspace, values.get("scene"), current_scene_id=None)
            event = AbilityEvent(workspace=workspace, ability=ability, **values)
            event.full_clean()
            event.save()
            _touch_ability(ability)
            return event
    except Ability.DoesNotExist as exc:
        raise CharacterInaccessible("Ability is unavailable.") from exc
    except (Scene.DoesNotExist, IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Progression event could not be created.") from exc


def update_ability_event(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    event_id: uuid.UUID,
    values: dict[str, object],
) -> AbilityEvent:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            event = AbilityEvent.objects.select_for_update().get(
                id=event_id,
                workspace=workspace,
                ability=ability,
            )
            _validate_event_scene(
                workspace,
                values.get("scene"),
                current_scene_id=event.scene_id,
            )
            for field, value in values.items():
                setattr(event, field, value)
            event.full_clean()
            event.save()
            _touch_ability(ability)
            return event
    except (Ability.DoesNotExist, AbilityEvent.DoesNotExist) as exc:
        raise CharacterInaccessible("Progression event is unavailable.") from exc
    except (Scene.DoesNotExist, IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Progression event could not be updated.") from exc


def delete_ability_event(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    event_id: uuid.UUID,
) -> None:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            event = AbilityEvent.objects.get(id=event_id, workspace=workspace, ability=ability)
            event.delete()
            _touch_ability(ability)
    except (Ability.DoesNotExist, AbilityEvent.DoesNotExist) as exc:
        raise CharacterInaccessible("Progression event is unavailable.") from exc


def create_ability_prediction(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    values: dict[str, object],
) -> AbilityPrediction:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            prediction = AbilityPrediction(workspace=workspace, ability=ability, **values)
            prediction.full_clean()
            prediction.save()
            _touch_ability(ability)
            return prediction
    except Ability.DoesNotExist as exc:
        raise CharacterInaccessible("Ability is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Ability prediction could not be created.") from exc


def update_ability_prediction(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    prediction_id: uuid.UUID,
    values: dict[str, object],
) -> AbilityPrediction:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            prediction = AbilityPrediction.objects.select_for_update().get(
                id=prediction_id,
                workspace=workspace,
                ability=ability,
            )
            for field, value in values.items():
                setattr(prediction, field, value)
            prediction.full_clean()
            prediction.save()
            _touch_ability(ability)
            return prediction
    except (Ability.DoesNotExist, AbilityPrediction.DoesNotExist) as exc:
        raise CharacterInaccessible("Ability prediction is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise CharacterDomainError("Ability prediction could not be updated.") from exc


def delete_ability_prediction(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
    prediction_id: uuid.UUID,
) -> None:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            ability = _locked_ability(workspace, character_id, ability_id)
            prediction = AbilityPrediction.objects.get(
                id=prediction_id,
                workspace=workspace,
                ability=ability,
            )
            prediction.delete()
            _touch_ability(ability)
    except (Ability.DoesNotExist, AbilityPrediction.DoesNotExist) as exc:
        raise CharacterInaccessible("Ability prediction is unavailable.") from exc


def _locked_ability(
    workspace: Workspace,
    character_id: uuid.UUID,
    ability_id: uuid.UUID,
) -> Ability:
    return cast(
        Ability,
        Ability.objects.select_for_update().get(
            id=ability_id,
            workspace=workspace,
            character_id=character_id,
            character__workspace=workspace,
        ),
    )


def _validate_event_scene(
    workspace: Workspace,
    scene_value: object,
    *,
    current_scene_id: uuid.UUID | None,
) -> None:
    if scene_value is None:
        return
    if not isinstance(scene_value, Scene):
        raise ValidationError("Linked Scene is invalid.")
    if scene_value.workspace_id != workspace.id:
        raise ValidationError("Linked Scene must belong to this Workspace.")
    if scene_value.id != current_scene_id and scene_value.lifecycle != Scene.Lifecycle.ACTIVE:
        raise ValidationError("Only active Scenes may be newly linked.")


def _touch_ability(ability: Ability) -> None:
    now = timezone.now()
    Ability.objects.filter(id=ability.id, workspace=ability.workspace_id).update(updated_at=now)
    Character.objects.filter(id=ability.character_id, workspace=ability.workspace_id).update(
        updated_at=now
    )


def _touch_character(character_id: uuid.UUID) -> None:
    Character.objects.filter(id=character_id).update(updated_at=timezone.now())
