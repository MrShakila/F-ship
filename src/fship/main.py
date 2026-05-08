import typer
import os
import json
import sys
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from fship.config import load_config, get_flavor, CONFIG_FILE, CONFIG_DIR, save_config, DEFAULT_CFG
from fship.runner import run_release

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
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    if bump and version:
        console.print("[red]Error: Cannot specify both --version and --bump[/red]")
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
def configure():
    """Interactive setup: configure flavors and app IDs."""
    CONFIG_DIR.mkdir(exist_ok=True)

    if CONFIG_FILE.exists():
        overwrite = Prompt.ask(
            f"{CONFIG_FILE} already exists. Overwrite?",
            choices=["y", "n"],
            default="n",
        )
        if overwrite == "n":
            console.print("[dim]Using existing config.[/dim]")
            return

    console.rule("[bold cyan]fship Configure[/bold cyan]")
    console.print("Configure your Flutter release flavors.\n")

    cfg = {"flavors": {}}

    while True:
        flavor_name = Prompt.ask("Flavor name (e.g. qa, uat, prod, or done to finish)")

        if flavor_name.lower() == "done":
            break

        console.print(f"\n[cyan]{flavor_name}:[/cyan]")
        firebase_app_id_env = Prompt.ask(
            "  Firebase app ID env var",
            default=f"FIREBASE_{flavor_name.upper()}_APP_ID",
        )
        entrypoint = Prompt.ask(
            "  Entry point", default=f"lib/main_{flavor_name}.dart"
        )
        apk_path = Prompt.ask(
            "  APK path",
            default=f"build/app/outputs/flutter-apk/app-{flavor_name}-release.apk",
        )
        groups = Prompt.ask("  Firebase groups", default="testers")

        cfg["flavors"][flavor_name] = {
            "firebase_app_id_env": firebase_app_id_env,
            "entrypoint": entrypoint,
            "apk_path": apk_path,
            "groups": groups,
        }

        console.print(f"[green]✓[/green] Added {flavor_name}\n")

    if not cfg["flavors"]:
        console.print("[red]No flavors configured. Aborting.[/red]")
        raise typer.Exit(1)

    save_config(cfg)
    console.print(f"\n[green]✓ Config saved to {CONFIG_FILE}[/green]")


@app.command()
def validate():
    """Validate config and required tools."""
    try:
        config = load_config()
        console.print(f"[green]✓[/green] Config loaded from {CONFIG_FILE}\n")

        console.print("[bold]Configured Flavors:[/bold]")
        for flavor, cfg in config.flavors.items():
            console.print(f"  [cyan]{flavor}:[/cyan] {cfg.entrypoint}")
            app_id = os.getenv(cfg.firebase_app_id_env)
            if app_id:
                console.print(f"    [green]✓[/green] {cfg.firebase_app_id_env} set")
            else:
                console.print(
                    f"    [yellow]⚠[/yellow] {cfg.firebase_app_id_env} not set"
                )

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
