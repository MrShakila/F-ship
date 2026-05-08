# fship — Flutter Ship

Memorable, easy CLI for orchestrating Flutter release workflows to Firebase App Distribution.

```bash
fship release qa                    # Interactive version bump + full release
fship release qa --version 1.2.4+46  # Exact version
fship release qa --bump patch       # Auto-increment patch
```

## Quick Start

1. **Install**: `pip install fship`
2. **Initialize**: `cd /path/to/flutter/project && fship init`
3. **Add Firebase App IDs**: Follow the interactive setup guide
4. **Validate**: `fship validate`
5. **Release**: `fship release qa` (or your flavor name)

## Why fship?

**Problem:** Manual Flutter releases to Firebase App Distribution are tedious and error-prone.
- Manual version bumping in pubspec.yaml
- Manual changelog creation
- Manual git tagging
- Manual APK/IPA building for each flavor
- Manual Firebase distribution
- Human error: wrong version, missing tags, incomplete changelogs

**Solution:** fship automates the entire workflow in one command.

## Features

✓ **Interactive Setup Guide**
- Interactive `fship init` walks through Firebase App ID retrieval
- Links to Firebase Console
- Multiple environment variable setup options

✓ **Android & iOS Support**
- Build and distribute both APK (Android) and IPA (iOS)
- Separate Firebase app IDs: APPIDANDROID, APPIDIOS
- Flavor-specific build paths for both platforms
- Single-command release for both platforms

✓ **Version Management**
- Interactive or automated version bumping
- Auto-increment: patch, minor, or major
- Exact version specification
- Format validation (X.Y.Z+B or X.Y.Z-suffix+B)

✓ **Changelog Generation**
- Auto-generate CHANGELOG.md from git history
- Uses git-chglog for professional formatting
- Customizable changelog templates

✓ **Git Integration**
- Auto-commit version changes
- Auto-create git tags
- Track release history in git

✓ **Multi-Flavor Support**
- Separate configurations per flavor (qa, uat, prod, custom)
- Flavor-specific entrypoints, build paths, Firebase app IDs
- Release to multiple flavors independently

✓ **Real-Time Progress Output**
- Stream Flutter build output to console
- Stream Firebase CLI output to console
- Live progress visibility (no silent waiting)

✓ **Firebase Distribution**
- One-command distribution to Firebase App Distribution
- Customizable tester groups (testers, internal, external)
- Release notes auto-generated from git log
- Support for both Android and iOS platforms

✓ **Input Validation**
- Version format validation (X.Y.Z+B)
- Flavor existence checking
- Path traversal protection
- Firebase app ID format validation
- Required environment variable validation

✓ **Dry-Run Mode**
- Test version bumping, changelog, and tagging without building/distributing
- Perfect for validating setup

✓ **Environment Management**
- Auto-loads Firebase app IDs from `.env.{flavor}` or `.env.dev`
- Interactive setup if config missing
- No hardcoded secrets in repo
- Support for both Android and iOS app IDs

## How It Works (Full Flow)

1. **Bump version** in `pubspec.yaml` (interactive or auto)
2. **Generate CHANGELOG.md** via `git-chglog`
3. **Generate release_note.txt** from git log since last tag
4. **Git commit** version changes
5. **Git tag** the release
6. **Build APK/IPA** for the flavor (with real-time progress)
7. **Distribute to Firebase App Distribution** (with real-time progress)

## Installation

**Via PyPI (Recommended)**
```bash
pip install fship
```

**From Source (Development)**
```bash
git clone https://github.com/MrShakila/F-ship.git
cd F-ship
pip install -e .
```

## Setup (One Time)

```bash
cd /path/to/your/flutter/project

# Interactive setup with Firebase App ID guide
fship init

# Validate setup
fship validate
```

### Interactive Init Guide

`fship init` will walk you through:

1. **Configure Flavors** — Choose which flavors (qa, uat, prod, custom)
2. **Get Firebase App IDs** — Interactive guide with Firebase Console links
3. **Set Environment Variables** — Choose between .env files or exports

### Configuration File Structure

After running `fship init`, your config is stored in `.config/fship.json`:

```json
{
  "flavors": {
    "qa": {
      "firebase_app_id_env_android": "APPIDANDROID",
      "firebase_app_id_env_ios": "APPIDIOS",
      "entrypoint": "lib/main_qa.dart",
      "apk_path": "build/app/outputs/flutter-apk/app-qa-release.apk",
      "ipa_path": "build/ios/ipa/fship-qa-release.ipa",
      "groups": "testers"
    }
  }
}
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

## Environment Setup

### Option 1: Single .env.dev file (for development)

Create `.env.dev` with both Android and iOS app IDs:

```bash
# .env.dev (add to .gitignore)
APPIDANDROID=1:123456:android:abcdef...
APPIDIOS=1:987654:ios:fedcba...
```

### Option 2: Flavor-Specific Files (Recommended for CI/CD)

Flavor determined by filename:

```bash
# .env.qa
APPIDANDROID=1:111111:android:aaaaaa...
APPIDIOS=1:222222:ios:bbbbbb...

# .env.uat
APPIDANDROID=1:333333:android:cccccc...
APPIDIOS=1:444444:ios:dddddd...

# .env.prod
APPIDANDROID=1:555555:android:eeeeee...
APPIDIOS=1:666666:ios:ffffff...
```

### Option 3: Export as Environment Variables

```bash
export APPIDANDROID='1:123456:android:abcdef...'
export APPIDIOS='1:987654:ios:fedcba...'
fship release qa
```

### Getting Firebase App IDs

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Click **Project Settings** (gear icon)
4. Select **Your apps** tab
5. Find your app and click it
6. Copy the **Google App ID** (format: `1:123456789:android:abcdef...` or `1:123456789:ios:ghijkl...`)

## Commands

```bash
fship release <flavor> [--version X.Y.Z+B] [--bump patch|minor|major] [--skip-build] [--skip-distribute]
fship init                         # Interactive setup with Firebase guide
fship validate                     # Check tools and config
fship version                      # Show fship version
fship --help                       # Full help
```

## Prerequisites

- Python 3.11+
- Flutter SDK
- Firebase CLI: `npm install -g firebase-tools`
- git-chglog: `brew install git-chglog` (macOS) or `npm install -g git-chglog`

## Troubleshooting

**"Firebase app ID not set"**
```bash
fship init           # Run setup again
fship validate       # Check configuration
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
- Ensure you're in a git repo
- Check `git status` for uncommitted changes
- Verify git is configured with name and email

## Security

fship has built-in protections:
- ✓ Version format validation
- ✓ Path traversal protection
- ✓ Firebase app ID format validation
- ✓ Flavor existence checking
- ✓ No shell injection vulnerabilities
- ✓ Environment variable validation

See [SECURITY_AUDIT.md](SECURITY_AUDIT.md) for details.

## Development

```bash
git clone https://github.com/MrShakila/F-ship.git
cd F-ship
pip install -e .
fship --help
```

### Running Tests

```bash
pytest tests/ -v
```

## License

MIT — See [LICENSE](LICENSE)

## Contributing

Issues and PRs welcome. See [GitHub](https://github.com/MrShakila/F-ship)
