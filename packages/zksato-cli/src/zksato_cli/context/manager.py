"""Context management for ZKSATO coding agent.

Provides token budgeting, summarization, compaction, and cross-session context sharing.
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ContextEntry:
    """A single context entry."""

    entry_id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:8])
    source: str = ""  # user, assistant, tool, system, file, summary
    content: str = ""
    content_type: str = "text"  # text, code, json, diff, summary
    metadata: dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    importance: float = 1.0  # 0.0 to 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tags: set[str] = field(default_factory=set)


@dataclass
class ContextWindow:
    """Managed context window with token budget."""

    entries: list[ContextEntry] = field(default_factory=list)
    max_tokens: int = 100000
    reserved_tokens: int = 5000

    def add_entry(self, entry: ContextEntry) -> bool:
        """Add entry if it fits in the window."""
        if self.used_tokens + entry.token_count > self.max_tokens - self.reserved_tokens:
            return False
        self.entries.append(entry)
        return True

    def remove_entry(self, entry_id: str) -> bool:
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
        min_importance: float = 0.0,
    ) -> list[ContextEntry]:
        """Get filtered entries."""
        filtered = self.entries
        if source:
            filtered = [e for e in filtered if e.source == source]
        if content_type:
            filtered = [e for e in filtered if e.content_type == content_type]
        if tags:
            filtered = [e for e in filtered if e.tags & tags]
        if min_importance > 0:
            filtered = [e for e in filtered if e.importance >= min_importance]
        return filtered

    @property
    def used_tokens(self) -> int:
        """Get total tokens used."""
        return sum(e.token_count for e in self.entries)

    @property
    def available_tokens(self) -> int:
        """Get available tokens."""
        return self.max_tokens - self.used_tokens - self.reserved_tokens

    def compact(self, target_tokens: int | None = None, strategy: str = "importance") -> int:
        """Compact context by removing low-importance entries."""
        target = target_tokens or (self.max_tokens - self.reserved_tokens)
        if self.used_tokens <= target:
            return 0

        if strategy == "importance":
            # Sort by importance (lowest first)
            self.entries.sort(key=lambda e: e.importance)
        elif strategy == "recency":
            # Sort by creation time (oldest first)
            self.entries.sort(key=lambda e: e.created_at)
        elif strategy == "size":
            # Sort by token count (largest first)
            self.entries.sort(key=lambda e: e.token_count, reverse=True)

        removed = 0
        while self.used_tokens > target and self.entries:
            removed_entry = self.entries.pop(0)
            removed += 1
            logger.debug(
                "Removed context entry %s (importance: %.2f)",
                removed_entry.entry_id,
                removed_entry.importance,
            )

        return removed

    def deduplicate(self) -> int:
        """Remove duplicate entries based on content."""
        seen = set()
        unique = []
        removed = 0

        for entry in self.entries:
            content_hash = hash(entry.content)
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(entry)
            else:
                removed += 1

        self.entries = unique
        return removed

    def summarize(self, model: str = "gpt-4o-mini", max_summary_tokens: int = 2000) -> str:
        """Generate a summary of the context window."""
        # This would use an LLM to generate a summary
        # For now, return a simple text summary
        summary_parts = [
            f"Context Summary ({len(self.entries)} entries, {self.used_tokens} tokens):"
        ]

        summary_parts.extend(
            f"  [{entry.source}] {entry.content[:100]}..." for entry in self.entries[-10:]
        )  # Last 10 entries

        return "\n".join(summary_parts)

    def to_messages(self) -> list[dict[str, str]]:
        """Convert context to chat messages format."""
        messages = []
        for entry in self.entries:
            role = "assistant" if entry.source == "assistant" else "user"
            messages.append({"role": role, "content": entry.content})
        return messages


class ContextManager:
    """Manages context for agents and tasks."""

    def __init__(
        self,
        default_max_tokens: int = 100000,
        encoding_name: str = "cl100k_base",
        storage_dir: str = ".zksato/contexts",
    ) -> None:
        self.default_max_tokens = default_max_tokens
        self._encoding = None
        if TIKTOKEN_AVAILABLE:
            with contextlib.suppress(Exception):
                self._encoding = tiktoken.get_encoding(encoding_name)
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._contexts: dict[str, ContextWindow] = {}
        self._load_all()

    def _get_context_file(self, context_id: str) -> Path:
        """Get the context file path."""
        return self.storage_dir / f"{context_id}.json"

    def _load_all(self) -> None:
        """Load all contexts from storage."""
        for context_file in self.storage_dir.glob("*.json"):
            try:
                with context_file.open("r") as f:
                    data = json.load(f)
                context_id = context_file.stem
                ctx = ContextSerializer.deserialize(data)
                self._contexts[context_id] = ctx
            except Exception as exc:
                logger.warning("Failed to load context %s: %s", context_file, exc)

    def _save_context(self, context_id: str) -> None:
        """Save context to storage."""
        ctx = self._contexts.get(context_id)
        if not ctx:
            return
        context_file = self._get_context_file(context_id)
        try:
            with context_file.open("w") as f:
                json.dump(ContextSerializer.serialize(ctx), f, indent=2)
        except Exception as exc:
            logger.error("Failed to save context %s: %s", context_id, exc)
        self._load_all()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if self._encoding:
            try:
                return len(self._encoding.encode(text))
            except Exception:
                pass
        return len(text) // 4  # Rough fallback

    def get_context(self, context_id: str, max_tokens: int | None = None) -> ContextWindow:
        """Get or create a context window."""
        if context_id not in self._contexts:
            self._contexts[context_id] = ContextWindow(
                max_tokens=max_tokens or self.default_max_tokens
            )
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
        obj_tokens = self._estimate_tokens(objective)
        ctx.add_entry(
            ContextEntry(
                source="system",
                content=f"Objective: {objective}",
                content_type="text",
                tags={"objective"},
                token_count=obj_tokens,
            )
        )

        # Add repository files if provided
        if repository_files:
            for file_path in repository_files:
                try:
                    content = Path(file_path).read_text(encoding="utf-8")
                    tokens = self._estimate_tokens(content)
                    if ctx.used_tokens + tokens > ctx.max_tokens - ctx.reserved_tokens:
                        break
                    ctx.add_entry(
                        ContextEntry(
                            source="repository",
                            content=f"File: {file_path}\n```\n{content}\n```",
                            content_type="code",
                            metadata={"file_path": file_path},
                            token_count=tokens,
                            tags={"repository", file_path.split("/")[-1]},
                        )
                    )
                except Exception as exc:
                    logger.warning("Failed to load repository file %s: %s", file_path, exc)

        self._contexts[task_id] = ctx
        self._save_context(task_id)
        return ctx

    def add_agent_output(
        self, context_id: str, agent_id: str, output: str, tags: set[str] | None = None
    ) -> bool:
        """Add agent output to context."""
        ctx = self.get_context(context_id)
        tokens = self._estimate_tokens(output)
        result = ctx.add_entry(
            ContextEntry(
                source=f"agent:{agent_id}",
                content=output,
                content_type="text",
                token_count=tokens,
                tags=tags or {"agent_output"},
            )
        )
        if result:
            self._save_context(context_id)
        return result

    def add_tool_result(
        self, context_id: str, tool_name: str, result: str, tags: set[str] | None = None
    ) -> bool:
        """Add tool execution result to context."""
        ctx = self.get_context(context_id)
        tokens = self._estimate_tokens(result)
        result_val = ctx.add_entry(
            ContextEntry(
                source=f"tool:{tool_name}",
                content=result,
                content_type="text",
                token_count=tokens,
                tags=tags or {"tool_result"},
            )
        )
        if result_val:
            self._save_context(context_id)
        return result_val

    def add_user_input(self, context_id: str, input_text: str) -> bool:
        """Add user input to context."""
        ctx = self.get_context(context_id)
        tokens = self._estimate_tokens(input_text)
        result_val = ctx.add_entry(
            ContextEntry(
                source="user",
                content=input_text,
                content_type="text",
                token_count=tokens,
                tags={"user_input"},
            )
        )
        if result_val:
            self._save_context(context_id)
        return result_val

    def add_file_content(self, context_id: str, file_path: str, content: str) -> bool:
        """Add file content to context."""
        ctx = self.get_context(context_id)
        tokens = self._estimate_tokens(content)
        result_val = ctx.add_entry(
            ContextEntry(
                source="file",
                content=f"File: {file_path}\n```\n{content}\n```",
                content_type="code",
                metadata={"file_path": file_path},
                token_count=tokens,
                tags={"file", file_path.split("/")[-1]},
            )
        )
        if result_val:
            self._save_context(context_id)
        return result_val

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

    def get_stats(self, context_id: str) -> dict[str, Any]:
        """Get context statistics."""
        ctx = self.get_context(context_id)
        return {
            "context_id": context_id,
            "entries": len(ctx.entries),
            "used_tokens": ctx.used_tokens,
            "available_tokens": ctx.available_tokens,
            "max_tokens": ctx.max_tokens,
            "sources": list({e.source for e in ctx.entries}),
            "content_types": list({e.content_type for e in ctx.entries}),
        }


class ContextSerializer:
    """Serialize/deserialize context for persistence."""

    @staticmethod
    def serialize(context: ContextWindow) -> dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "source": e.source,
                    "content": e.content,
                    "content_type": e.content_type,
                    "metadata": e.metadata,
                    "token_count": e.token_count,
                    "importance": e.importance,
                    "created_at": e.created_at.isoformat(),
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
                entry_id=entry_data["entry_id"],
                source=entry_data["source"],
                content=entry_data["content"],
                content_type=entry_data["content_type"],
                metadata=entry_data.get("metadata", {}),
                token_count=entry_data.get("token_count", 0),
                created_at=datetime.fromisoformat(entry_data["created_at"]),
                importance=entry_data.get("importance", 1.0),
                tags=set(entry_data.get("tags", [])),
            )
            ctx.entries.append(entry)
        return ctx
