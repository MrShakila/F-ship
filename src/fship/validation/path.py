"""Path security and existence validation."""

from pathlib import Path
from fship.errors import ValidationError


def validate_path_within_project(path: str | Path, project_root: Path | None = None) -> bool:
    """Validate path is within project directory (prevent traversal).

    Args:
        path: Path to validate
        project_root: Project root (default: cwd)

    Returns:
        True if safe

    Raises:
        ValidationError: If outside project or contains traversal
    """
    project_root = project_root or Path.cwd()
    path_obj = Path(path).resolve()
    root_obj = project_root.resolve()

    try:
        path_obj.relative_to(root_obj)
    except ValueError:
        raise ValidationError(
            f"Path {path!r} is outside project directory {project_root}"
        )
    return True


def validate_file_exists(path: str | Path, name: str = "File") -> bool:
    """Validate file exists and is readable.

    Args:
        path: File path to check
        name: Display name for error message

    Returns:
        True if file exists

    Raises:
        ValidationError: If file missing
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise ValidationError(f"{name} not found: {path}")
    if not path_obj.is_file():
        raise ValidationError(f"{name} is not a file: {path}")
    return True
