import os
import subprocess
from pathlib import Path
from rich.console import Console

console = Console()


def distribute_to_firebase(
    apk_path: str,
    firebase_app_id_env: str,
    groups: str = "testers",
    release_notes_file: str = "release_note.txt",
) -> bool:
    """Distribute APK to Firebase App Distribution."""
    app_id = os.getenv(firebase_app_id_env)

    if not app_id:
        console.print(
            f"[red]✗ Environment variable {firebase_app_id_env} not set.[/red]\n"
            f"[dim]Export it: export {firebase_app_id_env}=<your-app-id>[/dim]"
        )
        return False

    if not Path(apk_path).exists():
        console.print(f"[red]✗ APK not found: {apk_path}[/red]")
        return False

    if not Path(release_notes_file).exists():
        console.print(
            f"[yellow]Warning: {release_notes_file} not found. Distributing without notes.[/yellow]"
        )
        cmd = [
            "firebase",
            "appdistribution:distribute",
            apk_path,
            "--app",
            app_id,
            "--groups",
            groups,
        ]
    else:
        cmd = [
            "firebase",
            "appdistribution:distribute",
            apk_path,
            "--app",
            app_id,
            "--release-notes-file",
            release_notes_file,
            "--groups",
            groups,
        ]

    try:
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            console.print(
                f"[red]✗ Firebase distribution failed:[/red]\n{result.stderr[:500]}"
            )
            return False

        console.print("[green]✓[/green] APK distributed to Firebase")
        if "share-link" in result.stdout or "http" in result.stdout:
            console.print(f"[dim]{result.stdout}[/dim]")
        return True

    except FileNotFoundError:
        console.print(
            "[red]✗ Firebase CLI not found. Install: npm install -g firebase-tools[/red]"
        )
        return False
    except Exception as e:
        console.print(f"[red]✗ Distribution failed: {e}[/red]")
        return False
