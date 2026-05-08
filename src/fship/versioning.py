from pathlib import Path
from ruamel.yaml import YAML
from rich.console import Console
from rich.prompt import Prompt

console = Console()


def read_version(pubspec_path: Path = None) -> str:
    """Read version from pubspec.yaml. Format: X.Y.Z+B"""
    path = pubspec_path or Path.cwd() / "pubspec.yaml"

    if not path.exists():
        raise FileNotFoundError(f"pubspec.yaml not found at {path}")

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    data = yaml.load(path)
    return data.get("version", "0.0.0+0")


def write_version(new_version: str, pubspec_path: Path = None) -> None:
    """Write version to pubspec.yaml, preserving formatting."""
    path = pubspec_path or Path.cwd() / "pubspec.yaml"

    if not path.exists():
        raise FileNotFoundError(f"pubspec.yaml not found at {path}")

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    data = yaml.load(path)
    data["version"] = new_version

    with open(path, "w") as f:
        yaml.dump(data, f)


def parse_version(version_str: str) -> tuple[int, int, int, int]:
    """Parse 'X.Y.Z+B' into (major, minor, patch, build)."""
    parts = version_str.split("+")
    semantic = parts[0].split(".")
    build = int(parts[1]) if len(parts) > 1 else 0

    return (
        int(semantic[0]),
        int(semantic[1]) if len(semantic) > 1 else 0,
        int(semantic[2]) if len(semantic) > 2 else 0,
        build,
    )


def format_version(major: int, minor: int, patch: int, build: int) -> str:
    """Format (major, minor, patch, build) to 'X.Y.Z+B'."""
    return f"{major}.{minor}.{patch}+{build}"


def bump_version(current: str, part: str) -> str:
    """Bump version part: 'patch', 'minor', or 'major'. Resets build to 0."""
    major, minor, patch, build = parse_version(current)

    if part == "patch":
        patch += 1
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Unknown bump part: {part}")

    return format_version(major, minor, patch, 0)


def resolve_version(current: str, version: str = None, bump: str = None) -> str:
    """Resolve new version from flags or interactive prompt."""
    if version:
        return version

    if bump:
        new_version = bump_version(current, bump)
        console.print(f"[cyan]{current}[/cyan] → [green]{new_version}[/green]")
        return new_version

    console.print(f"Current version: [cyan]{current}[/cyan]")
    new_version = Prompt.ask("New version")
    return new_version
