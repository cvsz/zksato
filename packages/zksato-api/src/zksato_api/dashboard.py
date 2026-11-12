"""Dashboard service for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zksato_core.models import DashboardSnapshot


@dataclass
class DashboardService:
    """Provides dashboard data."""
    
    def get_snapshot(self) -> DashboardSnapshot:
        """Get current dashboard snapshot."""
        return DashboardSnapshot(
            timestamp=None,
            portfolio=None,
            active_orders=[],
            recent_fills=[],
            risk_metrics={},
            system_health={},
        )
    
    def get_portfolio_widget(self) -> dict[str, Any]:
        """Get portfolio widget data."""
        return {"equity": 0, "pnl": 0, "positions": []}
    
    def get_orders_widget(self) -> dict[str, Any]:
        """Get orders widget data."""
        return {"open": 0, "filled": 0, "rejected": 0}
    
    def get_risk_widget(self) -> dict[str, Any]:
        """Get risk widget data."""
        return {"utilization": 0, "limits": {}}