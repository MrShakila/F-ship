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
            "firebase_app_id_env_android": "APPIDANDROID",
            "firebase_app_id_env_ios": "APPIDIOS",
            "entrypoint": "lib/main_qa.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-qa-release.apk",
            "ipa_path": "build/ios/ipa/fship-qa-release.ipa",
            "groups": "testers",
        },
        "uat": {
            "firebase_app_id_env_android": "APPIDANDROID",
            "firebase_app_id_env_ios": "APPIDIOS",
            "entrypoint": "lib/main_uat.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-uat-release.apk",
            "ipa_path": "build/ios/ipa/fship-uat-release.ipa",
            "groups": "testers",
        },
        "prod": {
            "firebase_app_id_env_android": "APPIDANDROID",
            "firebase_app_id_env_ios": "APPIDIOS",
            "entrypoint": "lib/main_prod.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-prod-release.apk",
            "ipa_path": "build/ios/ipa/fship-prod-release.ipa",
            "groups": "testers",
        },
    }
}


def load_env_file(flavor: str = None) -> None:
    """Load environment variables from flavor-specific .env file.

    Args:
        flavor: Flavor name (qa, uat, prod, custom). If specified, loads ONLY that flavor's file.
                If None, loads all existing .env files (for validation/setup).
    """
    all_env_files = [
        Path.cwd() / ".env.dev",
        Path.cwd() / ".env.qa",
        Path.cwd() / ".env.uat",
        Path.cwd() / ".env.prod",
    ]

    if not any(f.exists() for f in all_env_files):
        _create_env_template()
        return

    # If flavor specified, load ONLY that flavor's env file
    if flavor:
        env_file = Path.cwd() / f".env.{flavor}"
        if not env_file.exists():
            return
        env_files_to_load = [env_file]
    else:
        # Load all existing env files (for validate command)
        env_files_to_load = [f for f in all_env_files if f.exists()]

    loaded = []
    for env_file in env_files_to_load:
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
    """Create .env.dev template and prompt user to fill in Firebase app IDs."""
    template = """# Firebase App IDs for Android and iOS
# Same variables for all flavors (flavor determined by .env file)
# Get these from Firebase Console > App settings

APPIDANDROID=
APPIDIOS=
"""
    ENV_FILE.write_text(template)
    console.print(f"[yellow]⚠  Created template: {ENV_FILE}[/yellow]")
    console.print(f"[yellow]Setup options:[/yellow]")
    console.print(f"[dim]Option 1: One file for all flavors (.env.dev)[/dim]")
    console.print(f"[dim]  APPIDANDROID=1:123456:android:abcdef...[/dim]")
    console.print(f"[dim]  APPIDIOS=1:987654:ios:fedcba...[/dim]")
    console.print(f"[dim]Option 2: Flavor-specific files (.env.qa, .env.uat, .env.prod)[/dim]")
    console.print(f"[dim]  .env.qa:   APPIDANDROID=1:123456:android:abcdef...[/dim]")
    console.print(f"[dim]           APPIDIOS=1:987654:ios:fedcba...[/dim]")
    console.print(f"[dim]  .env.uat:  APPIDANDROID=1:345678:android:ghijkl...[/dim]")
    console.print(f"[dim]           APPIDIOS=1:876543:ios:ihgfed...[/dim]")
    console.print(f"[dim]  .env.prod: APPIDANDROID=1:789012:android:mnopqr...[/dim]")
    console.print(f"[dim]           APPIDIOS=1:210987:ios:qponml...[/dim]")
    console.print(f"[dim]Get values from: Firebase Console > App settings[/dim]")
    console.print()
    raise SystemExit("Configure .env files and run again")


@dataclass
class FlavorConfig:
    firebase_app_id_env_android: str
    firebase_app_id_env_ios: str
    entrypoint: str
    apk_path: str
    ipa_path: str
    groups: str


@dataclass
class Config:
    flavors: dict[str, FlavorConfig]


def load_config(flavor: str = None) -> Config:
    """Load config from .config/fship.json or create with defaults.

    Args:
        flavor: Flavor name to load corresponding .env.{flavor} file. Falls back to .env.dev.
    """
    load_env_file(flavor)
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
                firebase_app_id_env_android=flavor_data.get(
                    "firebase_app_id_env_android", "APPIDANDROID"
                ),
                firebase_app_id_env_ios=flavor_data.get(
                    "firebase_app_id_env_ios", "APPIDIOS"
                ),
                entrypoint=flavor_data["entrypoint"],
                apk_path=flavor_data["apk_path"],
                ipa_path=flavor_data.get("ipa_path", ""),
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
