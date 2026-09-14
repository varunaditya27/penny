class UserNotFoundError(Exception):
    """Raised when a requested user ID is not found in persistent storage."""
    pass
