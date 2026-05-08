"""Configuration management with validation."""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from rich.console import Console

from fship.errors import ConfigError
from fship.validation import validate_flavor_exists

console = Console()

CONFIG_DIR = Path.cwd() / ".config"
CONFIG_FILE = CONFIG_DIR / "fship.json"
ENV_FILE = Path.cwd() / ".env.dev"

DEFAULT_CFG = {
    "flavors": {
        "qa": {
            "firebase_app_id_env": "APPIDANDROID",
            "entrypoint": "lib/main_qa.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-qa-release.apk",
            "groups": "testers",
        },
        "uat": {
            "firebase_app_id_env": "APPIDANDROID",
            "entrypoint": "lib/main_uat.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-uat-release.apk",
            "groups": "testers",
        },
        "prod": {
            "firebase_app_id_env": "APPIDANDROID",
            "entrypoint": "lib/main_prod.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-prod-release.apk",
            "groups": "testers",
        },
    }
}


def load_env_file() -> None:
    """Load environment variables from .env.* files (dev, qa, uat, prod)."""
    env_files = [
        Path.cwd() / ".env.dev",
        Path.cwd() / ".env.qa",
        Path.cwd() / ".env.uat",
        Path.cwd() / ".env.prod",
    ]

    if not any(f.exists() for f in env_files):
        _create_env_template()
        return

    loaded = []
    for env_file in env_files:
        if not env_file.exists():
            continue
        try:
            for line in env_file.read_text().strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip("'\"")
            loaded.append(env_file.name)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load {env_file}: {e}[/yellow]")

    if loaded:
        console.print(f"[dim]Loaded env from: {', '.join(loaded)}[/dim]")


def _create_env_template() -> None:
    """Create .env.dev template and prompt user to fill in Android app IDs."""
    template = """# Firebase Android App ID
# Same variable for all flavors (flavor determined by .env file)
# Get this from Firebase Console > App settings

APPIDANDROID=
"""
    ENV_FILE.write_text(template)
    console.print(f"[yellow]⚠  Created template: {ENV_FILE}[/yellow]")
    console.print(f"[yellow]Setup options:[/yellow]")
    console.print(f"[dim]Option 1: One file for all flavors (.env.dev)[/dim]")
    console.print(f"[dim]  APPIDANDROID_QA=1:123456:android:abcdef...[/dim]")
    console.print(f"[dim]  APPIDANDROID_UAT=1:345678:android:ghijkl...[/dim]")
    console.print(f"[dim]  APPIDANDROID_PROD=1:789012:android:mnopqr...[/dim]")
    console.print(f"[dim]Option 2: Flavor-specific files (.env.qa, .env.uat, .env.prod)[/dim]")
    console.print(f"[dim]  .env.qa:   APPIDANDROID_QA=1:123456:android:abcdef...[/dim]")
    console.print(f"[dim]  .env.uat:  APPIDANDROID_UAT=1:345678:android:ghijkl...[/dim]")
    console.print(f"[dim]  .env.prod: APPIDANDROID_PROD=1:789012:android:mnopqr...[/dim]")
    console.print(f"[dim]Get values from: Firebase Console > App settings[/dim]")
    console.print()
    raise SystemExit("Configure .env files and run again")


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
        raise ConfigError(f"Invalid JSON in {CONFIG_FILE}: {e}")

    flavors = {}
    for flavor_name, flavor_data in cfg.get("flavors", {}).items():
        try:
            flavors[flavor_name] = FlavorConfig(
                firebase_app_id_env=flavor_data["firebase_app_id_env"],
                entrypoint=flavor_data["entrypoint"],
                apk_path=flavor_data["apk_path"],
                groups=flavor_data.get("groups", "testers"),
            )
        except KeyError as e:
            raise ConfigError(
                f"Missing required key in flavor {flavor_name!r}: {e}"
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

    try:
        content = gitignore.read_text()
        if ".config/" not in content:
            gitignore.write_text(content.rstrip() + "\n.config/\n")
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to update .gitignore: {e}[/yellow]")


def get_flavor(config: Config, flavor: str) -> FlavorConfig:
    """Get flavor config with validation.

    Raises:
        ConfigError: If flavor not found
    """
    try:
        validate_flavor_exists(flavor, {"flavors": config.flavors})
        return config.flavors[flavor]
    except Exception as e:
        raise ConfigError(str(e))
