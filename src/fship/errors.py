"""Custom exceptions for fship."""


class FshipError(Exception):
    """Base exception for all fship errors."""

    pass


class ValidationError(FshipError):
    """Invalid input or configuration."""

    pass


class ConfigError(FshipError):
    """Config loading/parsing failed."""

    pass


class BuildError(FshipError):
    """Flutter build failed."""

    pass


class DistributionError(FshipError):
    """Firebase distribution failed."""

    pass


class VersionError(FshipError):
    """Version parsing/bumping failed."""

    pass
