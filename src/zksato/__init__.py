"""zksato automated trading platform."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("zksato-core")
except PackageNotFoundError:  # pragma: no cover - source tree without an installed package
    __version__ = "2.0.0-dev"
