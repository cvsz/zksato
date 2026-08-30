from __future__ import annotations

from zksato.config import Settings


class PredictionLiveGate:
    """Guarded live-mode scaffold for prediction markets."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enable_live = settings.prediction_enable_live
        self.acknowledge_loss = False
        self.reviewed_adapter = False
        self.kill_switch_ready = False

    def validate(self) -> None:
        if not self.settings.prediction_enabled:
            raise RuntimeError("prediction market is not enabled")
        if not self.enable_live:
            raise RuntimeError("prediction live trading is disabled by server policy")
        if not self.acknowledge_loss:
            raise RuntimeError("live trading locked: acknowledge loss is required")
        if not self.reviewed_adapter:
            raise RuntimeError("live trading locked: adapter review is required")
        if not self.kill_switch_ready:
            raise RuntimeError("live trading locked: kill switch readiness is required")
        raise NotImplementedError(
            "no real-money venue adapter is shipped; implement and independently review one"
        )
