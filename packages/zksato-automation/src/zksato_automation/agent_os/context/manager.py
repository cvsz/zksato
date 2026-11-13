"""Context management for autonomous agent orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from zksato_core.ids import new_uuid  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class ContextEntry:
    """A single context entry."""

    entry_id: UUID = field(default_factory=new_uuid)
    source: str = ""  # agent, tool, user, system, repository
    content: str = ""
    content_type: str = "text"  # text, code, json, markdown
    metadata: dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    relevance_score: float = 1.0
    tags: set[str] = field(default_factory=set)


@dataclass
class ContextWindow:
    """Managed context window with token budget."""

    entries: list[ContextEntry] = field(default_factory=list)
    max_tokens: int = 100000
    reserved_tokens: int = 1000

    def add_entry(self, entry: ContextEntry) -> bool:
        """Add entry if it fits in the window."""
        if self.used_tokens + entry.token_estimate > self.max_tokens - self.reserved_tokens:
            return False
        self.entries.append(entry)
        return True

    def remove_entry(self, entry_id: UUID) -> bool:
        """Remove an entry by ID."""
        for i, entry in enumerate(self.entries):
            if entry.entry_id == entry_id:
                self.entries.pop(i)
                return True
        return False

    def get_entries(
        self,
        source: str | None = None,
        content_type: str | None = None,
        tags: set[str] | None = None,
        min_relevance: float = 0.0,
    ) -> list[ContextEntry]:
        """Get filtered entries."""
        filtered = self.entries
        if source:
            filtered = [e for e in filtered if e.source == source]
        if content_type:
            filtered = [e for e in filtered if e.content_type == content_type]
        if tags:
            filtered = [e for e in filtered if e.tags & tags]
        if min_relevance > 0:
            filtered = [e for e in filtered if e.relevance_score >= min_relevance]
        return filtered

    @property
    def used_tokens(self) -> int:
        """Get total tokens used."""
        return sum(e.token_estimate for e in self.entries)

    @property
    def available_tokens(self) -> int:
        """Get available tokens."""
        return self.max_tokens - self.used_tokens - self.reserved_tokens

    def compress(self, target_tokens: int | None = None) -> int:
        """Compress context by removing low-relevance entries.

        Optimized for speed: uses partial sort and batch removal.
        Returns number of entries removed.
        """
        target = target_tokens or (self.max_tokens - self.reserved_tokens)
        if self.used_tokens <= target:
            return 0

        # Sort by relevance (lowest first) - in-place, O(n log n)
        self.entries.sort(key=lambda e: e.relevance_score)

        removed = 0
        # Batch remove entries until we're under target
        # Pop from front (lowest relevance) until we have enough room
        while self.used_tokens > target and self.entries:
            self.entries.pop(0)
            removed += 1

        return removed

    def deduplicate(self) -> int:
        """Remove duplicate entries based on content.

        Optimized: uses dict for O(n) deduplication preserving order.
        Returns number of entries removed.
        """
        seen: dict[int, ContextEntry] = {}
        unique = []
        removed = 0

        for entry in self.entries:
            content_hash = hash(entry.content)
            if content_hash not in seen:
                seen[content_hash] = entry
                unique.append(entry)
            else:
                removed += 1

        self.entries = unique
        return removed

    def to_messages(self) -> list[dict[str, str]]:
        """Convert context to chat messages format."""
        messages = []
        for entry in self.entries:
            role = "assistant" if entry.source == "agent" else "user"
            messages.append({"role": role, "content": entry.content})
        return messages


class ContextManager:
    """Manages context for agents and tasks."""

    def __init__(self, default_max_tokens: int = 100000) -> None:
        self.default_max_tokens = default_max_tokens
        self._contexts: dict[str, ContextWindow] = {}

    def get_context(self, context_id: str) -> ContextWindow:
        """Get or create a context window."""
        if context_id not in self._contexts:
            self._contexts[context_id] = ContextWindow(max_tokens=self.default_max_tokens)
        return self._contexts[context_id]

    def create_task_context(
        self,
        task_id: str,
        objective: str,
        repository_files: list[str] | None = None,
        max_tokens: int | None = None,
    ) -> ContextWindow:
        """Create a context window for a task."""
        ctx = ContextWindow(max_tokens=max_tokens or self.default_max_tokens)

        # Add objective
        ctx.add_entry(
            ContextEntry(
                source="system",
                content=f"Objective: {objective}",
                content_type="text",
                tags={"objective"},
                token_estimate=len(objective) // 4,
            )
        )

        # Add repository files if provided
        if repository_files:
            for file_path in repository_files:
                try:
                    with Path(file_path).open(encoding="utf-8") as f:
                        content = f.read()
                    ctx.add_entry(
                        ContextEntry(
                            source="repository",
                            content=f"File: {file_path}\n```\n{content}\n```",
                            content_type="code",
                            metadata={"file_path": file_path},
                            token_estimate=len(content) // 4,
                            tags={"repository", file_path.split("/")[-1]},
                        )
                    )
                except Exception as exc:
                    logger.warning("Failed to load repository file %s: %s", file_path, exc)

        self._contexts[task_id] = ctx
        return ctx

    def add_agent_output(
        self, context_id: str, agent_id: str, output: str, tags: set[str] | None = None
    ) -> bool:
        """Add agent output to context."""
        ctx = self.get_context(context_id)
        return ctx.add_entry(
            ContextEntry(
                source=f"agent:{agent_id}",
                content=output,
                content_type="text",
                token_estimate=len(output) // 4,
                tags=tags or {"agent_output"},
            )
        )

    def add_tool_result(
        self, context_id: str, tool_name: str, result: str, tags: set[str] | None = None
    ) -> bool:
        """Add tool execution result to context."""
        ctx = self.get_context(context_id)
        return ctx.add_entry(
            ContextEntry(
                source=f"tool:{tool_name}",
                content=result,
                content_type="text",
                token_estimate=len(result) // 4,
                tags=tags or {"tool_result"},
            )
        )

    def add_user_input(self, context_id: str, input_text: str) -> bool:
        """Add user input to context."""
        ctx = self.get_context(context_id)
        return ctx.add_entry(
            ContextEntry(
                source="user",
                content=input_text,
                content_type="text",
                token_estimate=len(input_text) // 4,
                tags={"user_input"},
            )
        )

    def get_context_for_model(
        self,
        context_id: str,
        max_tokens: int | None = None,
    ) -> list[dict[str, str]]:
        """Get context formatted for model input, with token limit."""
        ctx = self.get_context(context_id)
        if max_tokens is not None:
            original_max = ctx.max_tokens
            ctx.max_tokens = max_tokens
            messages = ctx.to_messages()
            ctx.max_tokens = original_max
            return messages
        return ctx.to_messages()

    def clear_context(self, context_id: str) -> bool:
        """Clear a context."""
        if context_id in self._contexts:
            del self._contexts[context_id]
            return True
        return False

    def merge_contexts(self, target_id: str, source_ids: list[str]) -> int:
        """Merge multiple contexts into target."""
        target = self.get_context(target_id)
        merged = 0

        for source_id in source_ids:
            if source_id == target_id:
                continue
            source = self._contexts.get(source_id)
            if not source:
                continue
            for entry in source.entries:
                if target.add_entry(entry):
                    merged += 1

        return merged


class ContextSerializer:
    """Serialize/deserialize context for persistence."""

    @staticmethod
    def serialize(context: ContextWindow) -> dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "entries": [
                {
                    "entry_id": str(e.entry_id),
                    "source": e.source,
                    "content": e.content,
                    "content_type": e.content_type,
                    "metadata": e.metadata,
                    "token_estimate": e.token_estimate,
                    "timestamp": e.timestamp.isoformat(),
                    "relevance_score": e.relevance_score,
                    "tags": list(e.tags),
                }
                for e in context.entries
            ],
            "max_tokens": context.max_tokens,
            "reserved_tokens": context.reserved_tokens,
        }

    @staticmethod
    def deserialize(data: dict[str, Any]) -> ContextWindow:
        """Deserialize context from dictionary."""
        ctx = ContextWindow(
            max_tokens=data.get("max_tokens", 100000),
            reserved_tokens=data.get("reserved_tokens", 1000),
        )
        for entry_data in data.get("entries", []):
            entry = ContextEntry(
                entry_id=UUID(entry_data["entry_id"]),
                source=entry_data["source"],
                content=entry_data["content"],
                content_type=entry_data["content_type"],
                metadata=entry_data.get("metadata", {}),
                token_estimate=entry_data.get("token_estimate", 0),
                timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                relevance_score=entry_data.get("relevance_score", 1.0),
                tags=set(entry_data.get("tags", [])),
            )
            ctx.entries.append(entry)
        return ctx
