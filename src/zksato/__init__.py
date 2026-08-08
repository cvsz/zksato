"""zksato automated trading platform."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("zksato")
except PackageNotFoundError:  # pragma: no cover - source tree without an installed package
    __version__ = "0.4.0"
