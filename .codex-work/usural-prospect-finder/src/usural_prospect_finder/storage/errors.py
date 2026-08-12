"""Storage-neutral repository exceptions."""


class RepositoryError(Exception):
    """Base error exposed by persistence adapters."""


class RepositoryConflictError(RepositoryError):
    """A uniqueness or identity constraint was violated."""
