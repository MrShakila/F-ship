import typer
import os
import subprocess
import sys
from pathlib import Path
from rich.console import Console

from fship.core import load_config, get_flavor
from fship.core.config import CONFIG_FILE, CONFIG_DIR, DEFAULT_CFG, save_config
from fship.runner import run_release, run_publish
from fship.errors import FshipError, ValidationError
from fship.validation import validate_bump_part

app = typer.Typer(
    help="fship — Flutter Ship. Orchestrate release workflows to Firebase App Distribution.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def release(
    flavor: str = typer.Argument(
        ..., help="Flavor to release (qa, uat, prod, or custom)"
    ),
    version: str = typer.Option(
        None,
        "--version",
        "-v",
        help="Exact version to release (e.g. 1.2.4+46). Interactive if omitted.",
    ),
    bump: str = typer.Option(
        None,
        "--bump",
        "-b",
        help="Auto-increment version: patch, minor, or major. Resets build to 0.",
    ),
    skip_build: bool = typer.Option(
        False, "--skip-build", help="Skip Flutter build step (for testing)"
    ),
    skip_distribute: bool = typer.Option(
        False,
        "--skip-distribute",
        help="Skip Firebase distribution (for dry-run)",
    ),
    no_push: bool = typer.Option(
        False, "--no-push", help="Commit and tag but do not push to remote"
    ),
    resume_from: str = typer.Option(
        None,
        "--resume-from",
        help="Resume from step: version, changelog, tag, build, distribute (skips earlier steps)",
    ),
):
    """Release a flavor to Firebase App Distribution.

    Examples:
        fship release qa                    # Interactive version prompt
        fship release qa --version 1.2.4+46  # Exact version
        fship release qa --bump patch       # Auto-bump patch version
        fship release qa --resume-from build   # Skip version/tag, retry from build
        fship release qa --resume-from distribute  # Skip build, retry distribution
    """
    try:
        config = load_config(flavor)
        flavor_config = get_flavor(config, flavor)

        if bump:
            validate_bump_part(bump)
        if version and bump:
            raise ValidationError("Cannot specify both --version and --bump")
        if resume_from and resume_from not in ["version", "changelog", "notes", "tag", "build", "distribute"]:
            raise ValidationError(f"Invalid resume step: {resume_from}")
    except FshipError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    parallel = os.getenv("FSHIP_PARALLEL_BUILDS", "").lower() in ("1", "true")

    success = run_release(
        flavor,
        flavor_config,
        version=version,
        bump=bump,
        skip_build=skip_build,
        skip_distribute=skip_distribute,
        no_push=no_push,
        resume_from=resume_from,
        parallel_builds=parallel,
        known_flavors=set(config.flavors.keys()),
    )

    raise typer.Exit(0 if success else 1)


@app.command()
def status(
    flavor: str = typer.Argument(None, help="Flavor to check (optional)"),
):
    """Show current version, last release, and pending commits."""
    try:
        from fship.core.versioning import read_version
        current = read_version()
        console.print(f"[bold]Current version:[/bold] [cyan]{current}[/cyan]")
    except Exception as e:
        console.print(f"[yellow]Version: unknown ({e})[/yellow]")

    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-version:refname"],
            capture_output=True, text=True, check=False,
        )
        tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
        if flavor:
            tags = [t for t in tags if flavor in t or t.startswith("v") and "-" not in t]
        last_tag = tags[0] if tags else None

        if last_tag:
            console.print(f"[bold]Last release:[/bold] [green]{last_tag}[/green]")
            date_result = subprocess.run(
                ["git", "log", "-1", "--format=%ar", last_tag],
                capture_output=True, text=True, check=False,
            )
            if date_result.returncode == 0:
                console.print(f"[bold]Released:[/bold] {date_result.stdout.strip()}")

            count_result = subprocess.run(
                ["git", "rev-list", "--count", f"{last_tag}..HEAD"],
                capture_output=True, text=True, check=False,
            )
            if count_result.returncode == 0:
                count = count_result.stdout.strip()
                console.print(f"[bold]Pending commits:[/bold] {count}")
        else:
            console.print("[dim]No releases found.[/dim]")
    except Exception as e:
        console.print(f"[yellow]Git info unavailable: {e}[/yellow]")


@app.command("pre-check")
def pre_check(
    flavor: str = typer.Argument(..., help="Flavor to validate"),
):
    """Run pre-release checks: Flutter, Firebase credentials, config."""
    console.rule(f"[bold cyan]Pre-release checks for {flavor}[/bold cyan]")
    all_ok = True

    try:
        config = load_config(flavor)
        flavor_config = get_flavor(config, flavor)
        console.print(f"[green]✓[/green] Config: flavor '{flavor}' found")
    except FshipError as e:
        console.print(f"[red]✗ Config: {e}[/red]")
        raise typer.Exit(1)

    result = subprocess.run(["flutter", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        version_line = result.stdout.split("\n")[0]
        console.print(f"[green]✓[/green] Flutter: {version_line}")
    else:
        console.print("[red]✗ Flutter not found[/red]")
        all_ok = False

    result = subprocess.run(["firebase", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        console.print(f"[green]✓[/green] Firebase CLI: {result.stdout.strip()}")
    else:
        console.print("[red]✗ Firebase CLI not found (npm install -g firebase-tools)[/red]")
        all_ok = False

    android_id = os.getenv(flavor_config.firebase_app_id_env_android)
    ios_id = os.getenv(flavor_config.firebase_app_id_env_ios)
    if android_id:
        console.print(f"[green]✓[/green] APPIDANDROID: set")
    else:
        console.print(f"[red]✗ APPIDANDROID not set in .env.{flavor}[/red]")
        all_ok = False
    if ios_id:
        console.print(f"[green]✓[/green] APPIDIOS: set")
    else:
        console.print(f"[yellow]⚠[/yellow] APPIDIOS not set (iOS distribution will be skipped)")

    from pathlib import Path as _Path
    apk = _Path(flavor_config.apk_path)
    if apk.exists():
        console.print(f"[green]✓[/green] APK exists: {apk}")
    else:
        console.print(f"[yellow]⚠[/yellow] APK not built yet: {apk}")

    console.print()
    if all_ok:
        console.print("[bold green]✓ All checks passed. Ready to release.[/bold green]")
    else:
        console.print("[bold red]✗ Issues found. Fix before releasing.[/bold red]")
    raise typer.Exit(0 if all_ok else 1)


@app.command("multi-release")
def multi_release(
    flavors: str = typer.Argument(..., help="Comma-separated flavors (e.g., qa,uat)"),
    bump: str = typer.Option(None, "--bump", "-b", help="Auto-bump: patch, minor, or major"),
    skip_build: bool = typer.Option(False, "--skip-build"),
    skip_distribute: bool = typer.Option(False, "--skip-distribute"),
    no_push: bool = typer.Option(False, "--no-push"),
):
    """Release multiple flavors in sequence.

    Example:
        fship multi-release qa,uat --bump patch
    """
    from fship.runner import run_multi_release

    flavor_list = [f.strip() for f in flavors.split(",") if f.strip()]
    if not flavor_list:
        console.print("[red]No flavors specified.[/red]")
        raise typer.Exit(1)

    try:
        config = load_config()  # load config only (env loaded per-flavor in run_multi_release)
        if bump:
            validate_bump_part(bump)
    except FshipError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    results = run_multi_release(
        flavor_list, config,
        bump=bump,
        skip_build=skip_build,
        skip_distribute=skip_distribute,
        no_push=no_push,
    )

    all_ok = all(results.values())
    raise typer.Exit(0 if all_ok else 1)


@app.command()
def publish(
    version: str = typer.Option(
        None,
        "--version",
        "-v",
        help="Exact version (e.g. 1.2.3+0). Interactive if omitted.",
    ),
    bump: str = typer.Option(
        None,
        "--bump",
        "-b",
        help="Auto-bump: patch, minor, or major.",
    ),
    no_push: bool = typer.Option(
        False, "--no-push", help="Commit and tag locally only, skip push"
    ),
):
    """Prepare package for publishing: version bump, changelog, commit, tag, and push.

    No build or Firebase distribution. Use before dart pub publish.

    Examples:
        fship publish --bump patch         # Auto-bump patch, commit, tag, push
        fship publish --version 1.2.3+0   # Exact version
        fship publish --no-push            # Commit + tag locally, no push
    """
    try:
        if bump:
            validate_bump_part(bump)
        if version and bump:
            raise ValidationError("Cannot specify both --version and --bump")
    except FshipError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    success = run_publish(version=version, bump=bump, no_push=no_push)
    raise typer.Exit(0 if success else 1)


@app.command()
def init(interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive setup with Firebase app ID guide")):
    """Initialize fship config and setup Firebase app IDs."""
    from rich.prompt import Prompt

    CONFIG_DIR.mkdir(exist_ok=True)

    if CONFIG_FILE.exists():
        console.print(f"[dim]{CONFIG_FILE} already exists.[/dim]")
        overwrite = Prompt.ask("[yellow]Overwrite?[/yellow]", choices=["y", "n"], default="n")
        if overwrite != "y":
            return

    console.rule("[bold cyan]fship Setup[/bold cyan]")
    console.print()

    config = DEFAULT_CFG.copy()
    config["flavors"] = {}

    if interactive:
        console.print("[bold]Step 1: Configure Flavors[/bold]")
        console.print("[dim]Add flavors (qa, uat, prod, or custom)[/dim]\n")

        flavors = Prompt.ask(
            "Flavors (comma-separated)",
            default="qa,uat,prod"
        )

        for flavor in [f.strip() for f in flavors.split(",") if f.strip()]:
            console.print(f"\n[bold blue]→ {flavor.upper()}[/bold blue]")

            entrypoint = Prompt.ask(
                "  Dart entrypoint path",
                default=f"lib/main_{flavor}.dart"
            )

            apk_path = Prompt.ask(
                "  APK output path",
                default=f"build/app/outputs/flutter-apk/app-{flavor}-release.apk"
            )

            ipa_path = Prompt.ask(
                "  IPA output path (iOS)",
                default=f"build/ios/ipa/fship-{flavor}-release.ipa"
            )

            groups = Prompt.ask(
                "  Firebase distribution groups",
                default="testers"
            )

            config["flavors"][flavor] = {
                "firebase_app_id_env_android": "APPIDANDROID",
                "firebase_app_id_env_ios": "APPIDIOS",
                "entrypoint": entrypoint,
                "apk_path": apk_path,
                "ipa_path": ipa_path,
                "groups": groups,
            }

        console.print("\n[bold]Step 2: Get Firebase App IDs[/bold]")
        console.print()
        _print_firebase_setup_guide(config)

        console.print("\n[bold]Step 3: Set Environment Variables[/bold]")
        _print_env_setup(config)

    else:
        config = DEFAULT_CFG

    save_config(config)
    console.print(f"\n[green]✓[/green] Config saved to {CONFIG_FILE}")


def _print_firebase_setup_guide(config: dict) -> None:
    """Print guide for getting Firebase app IDs."""
    console.print("[yellow]Get your Firebase App IDs:[/yellow]\n")
    console.print("1. Go to [cyan]Firebase Console[/cyan]: https://console.firebase.google.com")
    console.print("2. Select your project")
    console.print("3. Click [bold]Project Settings[/bold] (gear icon)")
    console.print("4. Select [bold]Your apps[/bold] tab")
    console.print("5. Find your Android app and click it")
    console.print("6. Copy the [bold]Google App ID[/bold] (format: [dim]1:123456789:android:abcdef...[/dim])")
    console.print()
    console.print("[bold]App IDs needed for:[/bold]")
    for flavor, cfg in config.get("flavors", {}).items():
        android_key = cfg.get("firebase_app_id_env_android", "APPIDANDROID")
        ios_key = cfg.get("firebase_app_id_env_ios", "APPIDIOS")
        console.print(f"  {flavor:8} → {android_key} + {ios_key}")


def _print_env_setup(config: dict) -> None:
    """Print instructions for setting up environment variables."""
    console.print("[yellow]Option 1: Use .env.dev (single file for dev)[/yellow]\n")
    console.print("Create [bold].env.dev[/bold]:")
    console.print(f"  [cyan]APPIDANDROID[/cyan]=1:123456789:android:abcdef...")
    console.print(f"  [cyan]APPIDIOS[/cyan]=1:987654321:ios:fedcba...")
    console.print()

    console.print("[yellow]Option 2: Use flavor-specific files (recommended for CI/CD)[/yellow]\n")
    console.print("Flavor determined by filename (.env.{flavor}):\n")
    for flavor in config.get("flavors", {}).keys():
        console.print(f"Create [bold].env.{flavor}[/bold]:")
        console.print(f"  [cyan]APPIDANDROID[/cyan]=1:123456789:android:abcdef...")
        console.print(f"  [cyan]APPIDIOS[/cyan]=1:987654321:ios:fedcba...\n")

    console.print("[yellow]Option 3: Export as environment variables[/yellow]\n")
    console.print("In your shell:")
    console.print(f"  [dim]export APPIDANDROID='1:123456789:android:abcdef...'[/dim]")
    console.print(f"  [dim]export APPIDIOS='1:987654321:ios:fedcba...'[/dim]")
    console.print()

    console.print("[green]✓[/green] Run [cyan]fship validate[/cyan] after setup to verify")


@app.command()
def validate():
    """Validate config and required tools."""
    try:
        config = load_config()
        console.print(f"[green]✓[/green] Config loaded from {CONFIG_FILE}\n")

        console.print("[bold]Configured Flavors:[/bold]")
        for flavor, cfg in config.flavors.items():
            console.print(f"  [cyan]{flavor}:[/cyan] {cfg.entrypoint}")

            android_id = os.getenv(cfg.firebase_app_id_env_android)
            ios_id = os.getenv(cfg.firebase_app_id_env_ios)

            if android_id:
                console.print(f"    [green]✓[/green] {cfg.firebase_app_id_env_android} (Android)")
            else:
                console.print(f"    [yellow]⚠[/yellow] {cfg.firebase_app_id_env_android} not set")

            if ios_id:
                console.print(f"    [green]✓[/green] {cfg.firebase_app_id_env_ios} (iOS)")
            else:
                console.print(f"    [yellow]⚠[/yellow] {cfg.firebase_app_id_env_ios} not set")

    except Exception as e:
        console.print(f"[red]✗ Config validation failed: {e}[/red]")
        raise typer.Exit(1)

    tools = [
        ("flutter", "flutter --version"),
        ("firebase", "firebase --version"),
        ("git", "git --version"),
        ("git-chglog", "git-chglog --version"),
    ]

    console.print("\n[bold]Checking Tools:[/bold]")
    import subprocess

    for tool, cmd in tools:
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                console.print(f"[green]✓[/green] {tool}")
            else:
                console.print(f"[yellow]⚠[/yellow] {tool} (not working)")
        except FileNotFoundError:
            console.print(f"[red]✗[/red] {tool} (not found)")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] {tool} ({e})")


@app.command()
def help():
    """Show detailed help with all commands and options."""
    from fship import __version__

    console.print(f"\n[bold cyan]fship {__version__}[/bold cyan] — Flutter Ship Release Orchestration")
    console.print("[dim]Automate Flutter releases to Firebase App Distribution[/dim]\n")

    console.print("[bold]COMMANDS[/bold]")
    console.print("  [cyan]release[/cyan]         Release a flavor (version bump, build, distribute)")
    console.print("  [cyan]publish[/cyan]         Prepare package for pub.dev (version bump, changelog, commit & tag)")
    console.print("  [cyan]multi-release[/cyan]   Release multiple flavors in sequence")
    console.print("  [cyan]status[/cyan]          Show current version, last release, pending commits")
    console.print("  [cyan]pre-check[/cyan]       Validate Flutter, Firebase, credentials before release")
    console.print("  [cyan]init[/cyan]            Interactive setup with Firebase app ID guide")
    console.print("  [cyan]validate[/cyan]        Check tools, config, and environment")
    console.print("  [cyan]version[/cyan]         Show fship version")
    console.print("  [cyan]help[/cyan]            Show this help message\n")

    console.print("[bold]RELEASE OPTIONS[/bold]")
    console.print("  [cyan]fship release <flavor> [OPTIONS][/cyan]\n")
    console.print("  [yellow]<flavor>[/yellow]                Required: qa, uat, prod, or custom")
    console.print("  [yellow]--version, -v VERSION[/yellow]   Exact version (e.g., 3.0.4+79)")
    console.print("  [yellow]--bump, -b PART[/yellow]         Auto-bump: patch, minor, or major")
    console.print("  [yellow]--skip-build[/yellow]            Skip Flutter build")
    console.print("  [yellow]--skip-distribute[/yellow]       Skip Firebase distribution")
    console.print("  [yellow]--no-push[/yellow]               Commit and tag locally, don't push")
    console.print("  [yellow]--resume-from STEP[/yellow]      Retry from step after failure")
    console.print("  [dim]                        Steps: version, changelog, notes, tag, build, distribute[/dim]\n")

    console.print("[bold]RELEASE EXAMPLES[/bold]")
    console.print("  [dim]# Interactive version selection[/dim]")
    console.print("  fship release qa\n")
    console.print("  [dim]# Exact version[/dim]")
    console.print("  fship release qa --version 3.0.4+79\n")
    console.print("  [dim]# Auto-bump patch[/dim]")
    console.print("  fship release qa --bump patch\n")
    console.print("  [dim]# Dry run (version + tag only, no build)[/dim]")
    console.print("  fship release qa --skip-build --skip-distribute\n")
    console.print("  [dim]# Retry distribution after fixing app ID[/dim]")
    console.print("  fship release qa --resume-from distribute\n")
    console.print("  [dim]# Prod release (pure semantic X.Y.Z+0)[/dim]")
    console.print("  fship release prod --bump patch\n")
    console.print("  [dim]# Parallel Android + iOS builds[/dim]")
    console.print("  FSHIP_PARALLEL_BUILDS=1 fship release qa\n")

    console.print("[bold]PUBLISH (package, no build/distribute)[/bold]")
    console.print("  [cyan]fship publish [OPTIONS][/cyan]\n")
    console.print("  [yellow]--version, -v VERSION[/yellow]   Exact version (e.g., 1.2.3+0)")
    console.print("  [yellow]--bump, -b PART[/yellow]         Auto-bump: patch, minor, or major")
    console.print("  [yellow]--no-push[/yellow]               Commit and tag locally, don't push\n")
    console.print("[bold]PUBLISH EXAMPLES[/bold]")
    console.print("  [dim]# Auto-bump patch and prepare for pub.dev[/dim]")
    console.print("  fship publish --bump patch\n")
    console.print("  [dim]# Exact version[/dim]")
    console.print("  fship publish --version 1.2.3+0\n")
    console.print("  [dim]# Commit and tag locally only[/dim]")
    console.print("  fship publish --bump minor --no-push\n")

    console.print("[bold]MULTI-RELEASE[/bold]")
    console.print("  [cyan]fship multi-release qa,uat --bump patch[/cyan]")
    console.print("  [dim]Releases qa then uat, shows per-flavor summary[/dim]\n")

    console.print("[bold]STATUS & CHECKS[/bold]")
    console.print("  [cyan]fship status qa[/cyan]        Current version, last tag, pending commits")
    console.print("  [cyan]fship pre-check qa[/cyan]     Flutter, Firebase CLI, credentials, APK path\n")

    console.print("[bold]VERSION FORMATS[/bold]")
    console.print("  [cyan]Prod:[/cyan]      X.Y.Z+0          (e.g., 3.0.5+0  — no suffix)")
    console.print("  [cyan]Non-prod:[/cyan]  X.Y.Z-suffix+B   (e.g., 3.0.4-qa-2+79)")
    console.print("             X.Y.Z+B          (auto-adds flavor suffix on bump)\n")

    console.print("[bold]AUTO-ROLLBACK[/bold]")
    console.print("  If distribution fails after commit/tag, fship reverts:")
    console.print("  • pubspec.yaml version")
    console.print("  • git commit (reset --soft)")
    console.print("  • git tag (deleted)")
    console.print("  Fix the issue and retry with [cyan]--resume-from distribute[/cyan]\n")

    console.print("[bold]ENVIRONMENT FILES[/bold]")
    console.print("  .env.qa / .env.uat / .env.prod   Per-flavor Firebase app IDs")
    console.print("  APPIDANDROID                      Firebase App ID for Android")
    console.print("  APPIDIOS                          Firebase App ID for iOS")
    console.print("  FSHIP_PARALLEL_BUILDS=1           Enable parallel APK+IPA builds\n")
    console.print("  [dim]Example .env.qa:[/dim]")
    console.print("  APPIDANDROID=1:123456:android:abcdef...")
    console.print("  APPIDIOS=1:987654:ios:fedcba...\n")

    console.print("[bold]SETUP[/bold]")
    console.print("  fship init              Interactive setup")
    console.print("  fship validate          Check all tools and config")
    console.print("  fship pre-check qa      Pre-flight checks before release\n")


@app.command()
def version():
    """Show fship version."""
    from fship import __version__

    console.print(f"fship {__version__}")


if __name__ == "__main__":
    app()
