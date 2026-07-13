import uuid
from collections.abc import Iterable
from typing import cast

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone

from accounts.models import Account
from characters.models import Character, CharacterScene
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
