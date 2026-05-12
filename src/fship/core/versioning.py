"""Version management with validation."""

import re
import subprocess
from pathlib import Path
from ruamel.yaml import YAML
from rich.console import Console
from rich.prompt import Prompt

from fship.errors import VersionError
from fship.validation import validate_version_format, validate_package_version_format, validate_bump_part

console = Console()


def get_max_build_from_tags() -> int:
    """Return highest build number (+N) found across all v* git tags."""
    try:
        result = subprocess.run(["git", "tag", "-l", "v*"], capture_output=True, text=True)
        if result.returncode != 0:
            return 0
        max_build = 0
        for tag in result.stdout.strip().splitlines():
            m = re.search(r'\+(\d+)$', tag)
            if m:
                max_build = max(max_build, int(m.group(1)))
        return max_build
    except Exception:
        return 0


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


def bump_flavor_version(current: str, flavor: str = "qa", known_flavors: set = None, min_build: int = 0) -> str:
    """Bump non-prod flavor version: increment suffix number and build.

    Rules:
    - No suffix: add flavor + counter           3.0.4+77      → 3.0.4-qa-1+78
    - Suffix is this flavor: increment counter  3.0.4-qa-1+78 → 3.0.4-qa-2+79
    - Suffix is another flavor: replace it      3.0.4-qa-1+78 (uat) → 3.0.4-uat-1+79
    - Suffix is custom (not a flavor): keep it  3.0.4-claim-1+78 → 3.0.4-claim-2+79

    known_flavors: set of configured flavor names used to distinguish flavor vs custom suffixes.
    If None or suffix not in known_flavors, treated as custom (preserved).

    min_build: floor for the new build number (from git tags). New build = max(build+1, min_build+1).

    Raises:
        VersionError: If parsing fails
    """
    validate_version_format(current)

    try:
        parts = current.split("+")
        semantic_part = parts[0]
        build = int(parts[1])
        new_build = max(build + 1, min_build + 1)

        if "-" not in semantic_part:
            return f"{semantic_part}-{flavor}-1+{new_build}"

        # Split into base semver and suffix (e.g. "3.0.4-qa-1" → "3.0.4", "qa-1")
        base_semver, suffix_full = semantic_part.split("-", 1)
        # Split suffix into name and number (e.g. "qa-1" → "qa", "1")
        suffix_parts = suffix_full.rsplit("-", 1)

        try:
            if len(suffix_parts) == 2:
                suffix_name, suffix_tail = suffix_parts
                int(suffix_tail)  # validate tail is numeric
            else:
                # No numeric tail — treat as unsupported format
                raise ValueError("no numeric suffix")
        except ValueError:
            raise VersionError(f"Can't parse flavor suffix: {suffix_full!r}")

        suffix_num = int(suffix_tail)
        is_flavor_suffix = known_flavors is not None and suffix_name in known_flavors

        if suffix_name == flavor:
            # Same flavor: increment counter
            return f"{base_semver}-{flavor}-{suffix_num + 1}+{new_build}"
        elif is_flavor_suffix:
            # Different flavor suffix: replace with current flavor, reset counter
            return f"{base_semver}-{flavor}-1+{new_build}"
        else:
            # Custom suffix: preserve it, just increment counter
            return f"{base_semver}-{suffix_name}-{suffix_num + 1}+{new_build}"

    except VersionError:
        raise
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


def read_package_version(pubspec_path: Path = None) -> str:
    """Read version from pubspec.yaml. Accepts X.Y.Z (no build number)."""
    path = pubspec_path or Path.cwd() / "pubspec.yaml"

    if not path.exists():
        raise VersionError(f"pubspec.yaml not found at {path}")

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    try:
        data = yaml.load(path)
        version = data.get("version", "0.0.0")
        validate_package_version_format(version)
        return version
    except Exception as e:
        raise VersionError(f"Failed to read version from pubspec.yaml: {e}")


def write_package_version(new_version: str, pubspec_path: Path = None) -> None:
    """Write X.Y.Z version to pubspec.yaml, preserving formatting."""
    path = pubspec_path or Path.cwd() / "pubspec.yaml"

    if not path.exists():
        raise VersionError(f"pubspec.yaml not found at {path}")

    validate_package_version_format(new_version)

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


def bump_package_version(current: str, part: str) -> str:
    """Bump X.Y.Z version: patch, minor, or major. Returns X.Y.Z (no build number).

    Raises:
        VersionError: If part invalid or parse fails
    """
    validate_package_version_format(current)
    validate_bump_part(part)

    try:
        major, minor, patch = (int(x) for x in current.split("."))

        if part == "patch":
            patch += 1
        elif part == "minor":
            minor += 1
            patch = 0
        elif part == "major":
            major += 1
            minor = 0
            patch = 0

        return f"{major}.{minor}.{patch}"
    except Exception as e:
        raise VersionError(f"Failed to bump package version: {e}")


def resolve_package_version(current: str, version: str = None, bump: str = None) -> str:
    """Resolve new package version (X.Y.Z) from flags or interactive prompt.

    Raises:
        VersionError: If resolved version invalid
    """
    if version:
        validate_package_version_format(version)
        return version

    if bump:
        validate_bump_part(bump)
        new_version = bump_package_version(current, bump)
        console.print(f"[cyan]{current}[/cyan] → [green]{new_version}[/green]")
        return new_version

    console.print(f"Current version: [cyan]{current}[/cyan]")
    suggested = bump_package_version(current, "patch")
    console.print(f"  [green]1) bump:[/green] {suggested}")
    choice = Prompt.ask("Select 1 or enter version")
    if choice == "1":
        return suggested

    validate_package_version_format(choice)
    return choice


def resolve_version(current: str, version: str = None, bump: str = None, flavor: str = None, known_flavors: set = None) -> str:
    """Resolve new version from flags or interactive prompt.

    Version format:
    - Prod: Pure semantic X.Y.Z+0 (no suffix names)
    - Non-prod: With suffix (e.g., 3.0.4-claim-2+79) or create one
    - Flavor suffix (qa/uat/etc): replaced when running different flavor
    - Custom suffix (claim/etc): preserved across all flavors

    known_flavors: set of configured flavor names (e.g. {"qa", "uat", "prod"}).
    Used to distinguish flavor suffixes from custom ones.

    Raises:
        VersionError: If resolved version invalid
    """
    if version:
        validate_version_format(version)
        return version

    if bump:
        validate_bump_part(bump)
        if flavor == "prod":
            new_version = bump_version(current, bump)
        else:
            max_build = get_max_build_from_tags()
            new_version = bump_flavor_version(current, flavor, known_flavors, min_build=max_build)
        console.print(f"[cyan]{current}[/cyan] → [green]{new_version}[/green]")
        return new_version

    console.print(f"Current version: [cyan]{current}[/cyan]")
    console.print(f"[dim]Suggested bumps:[/dim]")

    if flavor == "prod":
        suggested = bump_version(current, "patch")
    else:
        max_build = get_max_build_from_tags()
        suggested = bump_flavor_version(current, flavor, known_flavors, min_build=max_build)

    console.print(f"  [green]1) bump:[/green] {suggested}")
    choice = Prompt.ask("Select 1 or enter version")
    if choice == "1":
        return suggested

    validate_version_format(choice)
    return choice
