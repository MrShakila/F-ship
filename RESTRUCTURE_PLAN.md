# fship Project Restructuring Plan

## Current State
```
fship/
├── src/fship/
│   ├── __init__.py
│   ├── main.py (CLI entry)
│   ├── runner.py (orchestration)
│   ├── config.py (config loading)
│   ├── versioning.py (version parsing/bumping)
│   ├── builder.py (Flutter APK build)
│   ├── changelog.py (git operations)
│   └── distributor.py (Firebase distribution)
├── fship.yaml (example Flutter config)
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── LICENSE
```

**Issues:**
- No tests directory
- No validation layer (security risk)
- No clear separation of concerns
- No error handling utilities
- Config files mixed with code

## Proposed Structure

```
fship/
├── src/fship/
│   ├── __init__.py
│   ├── main.py (CLI entry point only)
│   ├── runner.py (orchestration) ⬅️ Keep
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   └── commands.py (CLI commands: release, init, config)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py (config loading/parsing)
│   │   ├── versioning.py (version operations)
│   │   └── types.py (FlavorConfig, Config types)
│   │
│   ├── operations/
│   │   ├── __init__.py
│   │   ├── builder.py (Flutter APK build)
│   │   ├── distributor.py (Firebase distribution)
│   │   └── changelog.py (git operations)
│   │
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── version.py (version format validation)
│   │   ├── env.py (environment variable validation)
│   │   ├── path.py (path security validation)
│   │   └── schema.py (config schema validation)
│   │
│   └── errors.py (custom exceptions)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py (pytest fixtures)
│   ├── unit/
│   │   ├── test_versioning.py
│   │   ├── test_config.py
│   │   └── test_validation.py
│   └── integration/
│       ├── test_release_flow.py
│       └── test_builder.py
│
├── config/
│   ├── fship.yaml (default config example)
│   └── .chglog/
│       └── config.yml (git-chglog config)
│
├── docs/
│   ├── SECURITY.md (security guidelines)
│   ├── ARCHITECTURE.md (design decisions)
│   └── DEVELOPMENT.md (dev setup)
│
├── .config/ (gitignored, user's local config)
│   └── fship.json
│
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── SECURITY_AUDIT.md
├── LICENSE
└── Makefile (or justfile)
```

## Rationale by Module

### `cli/commands.py` - Move CLI args here
**Why:** Keeps main.py lean, easier to test
- Extract `@app.command()` functions
- Keep only app setup in main.py

### `core/` - Domain models
**Why:** Centralize business logic
- `config.py`: Load/parse fship.json and fship.yaml
- `versioning.py`: Version bumping, parsing
- `types.py`: Dataclasses (Config, FlavorConfig)

### `operations/` - External integrations
**Why:** Clear responsibility boundaries
- `builder.py`: Calls `flutter build apk`
- `distributor.py`: Calls `firebase appdistribution:distribute`
- `changelog.py`: Git operations (commit, tag, log)

### `validation/` - Input sanitization (FIXES SECURITY)
**Why:** Defend against invalid input at boundary
```
validation/
├── version.py
│   ├── validate_version_format(version_str) -> bool
│   └── validate_bump_part(part: str) -> bool
├── env.py
│   ├── validate_firebase_app_id(app_id) -> bool
│   └── validate_required_env_vars(required: List[str]) -> bool
├── path.py
│   ├── validate_path_within_project(path, project_root) -> bool
│   └── validate_entrypoint_exists(path) -> bool
└── schema.py
    ├── validate_config_schema(config: dict) -> bool
    └── validate_flavor_config(flavor: dict) -> bool
```

### `errors.py` - Custom exceptions
```python
class FshipError(Exception):
    """Base exception"""

class ValidationError(FshipError):
    """Invalid input"""

class ConfigError(FshipError):
    """Config loading/parsing failed"""

class BuildError(FshipError):
    """Flutter build failed"""

class DistributionError(FshipError):
    """Firebase distribution failed"""

class VersionError(FshipError):
    """Version parsing/bumping failed"""
```

## Migration Path

### Phase 1: Create validation module (fixes security)
```bash
mkdir -p src/fship/validation
touch src/fship/validation/{__init__,version,env,path,schema}.py
# Add validators from SECURITY_AUDIT fixes
```

### Phase 2: Reorganize existing code
```bash
mkdir -p src/fship/{cli,core,operations}
mv src/fship/config.py src/fship/core/
mv src/fship/versioning.py src/fship/core/
mv src/fship/types.py src/fship/core/ (create if needed)
mv src/fship/{builder,distributor,changelog}.py src/fship/operations/
# Extract CLI commands from main.py to cli/commands.py
```

### Phase 3: Add tests
```bash
mkdir -p tests/{unit,integration}
# Create test files with basic structure
```

### Phase 4: Move config files
```bash
mkdir -p config/.chglog
mv fship.yaml config/
# Update paths in config.py
```

## Benefits

✅ **Security:** Dedicated validation layer  
✅ **Testability:** Each module independently testable  
✅ **Maintainability:** Clear separation of concerns  
✅ **Scalability:** Easy to add new operations/validators  
✅ **Documentation:** Structure documents architecture  
✅ **Onboarding:** New contributors understand org immediately  

## Breaking Changes

- Config paths may change (use symlinks during transition)
- Import paths change (update in main.py and pyproject.toml)
- CLI signature stays same (backward compatible)

## Timeline

- Phase 1 (validation): 30 min - CRITICAL for security
- Phase 2 (reorganize): 45 min - refactoring
- Phase 3 (tests): 60 min - baseline coverage
- Phase 4 (config): 15 min - polish

**Total: ~2.5 hours for complete restructure**
