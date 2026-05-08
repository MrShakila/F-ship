"""Environment variable validation."""

import os
import re
from fship.errors import ValidationError


def validate_firebase_app_id(app_id: str) -> bool:
    """Validate Firebase app ID format.

    Args:
        app_id: Firebase app ID to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If invalid
    """
    if not app_id or not isinstance(app_id, str):
        raise ValidationError("Firebase app ID must be non-empty string")

    if not re.match(r"^[a-zA-Z0-9:._-]+$", app_id):
        raise ValidationError(
            f"Invalid Firebase app ID: {app_id!r}. "
            "Must contain only alphanumeric, :, ., _, - characters"
        )
    return True


def validate_required_env_vars(required: list[str]) -> bool:
    """Validate all required env vars are set.

    Args:
        required: List of required env var names

    Returns:
        True if all present

    Raises:
        ValidationError: If any missing
    """
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        raise ValidationError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    return True
