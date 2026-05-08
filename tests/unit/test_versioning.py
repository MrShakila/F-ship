"""Unit tests for versioning module."""

import pytest

from fship.core.versioning import (
    parse_version,
    format_version,
    bump_version,
)
from fship.errors import VersionError


class TestParseVersion:
    """Version parsing tests."""

    def test_parse_valid_version(self):
        """Parse valid version string."""
        major, minor, patch, build = parse_version("1.2.3+45")
        assert major == 1
        assert minor == 2
        assert patch == 3
        assert build == 45

    def test_parse_zero_version(self):
        """Parse zero version."""
        major, minor, patch, build = parse_version("0.0.0+0")
        assert major == 0
        assert minor == 0
        assert patch == 0
        assert build == 0

    def test_parse_invalid_format(self):
        """Invalid format should raise VersionError."""
        with pytest.raises(VersionError):
            parse_version("1.2.3")
        with pytest.raises(VersionError):
            parse_version("a.b.c+d")


class TestFormatVersion:
    """Version formatting tests."""

    def test_format_version(self):
        """Format version tuple to string."""
        assert format_version(1, 2, 3, 45) == "1.2.3+45"
        assert format_version(0, 0, 0, 0) == "0.0.0+0"


class TestBumpVersion:
    """Version bumping tests."""

    def test_bump_patch(self):
        """Bump patch version."""
        result = bump_version("1.2.3+45", "patch")
        assert result == "1.2.4+0"

    def test_bump_minor(self):
        """Bump minor version resets patch."""
        result = bump_version("1.2.3+45", "minor")
        assert result == "1.3.0+0"

    def test_bump_major(self):
        """Bump major version resets minor and patch."""
        result = bump_version("1.2.3+45", "major")
        assert result == "2.0.0+0"

    def test_bump_invalid_part(self):
        """Invalid bump part should raise error."""
        with pytest.raises(VersionError):
            bump_version("1.2.3+45", "invalid")
