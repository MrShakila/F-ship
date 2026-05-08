import subprocess
from pathlib import Path
from rich.console import Console

console = Console()


def get_previous_tag() -> str:
    """Get the previous tag, skipping the latest one."""
    try:
        result = subprocess.run(
            [
                "bash",
                "-c",
                "git describe --tags --abbrev=0 $(git rev-list --tags --skip=1 --max-count=1)",
            ],
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
    """Generate release_note.txt from git log since last tag."""
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
            [
                "bash",
                "-c",
                f'git log --pretty="- %s (%an)" {rev_range}',
            ],
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
        console.print(f"[red]✗ Failed to generate release notes: {e}[/red]")
        return False


def git_add_and_commit(version: str, flavor: str) -> bool:
    """Stage and commit version bump + changelog. Only add files that exist."""
    try:
        files_to_add = ["pubspec.yaml"]
        if Path("CHANGELOG.md").exists():
            files_to_add.append("CHANGELOG.md")
        if Path("release_note.txt").exists():
            files_to_add.append("release_note.txt")

        subprocess.run(["git", "add"] + files_to_add, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: release {version}-{flavor}"],
            check=True,
        )
        console.print(f"[green]✓[/green] Committed: chore: release {version}-{flavor}")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Git commit failed: {e}[/red]")
        return False


def git_tag(version: str, flavor: str) -> bool:
    """Create git tag for release."""
    tag = f"v{version}-{flavor}"
    try:
        subprocess.run(["git", "tag", tag], check=True)
        console.print(f"[green]✓[/green] Tagged: {tag}")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Git tag failed: {e}[/red]")
        return False
