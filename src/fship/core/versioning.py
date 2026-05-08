"""Version management with validation."""

from pathlib import Path
from ruamel.yaml import YAML
from rich.console import Console
from rich.prompt import Prompt

from fship.errors import VersionError
from fship.validation import validate_version_format, validate_bump_part

console = Console()


def read_version(pubspec_path: Path = None) -> str:
    """Read version from pubspec.yaml. Format: X.Y.Z+B"""
    path = pubspec_path or Path.cwd() / "pubspec.yaml"

    if not path.exists():
        raise VersionError(f"pubspec.yaml not found at {path}")

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    try:
        data = yaml.load(path)
        version = data.get("version", "0.0.0+0")
        validate_version_format(version)
        return version
    except Exception as e:
        raise VersionError(f"Failed to read version from pubspec.yaml: {e}")


def write_version(new_version: str, pubspec_path: Path = None) -> None:
    """Write version to pubspec.yaml, preserving formatting."""
    path = pubspec_path or Path.cwd() / "pubspec.yaml"

    if not path.exists():
        raise VersionError(f"pubspec.yaml not found at {path}")

    validate_version_format(new_version)

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    try:
        data = yaml.load(path)
        data["version"] = new_version

        with open(path, "w") as f:
            yaml.dump(data, f)
    except Exception as e:
        raise VersionError(f"Failed to write version to pubspec.yaml: {e}")


def parse_version(version_str: str) -> tuple[int, int, int, int]:
    """Parse 'X.Y.Z+B' or 'X.Y.Z-suffix+B' into (major, minor, patch, build).

    Raises:
        VersionError: If format invalid
    """
    validate_version_format(version_str)

    try:
        parts = version_str.split("+")
        semantic = parts[0].split(".")

        patch_str = semantic[2]
        if "-" in patch_str:
            patch_str = patch_str.split("-")[0]

        return (
            int(semantic[0]),
            int(semantic[1]),
            int(patch_str),
            int(parts[1]),
        )
    except (ValueError, IndexError) as e:
        raise VersionError(f"Failed to parse version {version_str!r}: {e}")


def format_version(major: int, minor: int, patch: int, build: int) -> str:
    """Format (major, minor, patch, build) to 'X.Y.Z+B'."""
    return f"{major}.{minor}.{patch}+{build}"


def bump_flavor_version(current: str) -> str:
    """Bump non-prod flavor version: increment suffix number and build.

    For 3.0.4-qa-1+78 → 3.0.4-qa-2+79

    Raises:
        VersionError: If parsing fails
    """
    validate_version_format(current)

    try:
        parts = current.split("+")
        semantic_part = parts[0]
        build = int(parts[1])

        if "-" not in semantic_part:
            raise VersionError(f"Version {current!r} has no flavor suffix")

        base, suffix = semantic_part.rsplit("-", 1)
        try:
            suffix_num = int(suffix)
            new_suffix = str(suffix_num + 1)
        except ValueError:
            raise VersionError(f"Can't parse flavor suffix: {suffix!r}")

        return f"{base}-{new_suffix}+{build + 1}"
    except Exception as e:
        raise VersionError(f"Failed to bump flavor version: {e}")


def bump_version(current: str, part: str) -> str:
    """Bump version part: 'patch', 'minor', or 'major'. Resets build to 0.

    Raises:
        VersionError: If part invalid or parse fails
    """
    validate_version_format(current)
    validate_bump_part(part)

    try:
        major, minor, patch, _ = parse_version(current)

        if part == "patch":
            patch += 1
        elif part == "minor":
            minor += 1
            patch = 0
        elif part == "major":
            major += 1
            minor = 0
            patch = 0

        return format_version(major, minor, patch, 0)
    except Exception as e:
        raise VersionError(f"Failed to bump version: {e}")


def resolve_version(current: str, version: str = None, bump: str = None, flavor: str = None) -> str:
    """Resolve new version from flags or interactive prompt.

    For non-prod flavors (qa, uat, custom): bump suffix + build number
    For prod: use semantic versioning (patch, minor, major)

    Raises:
        VersionError: If resolved version invalid
    """
    if version:
        validate_version_format(version)
        return version

    is_prod = flavor == "prod"

    if bump:
        validate_bump_part(bump)
        if is_prod:
            new_version = bump_version(current, bump)
        else:
            new_version = bump_flavor_version(current)
        console.print(f"[cyan]{current}[/cyan] → [green]{new_version}[/green]")
        return new_version

    console.print(f"Current version: [cyan]{current}[/cyan]")
    console.print(f"[dim]Suggested bumps:[/dim]")

    if is_prod:
        patch_version = bump_version(current, 'patch')
        minor_version = bump_version(current, 'minor')
        major_version = bump_version(current, 'major')
        console.print(f"  [green]1) patch:[/green] {patch_version}")
        console.print(f"  [green]2) minor:[/green] {minor_version}")
        console.print(f"  [green]3) major:[/green] {major_version}")
        choice = Prompt.ask("Select (1-3) or enter version")
        if choice == "1":
            return patch_version
        elif choice == "2":
            return minor_version
        elif choice == "3":
            return major_version
    else:
        flavor_bumped = bump_flavor_version(current)
        console.print(f"  [green]1) flavor bump:[/green] {flavor_bumped}")
        choice = Prompt.ask("Select 1 or enter version")
        if choice == "1":
            return flavor_bumped

    validate_version_format(choice)
    return choice
