from __future__ import annotations

import random

from zksato.prediction.core import Tick


class SyntheticTickGenerator:
    """Deterministic synthetic tick generator for testing."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def generate(self, count: int = 100) -> list[Tick]:
        ticks: list[Tick] = []
        spot = 100.0
        reference = 100.0
        for i in range(count):
            volatility = abs(self._rng.gauss(0, 0.02))
            momentum = self._rng.gauss(0, 0.5)
            spot_change = self._rng.gauss(0, volatility * spot)
            spot = max(1.0, spot + spot_change)
            reference = max(1.0, reference + self._rng.gauss(0, 0.01 * reference))
            up_ask = max(0.01, min(0.99, 0.5 + self._rng.gauss(0, 0.05)))
            down_ask = max(0.01, min(0.99, 1.0 - up_ask + self._rng.gauss(0, 0.02)))
            ticks.append(
                Tick(
                    timestamp=i,
                    spot=spot,
                    reference=reference,
                    up_ask=up_ask,
                    down_ask=down_ask,
                    volatility=volatility,
                    momentum=momentum,
                )
            )
        return ticks
