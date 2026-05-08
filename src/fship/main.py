import typer
import os
import subprocess
import sys
from pathlib import Path
from rich.console import Console

from fship.core import load_config, get_flavor
from fship.core.config import CONFIG_FILE, CONFIG_DIR, DEFAULT_CFG, save_config
from fship.runner import run_release
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
):
    """Release a flavor to Firebase App Distribution.

    Examples:
        fship release qa                    # Interactive version prompt
        fship release qa --version 1.2.4+46  # Exact version
        fship release qa --bump patch       # Auto-bump patch version
        fship release prod --bump minor     # Bump minor, reset patch
    """
    try:
        config = load_config()
        flavor_config = get_flavor(config, flavor)

        if bump:
            validate_bump_part(bump)
        if version and bump:
            raise ValidationError("Cannot specify both --version and --bump")
    except FshipError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    success = run_release(
        flavor,
        flavor_config,
        version=version,
        bump=bump,
        skip_build=skip_build,
        skip_distribute=skip_distribute,
    )

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
def version():
    """Show fship version."""
    from fship import __version__

    console.print(f"fship {__version__}")


if __name__ == "__main__":
    app()
