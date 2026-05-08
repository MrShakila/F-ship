# fship — Flutter Ship

Memorable, easy CLI for orchestrating Flutter release workflows to Firebase App Distribution.

```bash
fship release qa                    # Interactive version bump + full release
fship release qa --version 1.2.4+46  # Exact version
fship release qa --bump patch       # Auto-increment patch
```

## What It Does (Full Flow)

1. **Bump version** in `pubspec.yaml` (interactive or auto)
2. **Generate CHANGELOG.md** via `git-chglog`
3. **Generate release_note.txt** from git log since last tag
4. **Git commit** version changes
5. **Git tag** the release
6. **Build APK** for the flavor
7. **Distribute to Firebase App Distribution**

## Installation

```bash
cd ~/Projects/fship
pip install -e .
```

## Setup (One Time)

```bash
cd /path/to/your/flutter/project

# Copy default config
fship init

# Edit fship.yaml — set your Firebase app IDs, entry points, APK paths
vi fship.yaml

# Validate setup
fship validate
```

### fship.yaml Example

```yaml
flavors:
  qa:
    firebase_app_id_env: FIREBASE_QA_APP_ID
    entrypoint: lib/main_qa.dart
    apk_path: build/app/outputs/flutter-apk/app-qa-release.apk
    groups: testers

  prod:
    firebase_app_id_env: FIREBASE_PROD_APP_ID
    entrypoint: lib/main_prod.dart
    apk_path: build/app/outputs/flutter-apk/app-prod-release.apk
    groups: testers
```

## Usage

### Interactive Version Bump

```bash
fship release qa
# Current version: 1.2.3+45
# New version: 1.2.4+46
# [shows full release workflow with progress]
```

### Exact Version (Non-Interactive)

```bash
fship release qa --version 1.2.4+46
```

### Auto-Increment

```bash
fship release qa --bump patch    # 1.2.3+45 → 1.2.4+0
fship release qa --bump minor    # 1.2.3+45 → 1.3.0+0
fship release qa --bump major    # 1.2.3+45 → 2.0.0+0
```

### Dry Run (Skip Build & Distribution)

```bash
fship release qa --skip-build --skip-distribute
# Only bumps version, generates changelog, commits, tags
```

## Prerequisites

- Python 3.11+
- Flutter SDK
- Firebase CLI: `npm install -g firebase-tools`
- git-chglog: `brew install git-chglog` (macOS) or `npm install -g git-chglog`
- Environment variables: `FIREBASE_QA_APP_ID`, `FIREBASE_UAT_APP_ID`, etc.

```bash
export FIREBASE_QA_APP_ID=1:123456:android:abcdef...
export FIREBASE_PROD_APP_ID=1:789012:android:ghijkl...
```

## Commands

```bash
fship release <flavor> [--version X.Y.Z+B] [--bump patch|minor|major] [--skip-build] [--skip-distribute]
fship init                         # Copy default fship.yaml
fship validate                     # Check tools and config
fship version                      # Show fship version
fship --help                       # Full help
```

## Troubleshooting

**"fship.yaml not found"**
```bash
fship init
vi fship.yaml  # customize
```

**"Firebase CLI not found"**
```bash
npm install -g firebase-tools
firebase login
```

**"git-chglog not found"**
```bash
brew install git-chglog
# or
npm install -g git-chglog
```

**"Commits/tags not created, but version was bumped"**
- Ensure you're in a git repo and have uncommitted changes allowed
- Check `git status`

## Development

```bash
cd ~/Projects/fship
pip install -e ".[dev]"  # future: add pytest, black, etc.
fship --help
```
