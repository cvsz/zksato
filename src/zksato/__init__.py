"""zksato automated trading platform."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("zksato")
except PackageNotFoundError:  # pragma: no cover - source tree without an installed package
    __version__ = "1.0.0"
