"""Firebase App Distribution."""

import os
import subprocess
from pathlib import Path
from rich.console import Console

from fship.errors import DistributionError
from fship.validation import validate_firebase_app_id, validate_file_exists

console = Console()


def distribute_to_firebase(
    apk_path: str,
    firebase_app_id_env_android: str,
    groups: str = "testers",
    release_notes_file: str = "release_note.txt",
) -> bool:
    """Distribute APK to Firebase App Distribution.

    Args:
        apk_path: Path to APK file
        firebase_app_id_env_android: Environment variable name for Android app ID
        groups: Comma-separated groups to distribute to
        release_notes_file: Path to release notes file

    Raises:
        DistributionError: If distribution fails
    """
    app_id = os.getenv(firebase_app_id_env_android)

    if not app_id:
        raise DistributionError(
            f"Environment variable {firebase_app_id_env_android} not set. "
            f"Add to .env.dev: {firebase_app_id_env_android}=<your-app-id>"
        )

    try:
        validate_firebase_app_id(app_id)
        validate_file_exists(apk_path, "APK")
    except Exception as e:
        raise DistributionError(str(e)) from e

    cmd = [
        "firebase",
        "appdistribution:distribute",
        apk_path,
        "--app",
        app_id,
        "--groups",
        groups,
    ]

    if Path(release_notes_file).exists():
        cmd.extend(["--release-notes-file", release_notes_file])
    else:
        console.print(
            f"[yellow]Warning: {release_notes_file} not found. "
            "Distributing without notes.[/yellow]"
        )

    try:
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
        console.print("[cyan]Uploading to Firebase...[/cyan]")

        result = subprocess.run(cmd, capture_output=False, text=True, check=False)

        if result.returncode != 0:
            console.print(f"[red]✗ Firebase distribution failed[/red]")
            return False

        console.print("[green]✓[/green] APK distributed to Firebase")
        return True

    except FileNotFoundError as e:
        raise DistributionError(
            "Firebase CLI not found. Install: npm install -g firebase-tools"
        ) from e
    except Exception as e:
        raise DistributionError(f"Distribution failed: {e}") from e
