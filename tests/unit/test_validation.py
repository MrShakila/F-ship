"""Unit tests for validation module."""

import pytest

from fship.validation import (
    validate_version_format,
    validate_bump_part,
    validate_firebase_app_id,
    validate_flavor_exists,
)
from fship.errors import ValidationError


class TestVersionValidation:
    """Version format validation tests."""

    def test_valid_version_format(self):
        """Valid X.Y.Z+B format should pass."""
        assert validate_version_format("1.2.3+45")
        assert validate_version_format("0.0.0+0")
        assert validate_version_format("99.99.99+9999")

    def test_invalid_version_missing_build(self):
        """Version without build number should fail."""
        with pytest.raises(ValidationError):
            validate_version_format("1.2.3")

    def test_invalid_version_format(self):
        """Invalid format should fail."""
        with pytest.raises(ValidationError):
            validate_version_format("1.2")
        with pytest.raises(ValidationError):
            validate_version_format("abc+def")
        with pytest.raises(ValidationError):
            validate_version_format("")

    def test_non_numeric_version(self):
        """Non-numeric version should fail."""
        with pytest.raises(ValidationError):
            validate_version_format("a.b.c+d")


class TestBumpPartValidation:
    """Bump part validation tests."""

    def test_valid_bump_parts(self):
        """Valid bump parts should pass."""
        assert validate_bump_part("patch")
        assert validate_bump_part("minor")
        assert validate_bump_part("major")

    def test_invalid_bump_part(self):
        """Invalid bump part should fail."""
        with pytest.raises(ValidationError):
            validate_bump_part("invalid")
        with pytest.raises(ValidationError):
            validate_bump_part("major_version")


class TestFirebaseValidation:
    """Firebase app ID validation tests."""

    def test_valid_app_id(self):
        """Valid Firebase app ID should pass."""
        assert validate_firebase_app_id("1:123456789:android:abcdef0123456789")

    def test_empty_app_id(self):
        """Empty app ID should fail."""
        with pytest.raises(ValidationError):
            validate_firebase_app_id("")


class TestFlavorValidation:
    """Flavor validation tests."""

    def test_valid_flavor(self):
        """Existing flavor should pass."""
        config = {"flavors": {"qa": {}, "prod": {}}}
        assert validate_flavor_exists("qa", config)

    def test_missing_flavor(self):
        """Non-existing flavor should fail."""
        config = {"flavors": {"qa": {}, "prod": {}}}
        with pytest.raises(ValidationError):
            validate_flavor_exists("staging", config)
