# fship — Flutter Ship

Memorable, easy CLI for orchestrating Flutter release workflows to Firebase App Distribution.

## Quick Reference

### Install
```bash
pip install fship
```

### Release
```bash
fship init                  # Create default config
fship release qa            # Interactive version prompt
fship release qa --bump patch    # Auto-bump patch
fship release qa --version 1.2.4+46  # Exact version
```

### Setup
1. `fship init` → creates `.config/fship.json` with defaults
2. Edit `.config/fship.json` for your Flutter project structure
3. Create `.env.dev` with Firebase app IDs:
   ```
   APPIDANDROID_QA=1:123456:android:abcdef...
   APPIDANDROID_UAT=1:345678:android:ghijkl...
   APPIDANDROID_PROD=1:789012:android:mnopqr...
   ```
4. `fship validate` → check config and tools

## Project Structure

```
src/fship/
  ├── main.py           # CLI commands (release, init, validate, version)
  ├── config.py         # Config loading, .env.dev support
  ├── runner.py         # Release orchestration
  ├── versioning.py     # Version bumping logic
  ├── changelog.py      # CHANGELOG generation
  ├── builder.py        # Flutter APK building
  ├── distributor.py    # Firebase distribution
  └── __init__.py       # Version info

.config/
  └── fship.json        # User config (git-ignored)

.env.dev               # Firebase app IDs (git-ignored, auto-loaded)
```

## Release Workflow

1. User runs: `fship release qa`
2. Load `.env.dev` (auto-loads APPIDANDROID_* vars)
3. Prompt for version (or use --version/--bump flags)
4. Bump version in `pubspec.yaml`
5. Generate CHANGELOG.md via git-chglog
6. Generate release_note.txt from git log
7. Git commit version changes
8. Git tag release
9. Build Flutter APK (flutter build apk)
10. Distribute to Firebase App Distribution

## Config Format

**`.config/fship.json`:**
```json
{
  "flavors": {
    "qa": {
      "firebase_app_id_env": "APPIDANDROID_QA",
      "entrypoint": "lib/main_qa.dart",
      "apk_path": "build/app/outputs/flutter-apk/app-qa-release.apk",
      "groups": "testers"
    },
    "uat": { ... },
    "prod": { ... }
  }
}
```

**`.env.dev`:**
```
APPIDANDROID_QA=1:123456:android:abcdef...
APPIDANDROID_UAT=1:345678:android:ghijkl...
APPIDANDROID_PROD=1:789012:android:mnopqr...
```

## Key Features

- **Multi-flavor support**: qa, uat, prod, or custom
- **Dry-run mode**: test without building/distributing
- **Auto-changelog**: generates from git commits
- **Version management**: interactive, auto-increment, or exact
- **Firebase integration**: direct distribution to App Distribution
- **Environment management**: auto-loads .env.dev on startup

## Commands

| Command | Purpose |
|---------|---------|
| `fship release <flavor>` | Release a flavor |
| `fship init` | Create default config |
| `fship validate` | Check config and tools |
| `fship version` | Show fship version |

## Flags

| Flag | Purpose |
|------|---------|
| `--version X.Y.Z+B` | Exact version |
| `--bump patch\|minor\|major` | Auto-increment |
| `--skip-build` | Skip Flutter build (dry-run) |
| `--skip-distribute` | Skip Firebase distribution |

## Prerequisites

- Python 3.11+
- Flutter SDK
- Firebase CLI: `npm install -g firebase-tools`
- git-chglog: `brew install git-chglog` or `npm install -g git-chglog`
- Git repository in Flutter project

## PyPI

Package published at: https://pypi.org/project/fship/

Current version: 0.2.0

## Development

```bash
git clone https://github.com/MrShakila/F-ship.git
cd F-ship
pip install -e .
fship --help
```
