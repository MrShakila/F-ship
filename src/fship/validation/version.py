"""Version format validation."""

import re
from fship.errors import ValidationError


def validate_version_format(version_str: str) -> bool:
    """Validate version matches X.Y.Z+B or X.Y.Z-suffix+B format.

    Args:
        version_str: Version string to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If format invalid
    """
    if not version_str or not isinstance(version_str, str):
        raise ValidationError("Version must be non-empty string")

    pattern = r"^\d+\.\d+\.\d+(-[a-z0-9\-]+)?\+\d+$"
    if not re.match(pattern, version_str):
        raise ValidationError(
            f"Invalid version format: {version_str!r}. "
            "Expected: X.Y.Z+B or X.Y.Z-suffix+B (e.g., 1.2.3+45 or 1.2.3-qa1+45)"
        )
    return True


def validate_package_version_format(version_str: str) -> bool:
    """Validate version matches X.Y.Z (pub.dev semver, no build number).

    Raises:
        ValidationError: If format invalid
    """
    if not version_str or not isinstance(version_str, str):
        raise ValidationError("Version must be non-empty string")

    pattern = r"^\d+\.\d+\.\d+$"
    if not re.match(pattern, version_str):
        raise ValidationError(
            f"Invalid version format: {version_str!r}. "
            "Expected: X.Y.Z (e.g., 1.2.3)"
        )
    return True


def validate_bump_part(part: str) -> bool:
    """Validate bump part is patch|minor|major.

    Args:
        part: Bump part to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If not valid
    """
    if part not in ("patch", "minor", "major"):
        raise ValidationError(
            f"Invalid bump part: {part!r}. "
            "Must be one of: patch, minor, major"
        )
    return True
