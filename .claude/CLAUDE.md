# fship — Project Context

## Project Summary

fship is a Flutter release orchestration CLI for Firebase App Distribution. Automates version bumping, changelog generation, git tagging, and APK/IPA distribution in one command. Supports multiple flavors (qa, uat, prod, custom) with per-flavor Firebase app IDs.

**Status**: Stable (v0.6.0). Recent improvements: prod semantic versioning, flavor-specific env loading, resume-from failed steps, iOS support, interactive setup, real-time progress, modular validation layer, security hardening.

## Architecture

See [ARCHITECTURE.md](../ARCHITECTURE.md) for module breakdown (validation → core → operations → main).

Key points:
- Input validation at entry boundary (prevents injection)
- Custom exception hierarchy (semantic error handling)
- Real-time subprocess output (no buffering)
- Flavor-based config isolation
- Environment variable strategy: single names per flavor, determined by `.env` filename

## Development Rules

### Code Changes

1. **Before writing**: Read the target file.
2. **Imports**: Use relative imports within fship package. External tools (git, flutter, firebase) handled via subprocess.
3. **Subprocess**: Never `shell=True`. Pass commands as lists: `["git", "log"]` not `"git log"`.
4. **Validation**: All user inputs pass validation layer before core logic. No late validation.
5. **Real-time output**: Long operations (build, distribute) use `capture_output=False` for live progress.
6. **Exceptions**: Raise semantic exceptions (BuildError, DistributionError) not generic Exception.

### Testing

- Unit tests in `tests/test_*.py`
- Use pytest: `pytest tests/ -v`
- Mock external tools (firebase, flutter) in integration tests
- Integration tests use real git (can create/destroy temp repos)

### Configuration

- `.config/fship.json` checked in (no secrets, defines flavor structure)
- `.env.{flavor}` NOT checked in (secrets only)
- Schema in `validation/schema.py`

### Release Workflow

Push a tag matching `v*` pattern → GitHub Actions auto-publishes to PyPI + GitHub.
File: `.github/workflows/release.yml`

## Recent Features (v0.6.0)

### Flavor-Specific Version Bumping
- **Prod flavor**: Pure semantic versioning (X.Y.Z+0, no suffix names)
- **Non-prod (qa/uat/custom)**: Suffix-based bumping
  - With custom suffix: `3.0.4-claim-2+79` → `3.0.4-claim-3+80` (bumps suffix)
  - Without suffix: `3.0.4+77` → `3.0.4-qa-1+78` (adds flavor name as suffix)
- Implementation: `resolve_version()` checks flavor and uses appropriate bump strategy

### Flavor-Specific Environment Loading
- Fixed bug where loading all `.env.*` files simultaneously caused later ones to overwrite earlier ones
- Now `load_env_file(flavor)` loads ONLY `.env.{flavor}` when flavor specified
- `validate` command loads all existing env files to check setup
- Prevents wrong app IDs being used in distribution step

### Resume From Failed Steps
- Added `--resume-from STEP` flag to retry from failure point
- Skips completed steps (version bump, tag, etc.)
- Available steps: `version`, `changelog`, `notes`, `tag`, `build`, `distribute`
- Useful when Firebase fails but version/tag already created

### No-Push Mode
- `--no-push` flag commits and tags locally without pushing to remote
- User can manually verify before pushing: `git push origin main && git push origin v0.6.0`
- Better for CI/CD that pushes separately

## Known Decisions

### Why Modular Validation?

Early validation prevents invalid data flowing through business logic. Easier to test, debug, and secure.

### Why Real-Time Output?

Users watch long builds. Buffering creates "frozen" appearance. Streaming shows progress without extra overhead.

### Why Flavor-Based Config?

Supports multiple environments (qa/uat/prod) independently. Each flavor has isolated Firebase credentials and build paths. Reduces manual mistakes.

### Why Environment Variable Names Not Flavor-Prefixed?

`.env.qa` → `APPIDANDROID` (not `APPIDANDROID_QA`). Filename encodes flavor. Simpler in CI/CD (single secret name per env file). Matches how `.env.prod` files work in other tools.

### Why Custom Exception Hierarchy?

Callers can catch specific errors (`if isinstance(e, BuildError)`). Improves error recovery and logging.

## Common Tasks

### Add a New Operation

1. Create `src/fship/operations/new_op.py` with function returning `bool`
2. Import in `src/fship/runner.py`
3. Add to `steps[]` in `run_release()`

### Add a New Flavor

1. Edit `.config/fship.json` and add flavor entry
2. Create `.env.{flavor_name}` with `APPIDANDROID` and `APPIDIOS`
3. User runs `fship release {flavor_name}`

### Update Version Format

Version format is validated against regex `^\d+\.\d+\.\d+(-[a-z0-9\-]+)?\+\d+$` in `validation/version.py` (allows optional flavor suffix).

Formats:
- Prod: `X.Y.Z+B` (e.g., `3.0.5+0`)
- Non-prod: `X.Y.Z+B` or `X.Y.Z-suffix+B` (e.g., `3.0.4+77` or `3.0.4-qa-2+79`)

To change format:
1. Update regex in `validate_version_format()`
2. Update `parse_version()` to extract components
3. Update `bump_version()` and `bump_flavor_version()`
4. Update examples in README.md
5. Update tests in `tests/test_validation.py`

### Debugging a Release

```bash
# Test without building/distributing
fship release qa --skip-build --skip-distribute

# Show current version
grep "version:" pubspec.yaml

# Show config
cat .config/fship.json

# Check env vars loaded
env | grep APPID
```

## File Locations

- **CLI entry**: `src/fship/main.py`
- **Release orchestration**: `src/fship/runner.py`
- **Validation rules**: `src/fship/validation/`
- **Business logic**: `src/fship/core/`
- **External integrations**: `src/fship/operations/`
- **Errors**: `src/fship/errors.py`
- **Tests**: `tests/`
- **Config schema**: `src/fship/validation/schema.py`
- **Architecture docs**: `ARCHITECTURE.md` (this repo)
- **Security audit**: `SECURITY_AUDIT.md` (lists 14 issues, all addressed)

## Notes for Future Work

- **Dry-run mode**: Currently skips build/distribute. Could add more granular dry-runs per step.
- **Rollback on failure**: If a step fails mid-release, consider rollback support (revert version, delete tag, etc.).
- **Parallel iOS/Android builds**: Currently sequential. Could parallelize with threading (be careful with shared state).
- **Changelog customization**: git-chglog uses templates. Could expose template path in config.
- **Test coverage**: Current coverage ~80%. Aim for 90%+ before v1.0.
- **IPA distribution**: Currently distributed via APK path logic. iOS IPA path handling needs testing on real CI/CD.

## User Preferences (from session)

- Always show progress when building or uploading
- Caveman mode active: terse responses, no fluff
- Use markdown links for file references in responses
