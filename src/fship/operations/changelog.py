"""Git operations for changelog and tagging."""

import subprocess
from pathlib import Path
from rich.console import Console

from fship.errors import DistributionError

console = Console()


def get_previous_tag() -> str:
    """Get the previous tag, skipping the latest one."""
    try:
        # Get the second-most recent tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            current_tag = result.stdout.strip()

            # Now get the one before that
            result = subprocess.run(
                ["git", "rev-list", "--tags", "--skip=1", "--max-count=1"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                commit = result.stdout.strip()
                result = subprocess.run(
                    ["git", "describe", "--tags", "--abbrev=0", commit],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
    except Exception:
        pass
    return ""


def generate_changelog() -> bool:
    """Generate CHANGELOG.md using git-chglog. Non-fatal if config missing."""
    try:
        result = subprocess.run(
            ["git-chglog", "-o", "CHANGELOG.md"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            console.print("[green]✓[/green] CHANGELOG.md generated")
            return True
        else:
            console.print(
                "[yellow]⚠[/yellow] git-chglog skipped (missing .chglog/config.yml or other error)"
            )
            return True  # non-fatal; continue with release

    except FileNotFoundError:
        console.print(
            "[yellow]⚠[/yellow] git-chglog not found. Install: brew install git-chglog"
        )
        return True  # non-fatal; continue


def generate_release_notes(flavor: str) -> bool:
    """Generate release_note.txt from git log since last tag.

    Raises:
        DistributionError: If git log fails
    """
    prev_tag = get_previous_tag()

    if not prev_tag:
        console.print(
            "[yellow]Warning: No previous tag found. Using all commits.[/yellow]"
        )
        rev_range = "HEAD"
    else:
        rev_range = f"{prev_tag}..HEAD"

    try:
        result = subprocess.run(
            ["git", "log", "--pretty=- %s (%an)", rev_range],
            capture_output=True,
            text=True,
            check=True,
        )
        release_notes = result.stdout.strip()

        if not release_notes:
            release_notes = f"Release {flavor} - no new commits"

        Path("release_note.txt").write_text(release_notes)
        console.print("[green]✓[/green] release_note.txt generated")
        return True
    except subprocess.CalledProcessError as e:
        raise DistributionError(f"Failed to generate release notes: {e}") from e


def git_add_and_commit(version: str, flavor: str) -> bool:
    """Stage and commit version bump + changelog. Only add files that exist.

    Raises:
        DistributionError: If git operations fail
    """
    try:
        files_to_add = ["pubspec.yaml"]
        if Path("CHANGELOG.md").exists():
            files_to_add.append("CHANGELOG.md")
        if Path("release_note.txt").exists():
            files_to_add.append("release_note.txt")

        subprocess.run(["git", "add"] + files_to_add, check=True)

        has_flavor_suffix = "-" in version.split("+")[0]
        is_prod = flavor == "prod"
        if has_flavor_suffix or is_prod:
            commit_msg = f"chore: release {version}"
        else:
            commit_msg = f"chore: release {version}-{flavor}"

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True,
        )
        console.print(f"[green]✓[/green] Committed: {commit_msg}")
        return True
    except subprocess.CalledProcessError as e:
        raise DistributionError(f"Git commit failed: {e}") from e


def git_tag(version: str, flavor: str) -> bool:
    """Create git tag for release.

    Raises:
        DistributionError: If tagging fails
    """
    has_flavor_suffix = "-" in version.split("+")[0]
    is_prod = flavor == "prod"
    tag = f"v{version}" if (has_flavor_suffix or is_prod) else f"v{version}-{flavor}"
    try:
        subprocess.run(["git", "tag", tag], check=True)
        console.print(f"[green]✓[/green] Tagged: {tag}")
        return True
    except subprocess.CalledProcessError as e:
        raise DistributionError(f"Git tag failed: {e}") from e
