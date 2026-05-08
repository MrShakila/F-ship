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

## Release Flow

```
1. validate_input()              [validation layer]
2. read_version()                [core: versioning]
3. resolve_version()             [core: versioning]
4. update_pubspec()              [core: versioning + file I/O]
5. generate_changelog()          [operations: changelog]
6. generate_release_notes()      [operations: git]
7. git_add_and_commit()          [operations: git]
8. git_tag()                     [operations: git]
9. build_apk() / build_ipa()     [operations: builder]
10. distribute_to_firebase()     [operations: distributor]
```

Each step can be skipped with `--skip-build` or `--skip-distribute`.

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
