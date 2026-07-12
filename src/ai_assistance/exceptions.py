class AIAssistanceError(Exception):
    pass


class AIRequestConflict(AIAssistanceError):
    pass


class AIRequestUnavailable(AIAssistanceError):
    pass


class StaleSuggestion(AIAssistanceError):
    pass
