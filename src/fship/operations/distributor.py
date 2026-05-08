"""Firebase App Distribution."""

import os
import subprocess
from pathlib import Path
from rich.console import Console

from fship.errors import DistributionError
from fship.validation import validate_firebase_app_id, validate_file_exists

console = Console()


def distribute_to_firebase(
    artifact_path: str,
    firebase_app_id_env: str,
    groups: str = "testers",
    release_notes_file: str = "release_note.txt",
    artifact_label: str = "APK",
) -> bool:
    """Distribute APK or IPA to Firebase App Distribution.

    Args:
        artifact_path: Path to APK or IPA file
        firebase_app_id_env: Environment variable name for Firebase app ID
        groups: Comma-separated groups to distribute to
        release_notes_file: Path to release notes file
        artifact_label: Display label for the artifact ("APK" or "IPA")

    Raises:
        DistributionError: If distribution fails
    """
    app_id = os.getenv(firebase_app_id_env)

    if not app_id:
        raise DistributionError(
            f"Environment variable {firebase_app_id_env} not set. "
            f"Add to .env.{{flavor}}: {firebase_app_id_env}=<your-app-id>"
        )

    masked = app_id[:12] + "..." + app_id[-6:] if len(app_id) > 18 else app_id
    console.print(f"[dim]Using {firebase_app_id_env}: {masked}[/dim]")

    try:
        validate_firebase_app_id(app_id)
        validate_file_exists(artifact_path, artifact_label)
    except Exception as e:
        raise DistributionError(str(e)) from e

    cmd = [
        "firebase",
        "appdistribution:distribute",
        artifact_path,
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
        console.print(f"[cyan]Uploading {artifact_label} to Firebase...[/cyan]")

        result = subprocess.run(cmd, capture_output=False, text=True, check=False)

        if result.returncode != 0:
            console.print(f"[red]✗ Firebase {artifact_label} distribution failed[/red]")
            return False

        console.print(f"[green]✓[/green] {artifact_label} distributed to Firebase")
        return True

    except FileNotFoundError as e:
        raise DistributionError(
            "Firebase CLI not found. Install: npm install -g firebase-tools"
        ) from e
    except Exception as e:
        raise DistributionError(f"Distribution failed: {e}") from e
