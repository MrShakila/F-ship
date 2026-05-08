import subprocess
import threading
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


def _rollback_release(original_version: str, new_version: str, flavor: str) -> None:
    """Revert version bump and delete git tag after failure."""
    console.print("\n[yellow]Rolling back release...[/yellow]")
    try:
        write_version(original_version)
        console.print(f"[green]✓[/green] Reverted pubspec.yaml: {new_version} → {original_version}")
    except Exception as e:
        console.print(f"[red]✗ Failed to revert pubspec.yaml: {e}[/red]")

    has_flavor_suffix = "-" in new_version.split("+")[0]
    is_prod = flavor == "prod"
    tag = f"v{new_version}" if (has_flavor_suffix or is_prod) else f"v{new_version}-{flavor}"

    try:
        result = subprocess.run(["git", "tag", "-d", tag], capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"[green]✓[/green] Deleted tag: {tag}")
        else:
            console.print(f"[yellow]⚠[/yellow] Tag {tag} not found or already deleted")
    except Exception as e:
        console.print(f"[red]✗ Failed to delete tag: {e}[/red]")

    try:
        result = subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True)
        if result.returncode == 0 and f"chore: release {new_version}" in result.stdout:
            subprocess.run(["git", "reset", "--soft", "HEAD~1"], check=True)
            console.print("[green]✓[/green] Reverted git commit")
    except Exception as e:
        console.print(f"[red]✗ Failed to revert commit: {e}[/red]")

    console.print("[yellow]Rollback complete. Fix the issue and retry.[/yellow]")


def _build_parallel(flavor: str, flavor_config: FlavorConfig) -> tuple[bool, bool]:
    """Build APK and IPA in parallel using threads. Returns (apk_success, ipa_success)."""
    apk_result = [False]
    ipa_result = [False]
    apk_path_result = [None]

    def build_apk_thread():
        try:
            success, apk_path = build_apk(flavor, flavor_config.entrypoint)
            apk_result[0] = success
            apk_path_result[0] = apk_path
            if success:
                console.print(f"[green]✓[/green] APK ready: {apk_path or 'built'}")
            else:
                console.print("[red]✗ APK build failed[/red]")
        except Exception as e:
            console.print(f"[red]✗ APK build error: {e}[/red]")

    def build_ipa_thread():
        try:
            from fship.operations.builder import build_ipa
            success, ipa_path = build_ipa(flavor, flavor_config.entrypoint)
            ipa_result[0] = success
            if success:
                console.print(f"[green]✓[/green] IPA ready: {ipa_path or 'built'}")
            else:
                console.print("[yellow]⚠[/yellow] IPA build failed (Android-only release)")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] IPA build skipped: {e}")

    t_apk = threading.Thread(target=build_apk_thread)
    t_ipa = threading.Thread(target=build_ipa_thread)

    t_apk.start()
    t_ipa.start()
    t_apk.join()
    t_ipa.join()

    return apk_result[0], ipa_result[0]


def run_release(
    flavor: str,
    flavor_config: FlavorConfig,
    version: str = None,
    bump: str = None,
    skip_build: bool = False,
    skip_distribute: bool = False,
    no_push: bool = False,
    resume_from: str = None,
    auto_rollback: bool = True,
    parallel_builds: bool = False,
) -> bool:
    """Orchestrate full release flow."""

    console.rule(f"[bold cyan]fship release {flavor}[/bold cyan]")

    try:
        current_version = read_version()
        new_version = resolve_version(current_version, version, bump, flavor)

        # shared state: build step writes ipa_built, distribute step reads it
        build_state = {"ipa_built": False}

        def build_step():
            has_ios = bool(flavor_config.ipa_path and flavor_config.firebase_app_id_env_ios)

            if parallel_builds and has_ios:
                console.print("[dim]Building APK + IPA in parallel...[/dim]")
                apk_ok, ipa_ok = _build_parallel(flavor, flavor_config)
                build_state["ipa_built"] = ipa_ok
                return apk_ok
            else:
                # Build APK
                success, apk_path = build_apk(flavor, flavor_config.entrypoint)
                if success:
                    console.print(f"[green]✓[/green] APK ready: {apk_path or 'built'}")
                else:
                    return False

                # Build IPA sequentially if configured
                if has_ios:
                    from fship.operations.builder import build_ipa
                    ipa_ok, ipa_path = build_ipa(flavor, flavor_config.entrypoint)
                    build_state["ipa_built"] = ipa_ok
                    if ipa_ok:
                        console.print(f"[green]✓[/green] IPA ready: {ipa_path or 'built'}")
                    else:
                        console.print("[yellow]⚠[/yellow] IPA build failed (Android-only distribution)")

                return success

        def distribute_both_step():
            # Always distribute APK
            apk_ok = distribute_step(flavor_config)
            # Distribute IPA only if it was built in parallel
            if build_state["ipa_built"] and flavor_config.ipa_path and flavor_config.firebase_app_id_env_ios:
                console.print("\n[bold blue]→[/bold blue] Distribute IPA to Firebase")
                ios_ok = distribute_to_firebase(
                    flavor_config.ipa_path,
                    flavor_config.firebase_app_id_env_ios,
                    flavor_config.groups,
                )
                if not ios_ok:
                    console.print("[yellow]⚠[/yellow] iOS distribution failed (Android succeeded)")
            return apk_ok

        all_steps = [
            ("Update pubspec.yaml", "version", lambda: update_pubspec(new_version)),
            ("Generate CHANGELOG.md", "changelog", lambda: generate_changelog()),
            ("Generate release notes", "notes", lambda: generate_release_notes(flavor)),
            ("Commit & tag", "tag", lambda: commit_and_tag(new_version, flavor)),
            ("Build", "build", build_step),
            ("Distribute to Firebase", "distribute", distribute_both_step),
        ]

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
            if skip_build:
                steps = [s for s in steps if s[0] != "Build"]
            if skip_distribute:
                steps = [s for s in steps if s[0] != "Distribute to Firebase"]

        completed_steps = []
        for step_name, step_fn in steps:
            console.print(f"\n[bold blue]→[/bold blue] {step_name}")
            try:
                if not step_fn():
                    console.print(f"\n[bold red]Release stopped at: {step_name}[/bold red]")
                    if auto_rollback and "Commit & tag" in completed_steps:
                        _rollback_release(current_version, new_version, flavor)
                    return False
                completed_steps.append(step_name)
            except FshipError as e:
                console.print(f"\n[bold red]Release stopped at: {step_name}[/bold red]")
                console.print(f"[red]Error: {e}[/red]")
                if auto_rollback and "Commit & tag" in completed_steps:
                    _rollback_release(current_version, new_version, flavor)
                return False

        console.print(f"\n[bold green]✓ Release {new_version} to {flavor} complete![/bold green]")
        show_summary(new_version, flavor, no_push=no_push)
        return True

    except FshipError as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        return False
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error: {e}[/bold red]")
        return False


def run_multi_release(
    flavors: list[str],
    config,
    version: str = None,
    bump: str = None,
    skip_build: bool = False,
    skip_distribute: bool = False,
    no_push: bool = False,
) -> dict[str, bool]:
    """Release multiple flavors sequentially. Returns {flavor: success}."""
    results = {}
    console.rule("[bold cyan]fship multi-release[/bold cyan]")
    console.print(f"[dim]Releasing to: {', '.join(flavors)}[/dim]\n")

    for flavor in flavors:
        try:
            from fship.core import get_flavor
            from fship.core.config import load_env_file
            load_env_file(flavor)  # load flavor-specific env before each release
            flavor_config = get_flavor(config, flavor)
        except FshipError as e:
            console.print(f"[red]✗ Skipping {flavor}: {e}[/red]")
            results[flavor] = False
            continue

        console.print(f"\n[bold]━━━ {flavor.upper()} ━━━[/bold]")
        results[flavor] = run_release(
            flavor, flavor_config,
            version=version, bump=bump,
            skip_build=skip_build, skip_distribute=skip_distribute,
            no_push=no_push,
        )

    console.rule("[bold]Multi-Release Summary[/bold]")
    for flavor, success in results.items():
        status = "[green]✓ success[/green]" if success else "[red]✗ failed[/red]"
        console.print(f"  {flavor}: {status}")

    return results


def update_pubspec(version: str) -> bool:
    try:
        current = read_version()
        write_version(version)
        console.print(f"[green]✓[/green] pubspec.yaml: {current} → {version}")
        return True
    except FshipError as e:
        console.print(f"[red]✗ Failed to update pubspec.yaml: {e}[/red]")
        raise


def commit_and_tag(version: str, flavor: str) -> bool:
    git_add_and_commit(version, flavor)
    git_tag(version, flavor)
    return True


def distribute_step(flavor_config: FlavorConfig) -> bool:
    return distribute_to_firebase(
        flavor_config.apk_path,
        flavor_config.firebase_app_id_env_android,
        flavor_config.groups,
    )


def show_summary(version: str, flavor: str, no_push: bool = False) -> None:
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
    table.add_row("Distribution", "Firebase App Distribution")

    console.print(table)

    if no_push:
        console.print("\n[yellow]⚠ Changes committed and tagged locally.[/yellow]")
        console.print(f"[dim]Push manually: git push origin main && git push origin {tag_name}[/dim]")
