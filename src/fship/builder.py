import subprocess
from pathlib import Path
from rich.console import Console

console = Console()


def build_apk(flavor: str, entrypoint: str) -> tuple[bool, str]:
    """Build Flutter APK for flavor."""
    cmd = [
        "flutter",
        "build",
        "apk",
        "--flavor",
        flavor,
        "-t",
        entrypoint,
    ]

    try:
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            console.print(
                f"[red]✗ Flutter build failed:[/red]\n{result.stderr[:500]}"
            )
            return False, ""

        console.print("[green]✓[/green] APK built successfully")

        apk_path = find_built_apk(flavor)
        if apk_path:
            console.print(f"[green]✓[/green] Found APK: {apk_path}")
            return True, str(apk_path)
        else:
            console.print(
                "[yellow]Warning: Could not locate built APK. Check build output.[/yellow]"
            )
            return True, ""

    except FileNotFoundError:
        console.print(
            "[red]✗ Flutter not found. Install Flutter SDK or add to PATH.[/red]"
        )
        return False, ""
    except Exception as e:
        console.print(f"[red]✗ Build failed: {e}[/red]")
        return False, ""


def find_built_apk(flavor: str) -> Path | None:
    """Try to locate the built APK by checking standard paths."""
    standard_paths = [
        f"build/app/outputs/flutter-apk/app-{flavor}-release.apk",
        f"build/app/outputs/apk/{flavor}/release/app-{flavor}-release.apk",
        f"build/app/outputs/apk/release/app-release.apk",
    ]

    for p in standard_paths:
        path = Path(p)
        if path.exists():
            return path

    return None
