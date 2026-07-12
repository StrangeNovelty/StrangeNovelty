class JobError(Exception):
    """Base bounded job error."""


class InvalidJobTransition(JobError):
    pass


class StaleJobLease(JobError):
    pass


class IdempotencyConflict(JobError):
    pass


class UnknownJobType(JobError):
    pass


class ImmutableJobRecord(JobError):
    pass


class RetryableJobError(JobError):
    pass


class TerminalJobError(JobError):
    pass


class AmbiguousJobOutcome(JobError):
    pass
