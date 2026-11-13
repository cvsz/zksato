"""Strategy memory and context persistence."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from zksato_strategy.research import ResearchNote, StrategyContext


class MemoryStore(Protocol):
    """Protocol for memory storage backends."""

    async def save_context(self, context: StrategyContext) -> None: ...
    async def load_context(self, strategy_id: str) -> StrategyContext | None: ...
    async def save_note(self, note: ResearchNote) -> None: ...
    async def get_notes(
        self, strategy_id: str | None = None, symbol: str | None = None
    ) -> list[ResearchNote]: ...


class FileMemoryStore:
    """File-based memory store."""

    def __init__(self, base_path: str | Path = "./data/memory") -> None:
        self.base_path = Path(base_path)
        self.contexts_dir = self.base_path / "contexts"
        self.notes_dir = self.base_path / "notes"
        self.contexts_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    async def save_context(self, context: StrategyContext) -> None:
        """Save strategy context to file."""
        context.last_updated = datetime.now(UTC)
        file_path = self.contexts_dir / f"{context.strategy_id}.json"
        file_path.write_text(json.dumps(asdict(context), default=str, indent=2))

    async def load_context(self, strategy_id: str) -> StrategyContext | None:
        """Load strategy context from file."""
        file_path = self.contexts_dir / f"{strategy_id}.json"
        if not file_path.exists():
            return None
        data = json.loads(file_path.read_text())
        # Convert datetime strings back
        for key in ["last_updated"]:
            if key in data and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return StrategyContext(**data)

    async def save_note(self, note: ResearchNote) -> None:
        """Save research note to file."""
        note.created_at = datetime.now(UTC)
        file_path = (
            self.notes_dir / f"{note.strategy_id}_{note.symbol}_{note.created_at.isoformat()}.json"
        )
        file_path.write_text(json.dumps(asdict(note), default=str, indent=2))

    async def get_notes(
        self,
        strategy_id: str | None = None,
        symbol: str | None = None,
    ) -> list[ResearchNote]:
        """Get research notes."""
        notes = []
        for file_path in self.notes_dir.glob("*.json"):
            data = json.loads(file_path.read_text())
            note = ResearchNote(**data)
            if strategy_id and note.strategy_id != strategy_id:
                continue
            if symbol and note.symbol != symbol:
                continue
            notes.append(note)
        return notes


class InMemoryStore:
    """In-memory memory store for testing."""

    def __init__(self) -> None:
        self._contexts: dict[str, StrategyContext] = {}
        self._notes: list[ResearchNote] = []

    async def save_context(self, context: StrategyContext) -> None:
        self._contexts[context.strategy_id] = context

    async def load_context(self, strategy_id: str) -> StrategyContext | None:
        return self._contexts.get(strategy_id)

    async def save_note(self, note: ResearchNote) -> None:
        self._notes.append(note)

    async def get_notes(
        self,
        strategy_id: str | None = None,
        symbol: str | None = None,
    ) -> list[ResearchNote]:
        notes = self._notes
        if strategy_id:
            notes = [n for n in notes if n.strategy_id == strategy_id]
        if symbol:
            notes = [n for n in notes if n.symbol == symbol]
        return notes


class StrategyMemory:
    """High-level strategy memory manager."""

    def __init__(self, store: MemoryStore | None = None) -> None:
        self.store = store or InMemoryStore()

    async def save_context(self, strategy_id: str, context: StrategyContext) -> None:
        await self.store.save_context(context)

    async def load_context(self, strategy_id: str) -> StrategyContext | None:
        return await self.store.load_context(strategy_id)

    async def save_research_note(self, note: ResearchNote) -> None:
        await self.store.save_note(note)

    async def get_research_notes(
        self,
        strategy_id: str | None = None,
        symbol: str | None = None,
    ) -> list[ResearchNote]:
        return await self.store.get_notes(strategy_id, symbol)

    async def warm_start(self, strategy_id: str) -> StrategyContext | None:
        """Load context for warm start."""
        return await self.load_context(strategy_id)
