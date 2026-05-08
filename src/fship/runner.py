from pathlib import Path
from rich.console import Console
from rich.table import Table
from fship.config import Config, FlavorConfig
from fship.versioning import (
    read_version,
    write_version,
    resolve_version,
)
from fship.changelog import (
    generate_changelog,
    generate_release_notes,
    git_add_and_commit,
    git_tag,
)
from fship.builder import build_apk
from fship.distributor import distribute_to_firebase

console = Console()


def run_release(
    flavor: str,
    flavor_config: FlavorConfig,
    version: str = None,
    bump: str = None,
    skip_build: bool = False,
    skip_distribute: bool = False,
) -> bool:
    """Orchestrate full release flow."""

    console.rule(f"[bold cyan]fship release {flavor}[/bold cyan]")

    try:
        current_version = read_version()
        new_version = resolve_version(current_version, version, bump)

        steps = [
            ("Update pubspec.yaml", lambda: update_pubspec(new_version)),
            ("Generate CHANGELOG.md", lambda: generate_changelog()),
            ("Generate release notes", lambda: generate_release_notes(flavor)),
            ("Commit & tag", lambda: commit_and_tag(new_version, flavor)),
        ]

        if not skip_build:
            steps.append(
                ("Build APK", lambda: build_apk_step(flavor, flavor_config))
            )

        if not skip_distribute:
            steps.append(
                (
                    "Distribute to Firebase",
                    lambda: distribute_step(flavor_config),
                )
            )

        for step_name, step_fn in steps:
            console.print(f"\n[bold blue]→[/bold blue] {step_name}")
            if not step_fn():
                console.print(f"\n[bold red]Release stopped at: {step_name}[/bold red]")
                return False

        console.print(
            f"\n[bold green]✓ Release {new_version} to {flavor} complete![/bold green]"
        )
        show_summary(new_version, flavor)
        return True

    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        return False


def update_pubspec(version: str) -> bool:
    """Update pubspec.yaml with new version."""
    try:
        current = read_version()
        write_version(version)
        console.print(f"[green]✓[/green] pubspec.yaml: {current} → {version}")
        return True
    except Exception as e:
        console.print(f"[red]✗ Failed to update pubspec.yaml: {e}[/red]")
        return False


def commit_and_tag(version: str, flavor: str) -> bool:
    """Stage, commit, and tag the release."""
    if not git_add_and_commit(version, flavor):
        return False
    if not git_tag(version, flavor):
        return False
    return True


def build_apk_step(flavor: str, flavor_config: FlavorConfig) -> tuple[bool, str]:
    """Build APK and return (success, apk_path)."""
    success, apk_path = build_apk(flavor, flavor_config.entrypoint)
    if success:
        console.print(f"[green]✓[/green] APK ready: {apk_path or 'built'}")
    return success


def distribute_step(flavor_config: FlavorConfig) -> bool:
    """Distribute APK to Firebase."""
    apk_path = flavor_config.apk_path
    if not Path(apk_path).exists():
        console.print(f"[red]✗ APK path not found: {apk_path}[/red]")
        return False

    return distribute_to_firebase(
        apk_path,
        flavor_config.firebase_app_id_env,
        flavor_config.groups,
    )


def show_summary(version: str, flavor: str) -> None:
    """Display summary table of what was done."""
    table = Table(title=f"Release Summary: {version} → {flavor}")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    table.add_row("Version Bumped", "pubspec.yaml updated")
    table.add_row("Changelog", "CHANGELOG.md generated")
    table.add_row("Release Notes", "release_note.txt generated")
    table.add_row("Git Commit", f"chore: release {version}-{flavor}")
    table.add_row("Git Tag", f"v{version}-{flavor}")
    table.add_row("Build", "APK compiled")
    table.add_row("Distribution", f"Firebase App Distribution")

    console.print(table)
