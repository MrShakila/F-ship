import json
import sys
from dataclasses import dataclass
from pathlib import Path
from rich.console import Console

console = Console()

CONFIG_DIR = Path.cwd() / ".config"
CONFIG_FILE = CONFIG_DIR / "fship.json"

DEFAULT_CFG = {
    "flavors": {
        "qa": {
            "firebase_app_id_env": "FIREBASE_QA_APP_ID",
            "entrypoint": "lib/main_qa.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-qa-release.apk",
            "groups": "testers",
        },
        "uat": {
            "firebase_app_id_env": "FIREBASE_UAT_APP_ID",
            "entrypoint": "lib/main_uat.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-uat-release.apk",
            "groups": "testers",
        },
        "prod": {
            "firebase_app_id_env": "FIREBASE_PROD_APP_ID",
            "entrypoint": "lib/main_prod.dart",
            "apk_path": "build/app/outputs/flutter-apk/app-prod-release.apk",
            "groups": "testers",
        },
    }
}


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
