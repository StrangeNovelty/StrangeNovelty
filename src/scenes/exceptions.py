import uuid


class SceneDomainError(Exception):
    """Base class for bounded Scene-domain failures."""


class NotAuthenticated(SceneDomainError):
    pass


class SceneInaccessible(SceneDomainError):
    """The requested Workspace or Scene is unavailable to the actor."""


class InvalidSceneTitle(SceneDomainError):
    pass


class InvalidSceneContent(SceneDomainError):
    pass


class InvalidSceneOrdering(SceneDomainError):
    pass


class LifecycleDisallowsMutation(SceneDomainError):
    pass


class CrossWorkspaceReference(SceneDomainError):
    pass


class DomainIntegrityFailure(SceneDomainError):
    pass


class ImmutableRevisionError(SceneDomainError):
    pass


class ImmutableMutationOperationError(SceneDomainError):
    pass


class OptimisticConcurrencyConflict(SceneDomainError):
    def __init__(self, *, current_revision_id: uuid.UUID, current_scene_version: int):
        super().__init__("The Scene changed after the caller observed it.")
        self.current_revision_id = current_revision_id
        self.current_scene_version = current_scene_version
