import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from rich.console import Console

console = Console()

CONFIG_DIR = Path.cwd() / ".config"
CONFIG_FILE = CONFIG_DIR / "fship.json"
ENV_FILE = Path.cwd() / ".env.dev"

DEFAULT_CFG = {
    "flavors": {
        "qa": {
            "firebase_app_id_env": "APPIDANDROID_QA",
            "entrypoint": "lib/main_qa.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-qa-release.apk",
            "groups": "testers",
        },
        "uat": {
            "firebase_app_id_env": "APPIDANDROID_UAT",
            "entrypoint": "lib/main_uat.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-uat-release.apk",
            "groups": "testers",
        },
        "prod": {
            "firebase_app_id_env": "APPIDANDROID_PROD",
            "entrypoint": "lib/main_prod.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-prod-release.apk",
            "groups": "testers",
        },
    }
}


def load_env_file() -> None:
    """Load environment variables from .env.dev if it exists."""
    if not ENV_FILE.exists():
        _create_env_template()
        return

    try:
        for line in ENV_FILE.read_text().strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip("'\"")
        console.print(f"[dim]Loaded env from {ENV_FILE}[/dim]")
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to load {ENV_FILE}: {e}[/yellow]")


def _create_env_template() -> None:
    """Create .env.dev template and prompt user to fill in Android app IDs."""
    template = """# Firebase Android App IDs for each flavor
# Get these from Firebase Console > App settings

APPIDANDROID_QA=
APPIDANDROID_UAT=
APPIDANDROID_PROD=
"""
    ENV_FILE.write_text(template)
    console.print(f"[yellow]⚠  Created template: {ENV_FILE}[/yellow]")
    console.print(f"[yellow]Please edit and add your Android app IDs:[/yellow]")
    console.print(f"[dim]  APPIDANDROID_QA=1:123456:android:abcdef...[/dim]")
    console.print(f"[dim]  APPIDANDROID_UAT=1:345678:android:ghijkl...[/dim]")
    console.print(f"[dim]  APPIDANDROID_PROD=1:789012:android:mnopqr...[/dim]")
    console.print(f"[dim]Get values from: Firebase Console > App settings[/dim]")
    console.print()
    raise SystemExit("Configure .env.dev and run again")


@dataclass
class FlavorConfig:
    firebase_app_id_env: str
    entrypoint: str
    apk_path: str
    groups: str


@dataclass
class Config:
    flavors: dict[str, FlavorConfig]


def load_config() -> Config:
    """Load config from .config/fship.json or create with defaults."""
    load_env_file()
    CONFIG_DIR.mkdir(exist_ok=True)

    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CFG, indent=2))
        _ensure_gitignore()

    try:
        cfg = {**DEFAULT_CFG, **json.loads(CONFIG_FILE.read_text())}
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON in {CONFIG_FILE}: {e}[/red]")
        raise

    flavors = {}
    for flavor_name, flavor_data in cfg.get("flavors", {}).items():
        flavors[flavor_name] = FlavorConfig(
            firebase_app_id_env=flavor_data["firebase_app_id_env"],
            entrypoint=flavor_data["entrypoint"],
            apk_path=flavor_data["apk_path"],
            groups=flavor_data.get("groups", "testers"),
        )

    return Config(flavors=flavors)


def save_config(config: dict) -> None:
    """Save config to .config/fship.json."""
    CONFIG_DIR.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    _ensure_gitignore()
    console.print(f"[green]✓[/green] Config saved to {CONFIG_FILE}")


def _ensure_gitignore() -> None:
    """Add .config/ to .gitignore if git repo exists."""
    gitignore = Path.cwd() / ".gitignore"
    if not gitignore.exists():
        return

    content = gitignore.read_text()
    if ".config/" not in content:
        gitignore.write_text(content.rstrip() + "\n.config/\n")


def require_config(*keys: str) -> dict:
    """Load config and exit if required keys missing."""
    cfg = load_config()
    missing = [k for k in keys if k not in cfg.flavors]
    if missing:
        console.print(f"[red]✗ Missing flavors: {', '.join(missing)}[/red]")
        console.print(f"[dim]Edit: {CONFIG_FILE}[/dim]")
        sys.exit(1)
    return cfg.__dict__


def get_flavor(config: Config, flavor: str) -> FlavorConfig:
    if flavor not in config.flavors:
        available = ", ".join(config.flavors.keys())
        raise ValueError(f"Unknown flavor '{flavor}'. Available: {available}")
    return config.flavors[flavor]
