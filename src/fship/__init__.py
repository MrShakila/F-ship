"""Flutter Ship — release orchestration CLI."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("fship")
except PackageNotFoundError:
    __version__ = "unknown"
