from pathlib import Path
from rich.console import Console
from rich.table import Table

from fship.core import FlavorConfig, read_version, write_version, resolve_version
from fship.operations import (
    generate_changelog,
    generate_release_notes,
    git_add_and_commit,
    git_tag,
    build_apk,
    distribute_to_firebase,
)
from fship.errors import FshipError

console = Console()


def run_release(
    flavor: str,
    flavor_config: FlavorConfig,
    version: str = None,
    bump: str = None,
    skip_build: bool = False,
    skip_distribute: bool = False,
    no_push: bool = False,
    resume_from: str = None,
) -> bool:
    """Orchestrate full release flow.

    Args:
        resume_from: Resume from step: version, changelog, tag, build, distribute
    """

    console.rule(f"[bold cyan]fship release {flavor}[/bold cyan]")

    try:
        current_version = read_version()
        new_version = resolve_version(current_version, version, bump, flavor)

        # Define all steps with resume IDs
        all_steps = [
            ("Update pubspec.yaml", "version", lambda: update_pubspec(new_version)),
            ("Generate CHANGELOG.md", "changelog", lambda: generate_changelog()),
            ("Generate release notes", "notes", lambda: generate_release_notes(flavor)),
            ("Commit & tag", "tag", lambda: commit_and_tag(new_version, flavor)),
            ("Build APK", "build", lambda: build_apk_step(flavor, flavor_config) if not skip_build else True),
            ("Distribute to Firebase", "distribute", lambda: distribute_step(flavor_config) if not skip_distribute else True),
        ]

        # Filter steps based on resume_from or skip flags
        if resume_from:
            resume_ids = [step[1] for step in all_steps]
            try:
                start_idx = resume_ids.index(resume_from)
                steps = [(name, fn) for name, resume_id, fn in all_steps[start_idx:]]
            except ValueError:
                console.print(f"[red]Invalid resume step: {resume_from}[/red]")
                return False
        else:
            steps = [(name, fn) for name, resume_id, fn in all_steps]
            # Apply skip flags
            if skip_build:
                steps = [s for s in steps if "Build APK" not in s[0]]
            if skip_distribute:
                steps = [s for s in steps if "Distribute" not in s[0]]

        for step_name, step_fn in steps:
            console.print(f"\n[bold blue]→[/bold blue] {step_name}")
            try:
                if not step_fn():
                    console.print(f"\n[bold red]Release stopped at: {step_name}[/bold red]")
                    return False
            except FshipError as e:
                console.print(f"\n[bold red]Release stopped at: {step_name}[/bold red]")
                console.print(f"[red]Error: {e}[/red]")
                return False

        console.print(
            f"\n[bold green]✓ Release {new_version} to {flavor} complete![/bold green]"
        )
        show_summary(new_version, flavor, no_push=no_push)
        return True

    except FshipError as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        return False
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error: {e}[/bold red]")
        return False


def update_pubspec(version: str) -> bool:
    """Update pubspec.yaml with new version."""
    try:
        current = read_version()
        write_version(version)
        console.print(f"[green]✓[/green] pubspec.yaml: {current} → {version}")
        return True
    except FshipError as e:
        console.print(f"[red]✗ Failed to update pubspec.yaml: {e}[/red]")
        raise


def commit_and_tag(version: str, flavor: str) -> bool:
    """Stage, commit, and tag the release."""
    git_add_and_commit(version, flavor)
    git_tag(version, flavor)
    return True


def build_apk_step(flavor: str, flavor_config: FlavorConfig) -> bool:
    """Build APK and return success status."""
    success, apk_path = build_apk(flavor, flavor_config.entrypoint)
    if success:
        console.print(f"[green]✓[/green] APK ready: {apk_path or 'built'}")
    return success


def distribute_step(flavor_config: FlavorConfig) -> bool:
    """Distribute APK to Firebase."""
    return distribute_to_firebase(
        flavor_config.apk_path,
        flavor_config.firebase_app_id_env_android,
        flavor_config.groups,
    )


def show_summary(version: str, flavor: str, no_push: bool = False) -> None:
    """Display summary table of what was done."""
    has_flavor_suffix = "-" in version.split("+")[0]
    is_prod = flavor == "prod"
    commit_msg = f"chore: release {version}" if (has_flavor_suffix or is_prod) else f"chore: release {version}-{flavor}"
    tag_name = f"v{version}" if (has_flavor_suffix or is_prod) else f"v{version}-{flavor}"

    table = Table(title=f"Release Summary: {version} → {flavor}")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    table.add_row("Version Bumped", "pubspec.yaml updated")
    table.add_row("Changelog", "CHANGELOG.md generated")
    table.add_row("Release Notes", "release_note.txt generated")
    table.add_row("Git Commit", commit_msg)
    table.add_row("Git Tag", tag_name)
    table.add_row("Build", "APK compiled")
    table.add_row("Distribution", f"Firebase App Distribution")

    console.print(table)

    if no_push:
        console.print("\n[yellow]⚠ Changes committed and tagged locally.[/yellow]")
        console.print(f"[dim]Push manually: git push origin main && git push origin {tag_name}[/dim]")
