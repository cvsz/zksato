from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from zksato.video_ea import (
    VideoDerivedEaPlanner,
    VideoEaActivationRequest,
    VideoEaBias,
    VideoEaPlan,
    VideoEaTrigger,
)


class VideoEaCycleState(StrEnum):
    IDLE = "idle"
    ARMED = "armed"
    ACTIVE = "active"
    PAUSED = "paused"
    TAKE_PROFIT = "take_profit"
    STOPPED = "stopped"
    INVALIDATED = "invalidated"


_TERMINAL_STATES = {
    VideoEaCycleState.TAKE_PROFIT,
    VideoEaCycleState.STOPPED,
    VideoEaCycleState.INVALIDATED,
}


class VideoEaCycleSnapshot(BaseModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    state: VideoEaCycleState
    symbol: str | None = None
    plan: VideoEaPlan | None = None
    last_price: float | None = None
    fired_trigger_keys: list[str] = Field(default_factory=list)
    fired_quantity: int = Field(default=0, ge=0)
    cycle_pnl_r: float = 0.0
    executable: bool = False


class VideoEaRuntimeEvent(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    state: VideoEaCycleState
    triggers: list[VideoEaTrigger] = Field(default_factory=list)
    reason: str
    executable: bool = False


class VideoEaArmRequest(BaseModel):
    plan: VideoEaPlan
    current_price: float = Field(gt=0)


class VideoEaPriceObservation(BaseModel):
    price: float = Field(gt=0)


class VideoEaRuntimeControlResponse(BaseModel):
    event: VideoEaRuntimeEvent
    snapshot: VideoEaCycleSnapshot


class VideoEaCycleRuntime:
    """Stateful virtual-trigger runtime with no broker execution authority."""

    def __init__(self) -> None:
        self._planner = VideoDerivedEaPlanner()
        self._plan: VideoEaPlan | None = None
        self._state = VideoEaCycleState.IDLE
        self._last_price: float | None = None
        self._fired: set[str] = set()
        self._cycle_pnl_r = 0.0

    @property
    def plan(self) -> VideoEaPlan | None:
        return self._plan

    def arm(self, plan: VideoEaPlan, *, current_price: float) -> VideoEaRuntimeEvent:
        if current_price <= 0:
            raise ValueError("current_price must be positive")
        if not plan.triggers:
            raise ValueError("cannot arm a plan without virtual triggers")
        if plan.executable:
            raise ValueError("video EA plans must remain non-executable")
        if not plan.research_only:
            raise ValueError("video EA plans must remain research-only")
        if self._state in {VideoEaCycleState.ARMED, VideoEaCycleState.ACTIVE}:
            raise ValueError("active cycle must be reset before arming a new plan")
        self._plan = plan
        self._state = VideoEaCycleState.ARMED
        self._last_price = current_price
        self._fired.clear()
        self._cycle_pnl_r = 0.0
        return VideoEaRuntimeEvent(
            event_type="cycle.armed",
            state=self._state,
            reason="bounded virtual ladder armed; no broker call was made",
        )

    def on_price(self, price: float) -> VideoEaRuntimeEvent:
        if price <= 0:
            raise ValueError("price must be positive")
        if self._plan is None or self._last_price is None:
            return self._idle_event()
        if self._state == VideoEaCycleState.PAUSED:
            return VideoEaRuntimeEvent(
                event_type="cycle.paused",
                state=self._state,
                reason="price ignored while the virtual-trigger cycle is paused",
            )
        if self._state not in {VideoEaCycleState.ARMED, VideoEaCycleState.ACTIVE}:
            return self._closed_event()

        if self._invalidated(price):
            self._state = VideoEaCycleState.INVALIDATED
            self._last_price = price
            return VideoEaRuntimeEvent(
                event_type="cycle.invalidated",
                state=self._state,
                reason="price crossed the PA-zone cycle invalidation boundary",
            )

        activation = self._planner.activate(
            VideoEaActivationRequest(
                plan=self._plan,
                previous_price=self._last_price,
                current_price=price,
            )
        )
        self._last_price = price
        fresh = [item for item in activation.triggered if item.dedupe_key not in self._fired]
        for trigger in fresh:
            self._fired.add(trigger.dedupe_key)
        if fresh:
            self._state = VideoEaCycleState.ACTIVE
            return VideoEaRuntimeEvent(
                event_type="trigger.crossed",
                state=self._state,
                triggers=fresh,
                reason=(
                    "new virtual trigger crossings detected; rebuild each intent from trusted "
                    "server data and send it through TradingService/RiskEngine"
                ),
            )
        return VideoEaRuntimeEvent(
            event_type="price.observed",
            state=self._state,
            reason="price updated with no new virtual trigger",
        )

    def on_basket_pnl_r(self, pnl_r: float) -> VideoEaRuntimeEvent:
        if self._plan is None:
            return self._idle_event()
        if self._state in _TERMINAL_STATES:
            return self._closed_event()

        self._cycle_pnl_r = pnl_r
        if pnl_r >= self._plan.basket_take_profit_r:
            self._state = VideoEaCycleState.TAKE_PROFIT
            return VideoEaRuntimeEvent(
                event_type="basket.take_profit",
                state=self._state,
                reason="basket target reached; execution may flatten only through policy",
            )
        if pnl_r <= -self._plan.cycle_stop_r:
            self._state = VideoEaCycleState.STOPPED
            return VideoEaRuntimeEvent(
                event_type="basket.stop",
                state=self._state,
                reason="basket loss boundary reached; execution may reduce exposure safely",
            )
        return VideoEaRuntimeEvent(
            event_type="basket.observed",
            state=self._state,
            reason="basket remains inside configured R boundaries",
        )

    def reset(self) -> VideoEaRuntimeEvent:
        self._plan = None
        self._state = VideoEaCycleState.IDLE
        self._last_price = None
        self._fired.clear()
        self._cycle_pnl_r = 0.0
        return VideoEaRuntimeEvent(
            event_type="cycle.reset",
            state=self._state,
            reason="cycle state cleared; a fresh plan is required",
        )

    def pause(self) -> VideoEaRuntimeEvent:
        if self._plan is None:
            return self._idle_event()
        if self._state in _TERMINAL_STATES:
            return self._closed_event()
        if self._state == VideoEaCycleState.PAUSED:
            return VideoEaRuntimeEvent(
                event_type="cycle.paused",
                state=self._state,
                reason="cycle is already paused",
            )
        self._state = VideoEaCycleState.PAUSED
        return VideoEaRuntimeEvent(
            event_type="cycle.paused",
            state=self._state,
            reason="virtual-trigger evaluation paused; no broker call was made",
        )

    def resume(self) -> VideoEaRuntimeEvent:
        if self._plan is None:
            return self._idle_event()
        if self._state in _TERMINAL_STATES:
            return self._closed_event()
        if self._state != VideoEaCycleState.PAUSED:
            return VideoEaRuntimeEvent(
                event_type="cycle.resumed",
                state=self._state,
                reason="cycle was already accepting virtual observations",
            )
        self._state = VideoEaCycleState.ARMED
        return VideoEaRuntimeEvent(
            event_type="cycle.resumed",
            state=self._state,
            reason="virtual-trigger evaluation resumed; no broker call was made",
        )

    @classmethod
    def from_snapshot(
        cls,
        snapshot: VideoEaCycleSnapshot | dict[str, object],
    ) -> VideoEaCycleRuntime:
        runtime = cls()
        runtime.restore(snapshot)
        return runtime

    def restore(
        self,
        snapshot: VideoEaCycleSnapshot | dict[str, object],
    ) -> VideoEaRuntimeEvent:
        parsed = (
            snapshot
            if isinstance(snapshot, VideoEaCycleSnapshot)
            else VideoEaCycleSnapshot.model_validate(snapshot)
        )
        if parsed.executable:
            raise ValueError("runtime snapshots must remain non-executable")

        plan = parsed.plan
        fired = set(parsed.fired_trigger_keys)
        if len(fired) != len(parsed.fired_trigger_keys):
            raise ValueError("runtime snapshot contains duplicate fired trigger keys")
        if plan is None:
            if parsed.state != VideoEaCycleState.IDLE:
                raise ValueError("non-idle runtime snapshot requires a plan")
            if parsed.symbol is not None or parsed.last_price is not None or fired:
                raise ValueError("idle runtime snapshot cannot contain cycle state")
        else:
            if plan.executable:
                raise ValueError("runtime snapshots must remain non-executable")
            if not plan.research_only:
                raise ValueError("runtime snapshots must remain research-only")
            if parsed.symbol != plan.symbol:
                raise ValueError("runtime snapshot symbol does not match its plan")
            if parsed.state == VideoEaCycleState.IDLE:
                raise ValueError("idle runtime snapshot cannot contain a plan")
            trigger_keys = {trigger.dedupe_key for trigger in plan.triggers}
            if not fired.issubset(trigger_keys):
                raise ValueError("runtime snapshot contains an unknown fired trigger")
            if parsed.last_price is None or parsed.last_price <= 0:
                raise ValueError("active runtime snapshot requires a positive last price")

        self._plan = plan.model_copy(deep=True) if plan is not None else None
        self._state = parsed.state
        self._last_price = parsed.last_price
        self._fired = fired
        self._cycle_pnl_r = parsed.cycle_pnl_r
        return VideoEaRuntimeEvent(
            event_type="cycle.recovered",
            state=self._state,
            reason="durable virtual-trigger state recovered; no broker call was made",
        )

    def snapshot(self) -> VideoEaCycleSnapshot:
        quantity = 0
        if self._plan is not None:
            quantity = sum(
                trigger.quantity
                for trigger in self._plan.triggers
                if trigger.dedupe_key in self._fired
            )
        return VideoEaCycleSnapshot(
            schema_version=1,
            state=self._state,
            symbol=self._plan.symbol if self._plan else None,
            plan=self._plan.model_copy(deep=True) if self._plan else None,
            last_price=self._last_price,
            fired_trigger_keys=sorted(self._fired),
            fired_quantity=quantity,
            cycle_pnl_r=self._cycle_pnl_r,
            executable=False,
        )

    def _invalidated(self, price: float) -> bool:
        if self._plan is None or self._plan.invalidation_price is None:
            return False
        if self._plan.bias == VideoEaBias.LONG:
            return price <= self._plan.invalidation_price
        if self._plan.bias == VideoEaBias.SHORT:
            return price >= self._plan.invalidation_price
        return False

    @staticmethod
    def _idle_event() -> VideoEaRuntimeEvent:
        return VideoEaRuntimeEvent(
            event_type="cycle.idle",
            state=VideoEaCycleState.IDLE,
            reason="no video EA plan is armed",
        )

    def _closed_event(self) -> VideoEaRuntimeEvent:
        return VideoEaRuntimeEvent(
            event_type="cycle.closed",
            state=self._state,
            reason="cycle is terminal and requires an explicit reset",
        )
