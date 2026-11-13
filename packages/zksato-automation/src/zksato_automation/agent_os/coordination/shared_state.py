"""Shared state management for multi-agent coordination.

Implements CRDT-based distributed state synchronization for conflict-free
replicated data types across multiple agents.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CRDTBase:
    """Base class for CRDTs."""

    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 0

    def merge(self, other: CRDTBase) -> bool:
        """Merge with another CRDT. Returns True if changed."""
        if other.version > self.version:
            self.version = other.version
            self.last_updated = other.last_updated
            return True
        return False


@dataclass
class GCounter(CRDTBase):
    """Grow-only Counter CRDT."""

    counts: dict[str, int] = field(default_factory=dict)

    def increment(self, actor: str, value: int = 1) -> None:
        """Increment counter for an actor."""
        self.counts[actor] = self.counts.get(actor, 0) + value
        self.version += 1
        self.last_updated = datetime.now(UTC)

    def value(self) -> int:
        """Get total count."""
        return sum(self.counts.values())

    def merge(self, other: CRDTBase) -> bool:
        if not isinstance(other, GCounter):
            return False
        changed = False
        for actor, count in other.counts.items():
            if count > self.counts.get(actor, 0):
                self.counts[actor] = count
                changed = True
        if changed or super().merge(other):
            self.version = max(self.version, other.version) + 1
            return True
        return False


@dataclass
class PNCounter(CRDTBase):
    """Positive-Negative Counter CRDT (supports increment and decrement)."""

    positive: GCounter = field(default_factory=GCounter)
    negative: GCounter = field(default_factory=GCounter)

    def increment(self, actor: str, value: int = 1) -> None:
        """Increment counter."""
        self.positive.increment(actor, value)
        self.version += 1
        self.last_updated = datetime.now(UTC)

    def decrement(self, actor: str, value: int = 1) -> None:
        """Decrement counter."""
        self.negative.increment(actor, value)
        self.version += 1
        self.last_updated = datetime.now(UTC)

    def value(self) -> int:
        """Get current value (positive - negative)."""
        return self.positive.value() - self.negative.value()

    def merge(self, other: CRDTBase) -> bool:
        if not isinstance(other, PNCounter):
            return False
        p_changed = self.positive.merge(other.positive)
        n_changed = self.negative.merge(other.negative)
        if p_changed or n_changed or super().merge(other):
            self.version = max(self.version, other.version) + 1
            return True
        return False


@dataclass
class LWWRegister(CRDTBase):
    """Last-Writer-Wins Register CRDT."""

    value: Any = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    actor: str = ""

    def set(self, value: Any, actor: str) -> None:
        """Set value with timestamp."""
        now = datetime.now(UTC)
        if now >= self.timestamp:
            self.value = value
            self.timestamp = now
            self.actor = actor
            self.version += 1
            self.last_updated = now

    def get(self) -> Any:
        """Get current value."""
        return self.value

    def merge(self, other: CRDTBase) -> bool:
        if not isinstance(other, LWWRegister):
            return False
        if other.timestamp > self.timestamp:
            self.value = other.value
            self.timestamp = other.timestamp
            self.actor = other.actor
            self.version = max(self.version, other.version) + 1
            self.last_updated = datetime.now(UTC)
            return True
        return False


@dataclass
class ORSet(CRDTBase):
    """Observed-Remove Set CRDT."""

    elements: dict[Any, dict[str, tuple[datetime, bool]]] = field(default_factory=dict)
    # element -> {actor: (timestamp, is_add)}

    def add(self, element: Any, actor: str) -> None:
        """Add element."""
        now = datetime.now(UTC)
        if element not in self.elements:
            self.elements[element] = {}
        self.elements[element][actor] = (now, True)
        self.version += 1
        self.last_updated = now

    def remove(self, element: Any, actor: str) -> None:
        """Remove element."""
        now = datetime.now(UTC)
        if element in self.elements:
            self.elements[element][actor] = (now, False)
            self.version += 1
            self.last_updated = now

    def contains(self, element: Any) -> bool:
        """Check if element is in set."""
        if element not in self.elements:
            return False
        # Element is present if any actor has added it more recently than removed it
        return any(is_add for actor, (timestamp, is_add) in self.elements[element].items())

    def get_elements(self) -> set[Any]:
        """Get current elements."""
        result = set()
        for element, actors in self.elements.items():
            # Check if any actor has it added more recently than removed
            latest_add = None
            latest_remove = None
            for timestamp, is_add in actors.values():
                if is_add and (latest_add is None or timestamp > latest_add):
                    latest_add = timestamp
                elif not is_add and (latest_remove is None or timestamp > latest_remove):
                    latest_remove = timestamp
            if latest_add and (latest_remove is None or latest_add >= latest_remove):
                result.add(element)
        return result

    def merge(self, other: CRDTBase) -> bool:
        if not isinstance(other, ORSet):
            return False
        changed = False
        for element, actors in other.elements.items():
            if element not in self.elements:
                self.elements[element] = {}
                changed = True
            for actor, (timestamp, is_add) in actors.items():
                if (
                    actor not in self.elements[element]
                    or timestamp > self.elements[element][actor][0]
                ):
                    self.elements[element][actor] = (timestamp, is_add)
                    changed = True
        if changed or super().merge(other):
            self.version = max(self.version, other.version) + 1
            return True
        return False


@dataclass
class LWWMap(CRDTBase):
    """Last-Writer-Wins Map CRDT."""

    data: dict[str, tuple[Any, datetime, str]] = field(default_factory=dict)
    # key -> (value, timestamp, actor)

    def set(self, key: str, value: Any, actor: str) -> None:
        """Set key-value pair."""
        now = datetime.now(UTC)
        if key not in self.data or now >= self.data[key][1]:
            self.data[key] = (value, now, actor)
            self.version += 1
            self.last_updated = now

    def get(self, key: str, default: Any = None) -> Any:
        """Get value for key."""
        return self.data.get(key, (default,))[0]

    def delete(self, key: str, actor: str) -> bool:
        """Delete a key."""
        if key in self.data:
            now = datetime.now(UTC)
            self.data[key] = (None, now, actor)
            self.version += 1
            self.last_updated = now
            return True
        return False

    def keys(self) -> list[str]:
        """Get all keys with non-None values."""
        return [k for k, v in self.data.items() if v[0] is not None]

    def items(self) -> list[tuple[str, Any]]:
        """Get all items with non-None values."""
        return [(k, v[0]) for k, v in self.data.items() if v[0] is not None]

    def merge(self, other: CRDTBase) -> bool:
        if not isinstance(other, LWWMap):
            return False
        changed = False
        for key, (value, timestamp, actor) in other.data.items():
            if key not in self.data or timestamp > self.data[key][1]:
                self.data[key] = (value, timestamp, actor)
                changed = True
        if changed or super().merge(other):
            self.version = max(self.version, other.version) + 1
            return True
        return False


class SharedStateManager:
    """Manages shared state across agents using CRDTs."""

    def __init__(self) -> None:
        self.counters: dict[str, GCounter] = {}
        self.pn_counters: dict[str, PNCounter] = {}
        self.registers: dict[str, LWWRegister] = {}
        self.sets: dict[str, ORSet] = {}
        self.maps: dict[str, LWWMap] = {}
        self._lock = asyncio.Lock()

    def get_counter(self, name: str) -> GCounter:
        """Get or create a G-Counter."""
        if name not in self.counters:
            self.counters[name] = GCounter()
        return self.counters[name]

    def get_pn_counter(self, name: str) -> PNCounter:
        """Get or create a PN-Counter."""
        if name not in self.pn_counters:
            self.pn_counters[name] = PNCounter()
        return self.pn_counters[name]

    def get_register(self, name: str) -> LWWRegister:
        """Get or create an LWW Register."""
        if name not in self.registers:
            self.registers[name] = LWWRegister()
        return self.registers[name]

    def get_set(self, name: str) -> ORSet:
        """Get or create an OR-Set."""
        if name not in self.sets:
            self.sets[name] = ORSet()
        return self.sets[name]

    def get_map(self, name: str) -> LWWMap:
        """Get or create an LWW Map."""
        if name not in self.maps:
            self.maps[name] = LWWMap()
        return self.maps[name]

    async def merge_state(self, other_state: dict[str, Any]) -> bool:
        """Merge state from another agent."""
        async with self._lock:
            changed = False

            # Merge counters
            for name, data in other_state.get("counters", {}).items():
                counter = self.get_counter(name)
                other_counter = GCounter()
                other_counter.counts = data
                if counter.merge(other_counter):
                    changed = True

            # Merge registers
            for name, data in other_state.get("registers", {}).items():
                register = self.get_register(name)
                other_register = LWWRegister(
                    value=data["value"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    actor=data["actor"],
                )
                if register.merge(other_register):
                    changed = True

            # Merge sets
            for name, data in other_state.get("sets", {}).items():
                orset = self.get_set(name)
                other_orset = ORSet()
                other_orset.elements = data
                if orset.merge(other_orset):
                    changed = True

            # Merge maps
            for name, data in other_state.get("maps", {}).items():
                lww_map = self.get_map(name)
                other_map = LWWMap()
                other_map.data = data
                if lww_map.merge(other_map):
                    changed = True

            return changed

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            "counters": {name: c.counts for name, c in self.counters.items()},
            "pn_counters": {
                name: {"positive": c.positive.counts, "negative": c.negative.counts}
                for name, c in self.pn_counters.items()
            },
            "registers": {
                name: {"value": r.value, "timestamp": r.timestamp.isoformat(), "actor": r.actor}
                for name, r in self.registers.items()
            },
            "sets": {name: s.elements for name, s in self.sets.items()},
            "maps": {name: m.data for name, m in self.maps.items()},
        }


class StateSynchronizer:
    """Synchronizes state across agents."""

    def __init__(self, manager: SharedStateManager, agent_id: str) -> None:
        self.manager = manager
        self.agent_id = agent_id
        self._peers: dict[str, Any] = {}  # peer_id -> communicator

    def register_peer(self, peer_id: str, communicator: Any) -> None:
        """Register a peer for synchronization."""
        self._peers[peer_id] = communicator

    async def sync_with_peer(self, peer_id: str) -> bool:
        """Synchronize state with a specific peer."""
        communicator = self._peers.get(peer_id)
        if not communicator:
            return False

        try:
            # Request peer's state
            peer_state = await communicator.get_state()
            if peer_state:
                return await self.manager.merge_state(peer_state)
        except Exception as exc:
            logger.error("Failed to sync with peer %s: %s", peer_id, exc)
        return False

    async def broadcast_state(self) -> int:
        """Broadcast state to all peers."""
        state = self.manager.to_dict()
        synced = 0
        for peer_id, communicator in self._peers.items():
            try:
                await communicator.send_state(state)
                synced += 1
            except Exception as exc:
                logger.error("Failed to send state to %s: %s", peer_id, exc)
        return synced

    async def periodic_sync(self, interval: float = 5.0) -> None:
        """Periodically synchronize with all peers."""
        while True:
            await asyncio.sleep(interval)
            try:
                await self.broadcast_state()
                # Also sync with each peer
                for peer_id in self._peers:
                    await self.sync_with_peer(peer_id)
            except Exception as exc:
                logger.error("Periodic sync error: %s", exc)
