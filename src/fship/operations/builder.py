"""Flutter APK/IPA/AAB building."""

import subprocess
from pathlib import Path
from rich.console import Console

from fship.errors import BuildError
from fship.validation import validate_path_within_project

console = Console()


def build_apk(flavor: str, entrypoint: str) -> tuple[bool, str]:
    """Build Flutter APK for flavor.

    Args:
        flavor: Flavor name
        entrypoint: Path to entrypoint dart file

    Returns:
        (success, apk_path)

    Raises:
        BuildError: If build fails
    """
    try:
        validate_path_within_project(entrypoint)
    except Exception as e:
        raise BuildError(f"Invalid entrypoint path: {e}")

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
        console.print("[cyan]Building...[/cyan]")

        result = subprocess.run(cmd, check=False)

        if result.returncode != 0:
            console.print(f"[red]✗ Flutter build failed[/red]")
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

    except FileNotFoundError as e:
        raise BuildError(
            "Flutter not found. Install Flutter SDK or add to PATH."
        ) from e
    except Exception as e:
        raise BuildError(f"Build failed: {e}") from e


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


def build_aab(flavor: str, entrypoint: str) -> tuple[bool, str]:
    """Build Flutter Android App Bundle (AAB) for Play Store.

    Returns:
        (success, aab_path)
    """
    try:
        validate_path_within_project(entrypoint)
    except Exception as e:
        raise BuildError(f"Invalid entrypoint path: {e}")

    cmd = [
        "flutter",
        "build",
        "appbundle",
        "--flavor",
        flavor,
        "-t",
        entrypoint,
    ]

    try:
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
        console.print("[cyan]Building AAB...[/cyan]")

        result = subprocess.run(cmd, check=False)

        if result.returncode != 0:
            console.print("[red]✗ AAB build failed[/red]")
            return False, ""

        console.print("[green]✓[/green] AAB built successfully")

        aab_path = find_built_aab(flavor)
        if aab_path:
            console.print(f"[green]✓[/green] Found AAB: {aab_path}")
            return True, str(aab_path)
        else:
            console.print("[yellow]Warning: Could not locate AAB. Check build output.[/yellow]")
            return True, ""

    except FileNotFoundError as e:
        raise BuildError("Flutter not found. Install Flutter SDK or add to PATH.") from e
    except Exception as e:
        raise BuildError(f"AAB build failed: {e}") from e


def find_built_aab(flavor: str) -> Path | None:
    """Try to locate the built AAB by checking standard paths."""
    standard_paths = [
        f"build/app/outputs/bundle/{flavor}Release/app-{flavor}-release.aab",
        f"build/app/outputs/bundle/release/app-release.aab",
    ]

    for p in standard_paths:
        path = Path(p)
        if path.exists():
            return path

    return None


def build_ipa(flavor: str, entrypoint: str, export_method: str = None) -> tuple[bool, str]:
    """Build Flutter IPA for iOS.

    Args:
        export_method: 'ad-hoc' for Firebase distribution, 'app-store' for prod

    Returns:
        (success, ipa_path)
    """
    try:
        validate_path_within_project(entrypoint)
    except Exception as e:
        raise BuildError(f"Invalid entrypoint path: {e}")

    cmd = [
        "flutter",
        "build",
        "ipa",
        "--flavor",
        flavor,
        "-t",
        entrypoint,
    ]

    if export_method:
        cmd.extend(["--export-method", export_method])

    try:
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
        console.print("[cyan]Building IPA...[/cyan]")

        result = subprocess.run(cmd, check=False)

        if result.returncode != 0:
            console.print("[red]✗ IPA build failed[/red]")
            return False, ""

        ipa_path = find_built_ipa(flavor)
        if ipa_path:
            console.print("[green]✓[/green] IPA built successfully")
            console.print(f"[green]✓[/green] Found IPA: {ipa_path}")
            return True, str(ipa_path)
        else:
            console.print("[red]✗ IPA export failed — .ipa file not created[/red]")
            console.print("[dim]Check: signing certificate, provisioning profile, Apple account in Xcode[/dim]")
            return False, ""

    except FileNotFoundError as e:
        raise BuildError("Flutter not found. Install Flutter SDK or add to PATH.") from e
    except Exception as e:
        raise BuildError(f"IPA build failed: {e}") from e


def find_built_ipa(flavor: str) -> Path | None:
    """Try to locate the built IPA by checking standard paths."""
    standard_paths = [
        f"build/ios/ipa/{flavor}.ipa",
        f"build/ios/ipa/Runner.ipa",
    ]

    for p in standard_paths:
        path = Path(p)
        if path.exists():
            return path

    return None
