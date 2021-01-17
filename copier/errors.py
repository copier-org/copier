class UserMessageError(Exception):
    """Exit the program giving a message to the user."""


class UnsupportedVersionError(UserMessageError):
    """Copier version does not support template version."""
