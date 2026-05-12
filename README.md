# fship — Flutter Ship

Memorable, easy CLI for orchestrating Flutter release workflows to Firebase App Distribution.

```bash
fship release qa                         # Interactive version bump + full release
fship release qa --version 3.0.4+79      # Exact version
fship release qa --bump patch            # Auto-increment patch
fship release qa --resume-from distribute  # Retry after failure
fship multi-release qa,uat --bump patch  # Release multiple flavors
fship publish --bump patch               # Package publish: bump, changelog, commit & tag
fship status qa                          # Current version + last release info
fship pre-check qa                       # Pre-flight checks before release
```

## Quick Start

1. **Install**: `pip install fship`
2. **Initialize**: `cd /path/to/flutter/project && fship init`
3. **Add Firebase App IDs**: Follow the interactive setup guide
4. **Validate**: `fship validate`
5. **Pre-check**: `fship pre-check qa`
6. **Release**: `fship release qa` (or your flavor name)

## Why fship?

**Problem:** Manual Flutter releases to Firebase App Distribution are tedious and error-prone.
- Manual version bumping in pubspec.yaml
- Manual changelog creation
- Manual git tagging
- Manual APK/IPA building for each flavor
- Manual Firebase distribution
- Human error: wrong version, missing tags, incomplete changelogs

**Solution:** fship automates the entire workflow in one command, with safety features like auto-rollback and pre-release checks.

## Features

✓ **Interactive Setup Guide**
- Interactive `fship init` walks through Firebase App ID retrieval
- Links to Firebase Console
- Multiple environment variable setup options

✓ **Android & iOS Support**
- Build and distribute APK (Android), IPA (iOS), and AAB (Play Store)
- Separate Firebase app IDs: APPIDANDROID, APPIDIOS
- Flavor-specific build paths for both platforms
- Optional parallel APK + IPA builds (`FSHIP_PARALLEL_BUILDS=1`)

✓ **Version Management**
- Interactive or automated version bumping
- Auto-increment: patch, minor, or major
- Exact version specification
- Prod: pure semantic versioning (X.Y.Z+0, no suffix)
- Non-prod: flavor suffix (e.g., 3.0.4-qa-2+79)
- Format validation (X.Y.Z+B or X.Y.Z-suffix+B)

✓ **Changelog Generation**
- Auto-generate CHANGELOG.md from git history
- Uses git-chglog for professional formatting
- Release notes auto-generated from git log since last tag

✓ **Git Integration**
- Auto-commit version changes
- Auto-create git tags
- Track release history in git

✓ **Multi-Flavor Support**
- Separate configurations per flavor (qa, uat, prod, custom)
- Flavor-specific entrypoints, build paths, Firebase app IDs
- `fship multi-release qa,uat` releases multiple flavors in sequence

✓ **Auto-Rollback on Failure**
- If distribution fails after commit/tag, automatically reverts
- Restores original version in pubspec.yaml
- Deletes the git tag and resets the commit
- Resume cleanly with `--resume-from distribute`

✓ **Pre-Release Checks**
- `fship pre-check <flavor>` validates everything before release
- Checks Flutter SDK, Firebase CLI, credentials, APK path

✓ **Release Status**
- `fship status [flavor]` shows current version, last release, pending commits

✓ **Real-Time Progress Output**
- Stream Flutter build output to console
- Stream Firebase CLI output to console
- Live progress visibility (no silent waiting)

✓ **Firebase Distribution**
- One-command distribution to Firebase App Distribution
- Customizable tester groups (testers, internal, external)
- Flavor-specific env files: `.env.qa`, `.env.uat`, `.env.prod`

✓ **Input Validation**
- Version format validation (X.Y.Z+B)
- Flavor existence checking
- Path traversal protection
- Firebase app ID format validation
- Required environment variable validation

✓ **Package Publish Mode**
- `fship publish` bumps version, generates changelog, commits, and tags — no build or Firebase steps
- Use before `dart pub publish` to prepare a package release
- Same `--bump` and `--version` options as `release`

✓ **Dry-Run Mode**
- Test version bumping, changelog, and tagging without building/distributing
- Perfect for validating setup

✓ **Resume From Failed Step**
- `--resume-from STEP` retries from failure point
- Skips already-completed steps

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

### Retry Failed Release

If release fails at any step, fix the issue and resume from that point:

```bash
fship release qa --resume-from build       # Retry build and distribution
fship release qa --resume-from distribute  # Retry distribution only
```

Steps: `version`, `changelog`, `notes`, `tag`, `build`, `distribute`

If release fails after git commit/tag, fship **auto-rolls back** the version bump and deletes the tag so you can retry cleanly.

### Pre-Release Checks

```bash
fship pre-check qa
# ✓ Config: flavor 'qa' found
# ✓ Flutter: Flutter 3.x.x
# ✓ Firebase CLI: 13.x.x
# ✓ APPIDANDROID: set
# ⚠ APPIDIOS not set (iOS distribution will be skipped)
```

### Release Status

```bash
fship status qa
# Current version: 3.0.4-qa-2+79
# Last release: v3.0.4-qa-2+79
# Released: 2 days ago
# Pending commits: 3
```

### Multi-Flavor Release

```bash
fship multi-release qa,uat --bump patch
# Releases qa first, then uat
# Shows per-flavor success/failure summary
```

### Android App Bundle (Play Store)

Build AAB directly using Flutter's appbundle target. The `build_aab` function in `operations/builder.py` handles this — wire it into a custom step or extend the release flow.

### Package Publish (pub.dev)

For Dart/Flutter packages — bumps version, generates changelog, commits, and tags. No build or Firebase distribution.

```bash
fship publish --bump patch         # 0.9.5 → 0.9.6, commit, tag v0.9.6
fship publish --version 1.0.0+0   # Exact version
fship publish --no-push            # Commit + tag locally, push manually
```

Then publish the package:

```bash
dart pub publish
```

### Parallel iOS + Android Builds

Set environment variable to enable parallel builds:

```bash
FSHIP_PARALLEL_BUILDS=1 fship release qa
# Builds APK and IPA simultaneously using threads
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

## All Commands and Options

### Commands

| Command | Description |
|---|---|
| `fship release <flavor>` | Full release: version bump → changelog → tag → build → distribute |
| `fship publish` | Package publish: version bump → changelog → commit → tag (no build/distribute) |
| `fship multi-release <flavors>` | Release multiple flavors in sequence (e.g., `qa,uat`) |
| `fship status [flavor]` | Show current version, last release tag, and pending commit count |
| `fship pre-check <flavor>` | Pre-flight checks: Flutter SDK, Firebase CLI, credentials, APK path |
| `fship init` | Interactive setup guide — configure flavors and Firebase app IDs |
| `fship validate` | Check tools (flutter, firebase, git), config schema, and env vars |
| `fship help` | Full help with all commands, options, and examples |
| `fship version` | Show installed fship version |

### Release Options

| Option | Description |
|---|---|
| `<flavor>` | Required. Flavor to release: `qa`, `uat`, `prod`, or custom |
| `--version, -v VERSION` | Exact version (e.g., `3.0.4+79`). Skips interactive prompt |
| `--bump, -b PART` | Auto-increment: `patch`, `minor`, or `major`. Resets build to 0 |
| `--skip-build` | Skip Flutter build step (useful for testing config) |
| `--skip-distribute` | Skip Firebase distribution (dry-run mode) |
| `--no-push` | Commit and tag locally — don't push to remote |
| `--resume-from STEP` | Retry from a specific step after failure (see steps below) |

**Resume steps** (in order): `version` → `changelog` → `notes` → `tag` → `build` → `distribute`

### Multi-Release Options

| Option | Description |
|---|---|
| `<flavors>` | Required. Comma-separated flavor list (e.g., `qa,uat,prod`) |
| `--bump, -b PART` | Auto-bump all flavors: `patch`, `minor`, or `major` |
| `--skip-build` | Skip build for all flavors |
| `--skip-distribute` | Skip distribution for all flavors |
| `--no-push` | Local only for all flavors |

### Publish Options

| Option | Description |
|---|---|
| `--version, -v VERSION` | Exact version (e.g., `1.2.3+0`). Interactive if omitted |
| `--bump, -b PART` | Auto-increment: `patch`, `minor`, or `major` |
| `--no-push` | Commit and tag locally — don't push to remote |

### Environment Variables

| Variable | Description |
|---|---|
| `APPIDANDROID` | Firebase Android App ID (in `.env.{flavor}`) |
| `APPIDIOS` | Firebase iOS App ID (in `.env.{flavor}`) |
| `FSHIP_PARALLEL_BUILDS=1` | Build APK and IPA simultaneously using threads |

### Release Examples

```bash
# Interactive (prompts for version)
fship release qa

# Exact version
fship release qa --version 3.0.4+79

# Auto-increment (patch)
fship release qa --bump patch     # X.Y.Z+B → X.Y.(Z+1)+0

# Auto-increment (minor)
fship release qa --bump minor     # X.Y.Z+B → X.(Y+1).0+0

# Auto-increment (major)
fship release qa --bump major     # X.Y.Z+B → (X+1).0.0+0

# Prod flavor (semantic versioning, no suffix)
fship release prod --bump patch   # X.Y.Z+B → X.Y.(Z+1)+0

# Dry run (version + changelog + tag, no build/distribute)
fship release qa --skip-build --skip-distribute

# No push (local commit/tag only)
fship release qa --no-push

# Retry from build (after fixing app ID, build paths, etc.)
fship release qa --resume-from build

# Retry from distribution (after fixing Firebase config)
fship release qa --resume-from distribute

# Custom flavor (user-defined in .config/fship.json)
fship release staging --version 2.0.0+0
```

### Version Format

**Standard flavors (qa, uat, custom)**:
- With suffix: `X.Y.Z-suffix+B` (e.g., `3.0.4-qa-2+79`)
- Without suffix: `X.Y.Z+B` (e.g., `3.0.4+77`)
- Bumping adds flavor suffix if missing: `3.0.4+77` → `3.0.4-qa-1+78`

**Prod flavor**:
- Pure semantic: `X.Y.Z+0` (e.g., `3.0.5+0`)
- No suffix names (just numbers)
- Bumping uses standard semantic versioning

### Resume Steps

When using `--resume-from STEP`, available steps are:

1. `version` — Update pubspec.yaml
2. `changelog` — Generate CHANGELOG.md
3. `notes` — Generate release notes
4. `tag` — Commit and create git tag
5. `build` — Build APK/IPA
6. `distribute` — Distribute to Firebase App Distribution

### Resume From Failed Step

If release fails at any step, fix the issue and retry from that point:

```bash
# Release failed at build step
fship release qa --resume-from build       # Skip version/changelog/tag, retry build

# Release failed at distribution
fship release qa --resume-from distribute  # Skip build, retry distribution

# Available steps: version, changelog, notes, tag, build, distribute
```

**Example workflow**:
```bash
fship release qa --version 3.0.5+0
# → Firebase distribution fails (wrong app ID)

# Fix: Update .env.qa with correct APPIDANDROID

fship release qa --resume-from distribute
# → Retries distribution (skips version bump, build, tag)
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

**Release failed, want to retry from a specific step?**
- Fix the underlying issue (e.g., update app IDs, check Firebase setup)
- Use `--resume-from` to skip completed steps and retry from failure point:
```bash
fship release qa --resume-from build       # Retry build (skip version/tag)
fship release qa --resume-from distribute  # Retry distribution (skip build)
```

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
