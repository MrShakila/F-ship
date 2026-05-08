# Security Audit & Issues Report

## Critical Issues (5)

### 1. **Shell Injection in generate_release_notes()** [src/fship/changelog.py:66]
**Severity:** HIGH
```python
f'git log --pretty="- %s (%an)" {rev_range}'
```
- Using f-string with `rev_range` in bash -c command
- If `rev_range` contains special chars, could execute arbitrary commands
- **Fix:** Use subprocess list form instead of bash -c
```python
["git", "log", "--pretty=- %s (%an)", rev_range]
```

### 2. **Missing Version Format Validation** [src/fship/versioning.py:50]
**Severity:** HIGH
```python
def parse_version(version_str: str) -> tuple[int, int, int, int]:
    parts = version_str.split("+")
    semantic = parts[0].split(".")
    build = int(parts[1]) if len(parts) > 1 else 0
```
- No regex validation of format X.Y.Z+B
- Will crash with ValueError if non-numeric input given
- User can crash via `fship release qa --version abc+def`
- **Fix:** Add format validation with regex at start of function

### 3. **Missing Flavor Validation** [src/fship/main.py & src/fship/runner.py]
**Severity:** MEDIUM
```python
def release(flavor: str = typer.Argument(...))
```
- `flavor` accepted as-is without checking against config keys
- Invalid flavor silently fails or causes KeyError later
- **Fix:** Validate flavor exists in config.flavors before processing

### 4. **Missing Environment Variable Validation** [src/fship/distributor.py:24]
**Severity:** MEDIUM
```python
app_id = os.getenv(firebase_app_id_env)
if not app_id:  # Only checked here, too late
```
- No upfront validation of required env vars
- Should validate all required vars before starting release
- **Fix:** Add validation function that checks all env vars exist before run_release()

### 5. **Unsafe Path Handling** [src/fship/distributor.py:30, src/fship/builder.py]
**Severity:** MEDIUM
- `apk_path` from config not validated before use
- No checks for path traversal (e.g., `../../etc/passwd`)
- `entrypoint` path from config passed directly to flutter without validation
- **Fix:** Validate paths are within project directory

## Code Quality Issues (9)

### 6. **Weak Error Handling** [src/fship/runner.py:37]
```python
except Exception as e:
    console.print(f"\n[bold red]Error: {e}[/bold red]")
```
- Catches all exceptions, masks real errors
- Should catch specific exceptions (IOError, subprocess.CalledProcessError, etc.)
- **Fix:** Catch specific exceptions, let unexpected ones propagate

### 7. **No Input Validation for Bump Parameter** [src/fship/main.py]
```python
bump: str = typer.Option(None, "--bump", "-b")
```
- Not validated against ["patch", "minor", "major"]
- Invalid bump values cause ValueError at runtime
- **Fix:** Use typer Choice type or validate early

### 8. **Unhandled Exception in parse_version()** [src/fship/versioning.py:50]
```python
build = int(parts[1]) if len(parts) > 1 else 0
semantic = int(semantic[0])  # Could crash if non-numeric
```
- Will crash if version has non-numeric parts
- No try/except for ValueError
- **Fix:** Wrap in try/except or validate format first

### 9. **Unsafe YAML Handling** [src/fship/versioning.py:25, 38]
```python
yaml.dump(data, f)  # Could fail silently
```
- No error handling for write failures
- Partially written files could corrupt pubspec.yaml
- **Fix:** Use atomic write (write to temp, then move)

### 10. **Git Tag Not Validated for Duplicates** [src/fship/changelog.py:114]
```python
subprocess.run(["git", "tag", tag], check=True)
```
- If tag already exists, git fails
- No cleanup if later steps fail
- **Fix:** Check if tag exists first, add --force flag or better error handling

### 11. **Missing Validation of Release Notes File** [src/fship/distributor.py:45]
```python
if not Path(release_notes_file).exists():
    # Path hardcoded in function signature
```
- `release_notes_file` parameter has hardcoded default
- No validation that file is readable
- **Fix:** Make path configurable, add validation

### 12. **No Logging or Audit Trail** [src/fship/]
- No record of what was released, when, by whom
- No ability to audit releases
- **Fix:** Add release log file or use git log/tags for audit

### 13. **Missing Test Coverage** [Project structure]
- No tests directory found
- No validation of release flow
- **Fix:** Add pytest tests for version parsing, env validation, config loading

### 14. **Hardcoded Config Paths** [src/fship/config.py:8-9]
```python
CONFIG_DIR = Path.cwd() / ".config"
CONFIG_FILE = CONFIG_DIR / "fship.json"
```
- Relative to cwd, could break if run from different directory
- No XDG_CONFIG_HOME support
- **Fix:** Use absolute paths or XDG standards

## Dependency Issues

- **Missing version pins** in requirements/pyproject.toml
- **No security scanning** (bandit, safety) in CI/CD
- **ruamel.yaml** should be pinned to known-good version

## Recommendations

1. Add input validation layer at CLI boundary (main.py)
2. Create validation utility module (validation.py)
3. Replace bash -c with direct subprocess calls
4. Add atomic file write helper
5. Add pytest test suite
6. Add pre-commit hooks (bandit, black, flake8)
7. Add release audit logging
8. Document security assumptions in README

## Files to Review Priority

1. `src/fship/changelog.py` - Shell injection risk
2. `src/fship/versioning.py` - Validation missing
3. `src/fship/distributor.py` - Env validation missing
4. `src/fship/config.py` - Path handling
5. `src/fship/main.py` - Input validation
