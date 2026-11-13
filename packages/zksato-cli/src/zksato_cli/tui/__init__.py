"""zksato TUI - Terminal User Interface for agent management.

Provides a terminal-based interface for interacting with zksato agents,
strategies, risk engine, market data, and portfolio.

All TUI interactions route through the existing API layer and RiskEngine,
preserving all AGENTS.md safety invariants.
"""

from .app import ZKSATOTUI

__all__ = ["ZKSATOTUI"]
