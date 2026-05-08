# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-05-08

### Fixed

- PyPI package metadata (author, license, URLs)
- Interactive .env.dev setup for Firebase app IDs

## [0.1.0] - 2026-05-08

### Added

- Initial release of fship
- CLI for orchestrating Flutter release workflows to Firebase App Distribution
- Interactive version bumping (interactive, auto-increment, or exact version)
- CHANGELOG generation via git-chglog
- Release notes generation from git log
- Git tagging and commit management
- APK building for Flutter flavors
- Firebase App Distribution integration
- `fship init` command for project setup
- `fship validate` command for configuration validation
- `fship release` command with flavor support (e.g., `fship release qa`)
- PyPI publish workflow
