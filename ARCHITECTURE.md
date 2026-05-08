# fship Architecture

## Overview

fship is a modular Flutter release orchestration CLI. The codebase is organized into four core layers: **validation**, **core**, **operations**, and **main** entry point. This design enforces security at the boundary (validation) and separates concerns.

## Module Structure

```
src/fship/
├── __init__.py              # Version export
├── main.py                  # CLI entry point (typer app)
├── errors.py                # Custom exception hierarchy
├── runner.py                # Release orchestration engine
├── validation/              # Input sanitization layer
│   ├── __init__.py
│   ├── version.py           # Version format validation (X.Y.Z+B)
│   ├── env.py               # Environment variable validation
│   ├── path.py              # Path security (traversal protection)
│   └── schema.py            # Config schema validation
├── core/                    # Business logic
│   ├── __init__.py
│   ├── config.py            # Config loading & flavor management
│   └── versioning.py        # Version bumping logic
└── operations/              # External integrations
    ├── __init__.py
    ├── builder.py           # Flutter build (APK/IPA)
    ├── distributor.py       # Firebase App Distribution
    ├── git.py               # Git tagging & commits
    └── changelog.py         # Changelog generation (git-chglog)
```

## Design Patterns

### 1. Input Validation at Boundary

All user inputs are validated at entry before passing to core logic:

```python
# In main.py
validate_version_format(version)      # Reject malformed versions
validate_flavor_exists(flavor, config) # Reject non-existent flavors
validate_required_env_vars(env_vars)  # Reject missing credentials
validate_file_path(path)              # Reject path traversal attempts
```

**Why:** Prevents injection, ensures data integrity, fails fast.

### 2. Exception Hierarchy

Custom exceptions provide semantic clarity:

- `FshipError` — Base exception
  - `ValidationError` — Input validation failed
  - `ConfigError` — Configuration missing/invalid
  - `BuildError` — Flutter build failed
  - `DistributionError` — Firebase distribution failed
  - `VersionError` — Version parsing/bumping failed

**Why:** Callers can catch specific errors; improves error recovery.

### 3. Real-Time Progress Streaming

Long operations (build, distribute) stream output to console without buffering:

```python
# In operations/builder.py
result = subprocess.run(cmd, capture_output=False, text=True, check=False)
```

**Why:** User sees live progress; no "frozen" appearance.

### 4. Flavor-Based Configuration

Flavors (qa, uat, prod, custom) isolate Firebase app IDs and build paths:

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

**Why:** Multi-flavor support; isolated credentials; reduces manual mistakes.

### 5. Environment Variable Strategy

Single variable names per flavor, determined by `.env` file name:

- `.env.qa` → `APPIDANDROID`, `APPIDIOS` for QA
- `.env.uat` → `APPIDANDROID`, `APPIDIOS` for UAT
- `.env.prod` → `APPIDANDROID`, `APPIDIOS` for Prod
- `.env.dev` → fallback for development

**Why:** Simpler than flavor-prefixed names; CI/CD friendly (name encodes flavor).

## Command Logic Maps

### `fship release <flavor>`

```
main.py::release()
│
├── load_config(flavor)
│   └── load_env_file(flavor)           ← loads .env.{flavor} ONLY
│       └── if missing → warn + use system env
│
├── get_flavor(config, flavor)          ← validates flavor exists
├── validate_bump_part(bump)            ← if --bump given
│
└── run_release(flavor, flavor_config, ...)
    │
    ├── read_version()                  ← reads pubspec.yaml
    ├── resolve_version()               ← interactive or --version/--bump
    │   ├── prod  → bump_version()      ← X.Y.Z+0 (no suffix)
    │   └── other → bump_flavor_version() ← X.Y.Z-suffix+B
    │
    ├── [resume_from] → skip to step
    │
    ├── step: Update pubspec.yaml       ← write_version()
    ├── step: Generate CHANGELOG.md     ← git-chglog (non-fatal if missing)
    ├── step: Generate release notes    ← git log since last tag → release_note.txt
    ├── step: Commit & tag              ← git add + commit + tag (ONCE)
    │
    ├── step: Build
    │   ├── ipa_path configured?
    │   │   ├── FSHIP_PARALLEL_BUILDS=1 → APK + IPA in parallel threads
    │   │   └── else                    → APK first, then IPA sequentially
    │   └── no ipa_path                 → APK only
    │
    ├── step: Distribute to Firebase
    │   ├── always → distribute APK (APPIDANDROID)
    │   └── ipa_built=True → distribute IPA (APPIDIOS) in same step
    │
    ├── on step failure
    │   ├── auto_rollback=True + tag already created?
    │   │   ├── revert pubspec.yaml
    │   │   ├── git reset --soft HEAD~1
    │   │   └── git tag -d {tag}
    │   └── print: fix issue, retry with --resume-from
    │
    └── show_summary()
```

---

### `fship multi-release <flavors>`

```
main.py::multi_release()
│
├── load_config()                       ← config only, no env loaded yet
├── validate_bump_part(bump)
│
└── run_multi_release(flavor_list, config, ...)
    │
    └── for each flavor in list:
        ├── load_env_file(flavor)       ← reload env per flavor
        ├── get_flavor(config, flavor)
        └── run_release(flavor, ...)    ← full release flow (see above)
    │
    └── print per-flavor summary table
```

---

### `fship status [flavor]`

```
main.py::status()
│
├── read_version()                      ← pubspec.yaml current version
│
├── git tag --sort=-version:refname     ← get all tags
│   └── filter by flavor if given
│
├── git log -1 --format=%ar {last_tag}  ← "2 days ago"
│
└── git rev-list --count {tag}..HEAD    ← pending commit count
```

---

### `fship pre-check <flavor>`

```
main.py::pre_check()
│
├── load_config(flavor)                 ← load config + flavor env
├── get_flavor(config, flavor)          ← validate flavor exists
│
├── flutter --version                  ← check Flutter SDK
├── firebase --version                 ← check Firebase CLI
│
├── os.getenv(APPIDANDROID)            ← check Android app ID set
├── os.getenv(APPIDIOS)                ← check iOS app ID set (warn only)
│
├── check apk_path exists              ← warn if not built yet
│
└── print: all OK / issues found
```

---

### `fship init`

```
main.py::init()
│
├── CONFIG_FILE exists? → prompt overwrite
│
├── interactive=True
│   ├── prompt: flavors to configure (qa/uat/prod/custom)
│   ├── per flavor:
│   │   ├── entrypoint (lib/main_{flavor}.dart)
│   │   ├── apk_path
│   │   ├── ipa_path
│   │   └── groups (testers)
│   ├── print Firebase Console guide
│   └── print .env setup options
│
└── save_config() → .config/fship.json
```

---

### `fship validate`

```
main.py::validate()
│
├── load_config()                       ← all env files loaded
├── validate config schema
│
├── per flavor:
│   ├── os.getenv(APPIDANDROID)        ← check Android ID
│   └── os.getenv(APPIDIOS)            ← check iOS ID
│
└── check tools:
    ├── flutter --version
    ├── firebase --version
    ├── git --version
    └── git-chglog --version
```

---

### `fship help`

```
main.py::help()
└── print: commands table, options, examples, version formats,
          rollback behavior, env vars, setup guide
```

---

### `fship version`

```
main.py::version()
└── print: fship {__version__}          ← from src/fship/__init__.py
```

## Security Considerations

### Validation Layer

- **Version format**: Regex `^\d+\.\d+\.\d+\+\d+$` prevents injection
- **Path traversal**: Checks for `..`, absolute paths, symlinks
- **Flavor validation**: Against config.flavors keys only
- **Schema validation**: JSON schema checks all required fields

### Subprocess Calls

- Never use `shell=True`
- Pass command as list: `["git", "log", ...]` not `"git log ..."`
- No bash `-c` wrapper (previously vulnerable)

### Secrets

- Never printed to console
- Never committed to git (via .gitignore: *.env*)
- Loaded from environment only

## Configuration Files

### `.config/fship.json`

Checked into git (no secrets). Defines flavor structure and build paths.

Example:
```json
{
  "flavors": {
    "qa": { ... },
    "uat": { ... }
  }
}
```

### `.env.{flavor}` or `.env.dev`

Not checked into git. Contains Firebase app IDs only.

Example:
```bash
APPIDANDROID=1:123456:android:abcdef...
APPIDIOS=1:987654:ios:fedcba...
```

### GitHub Actions Workflow

Triggered on `git tag v*` push. Publishes release to GitHub + PyPI.

File: `.github/workflows/release.yml`

## Future Extensibility

### Adding a New Operation

1. Create `operations/new_op.py` with function:
   ```python
   def new_operation(...) -> bool:
       validate_inputs()
       # ... logic ...
       return success
   ```

2. Import in `runner.py`:
   ```python
   from fship.operations import new_operation
   ```

3. Add to release flow in `run_release()`.

### Adding a New Flavor

1. Edit `.config/fship.json`:
   ```json
   "custom": {
     "firebase_app_id_env_android": "APPIDANDROID",
     "firebase_app_id_env_ios": "APPIDIOS",
     ...
   }
   ```

2. Create `.env.custom`:
   ```bash
   APPIDANDROID=...
   APPIDIOS=...
   ```

## Testing

Unit tests in `tests/`:
- `test_validation.py` — Input validation
- `test_versioning.py` — Version bumping
- `test_config.py` — Config loading
- `test_*_integration.py` — End-to-end (mocked Firebase/git)

Run:
```bash
pytest tests/ -v
```

## Dependencies

- `typer[all]` — CLI framework
- `rich` — Terminal formatting
- `pyyaml`, `ruamel.yaml` — Config parsing
- `subprocess` — Process execution (stdlib)
- `pathlib` — Path validation (stdlib)

External tools (not Python dependencies):
- `flutter` — Build APK/IPA
- `firebase-tools` — Distribution
- `git-chglog` — Changelog generation
- `git` — Version control
