"""Session persistence for ZKSATO coding agent.

Provides persistent session storage with resume capability, message history,
tool-call tracking, and execution checkpoints.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Session lifecycle status."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ERROR = "error"


class MessageRole(str, Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    TOOL_RESULT = "tool_result"


@dataclass
class ToolCall:
    """Tool call record."""

    tool_call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    result: str | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: str = "pending"  # pending, completed, error


@dataclass
class SessionMessage:
    """A message in the session conversation."""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.USER
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SessionCheckpoint:
    """Execution checkpoint for recovery."""

    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    label: str = ""
    description: str = ""
    state_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    parent_checkpoint_id: str | None = None


@dataclass
class Session:
    """Persistent coding agent session."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_path: str = ""
    title: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    messages: list[SessionMessage] = field(default_factory=list)
    checkpoints: list[SessionCheckpoint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    total_tokens: int = 0
    total_cost: float = 0.0

    def add_message(self, message: SessionMessage) -> None:
        """Add a message to the session."""
        self.messages.append(message)
        self.updated_at = datetime.now(UTC)
        self.last_activity = datetime.now(UTC)

    def add_checkpoint(self, checkpoint: SessionCheckpoint) -> None:
        """Add a checkpoint."""
        checkpoint.session_id = self.session_id
        self.checkpoints.append(checkpoint)
        self.updated_at = datetime.now(UTC)

    def get_latest_checkpoint(self) -> SessionCheckpoint | None:
        """Get the most recent checkpoint."""
        if not self.checkpoints:
            return None
        return max(self.checkpoints, key=lambda c: c.created_at)

    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)

    def get_tool_call_count(self) -> int:
        """Get total tool call count."""
        return sum(len(m.tool_calls) for m in self.messages)

    def to_dict(self) -> dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "title": self.title,
            "status": self.status.value,
            "messages": [
                {
                    "message_id": m.message_id,
                    "role": m.role.value,
                    "content": m.content,
                    "tool_calls": [
                        {
                            "tool_call_id": tc.tool_call_id,
                            "name": tc.name,
                            "arguments": tc.arguments,
                            "result": tc.result,
                            "error": tc.error,
                            "started_at": tc.started_at.isoformat(),
                            "completed_at": tc.completed_at.isoformat()
                            if tc.completed_at
                            else None,
                            "status": tc.status,
                        }
                        for tc in m.tool_calls
                    ],
                    "metadata": m.metadata,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in self.messages
            ],
            "checkpoints": [
                {
                    "checkpoint_id": c.checkpoint_id,
                    "session_id": c.session_id,
                    "label": c.label,
                    "description": c.description,
                    "state_snapshot": c.state_snapshot,
                    "created_at": c.created_at.isoformat(),
                    "parent_checkpoint_id": c.parent_checkpoint_id,
                }
                for c in self.checkpoints
            ],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Deserialize session from dictionary."""
        session = cls(
            session_id=data["session_id"],
            project_path=data.get("project_path", ""),
            title=data.get("title", ""),
            status=SessionStatus(data.get("status", "active")),
            metadata=data.get("metadata", {}),
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
        )

        if data.get("created_at"):
            session.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            session.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("last_activity"):
            session.last_activity = datetime.fromisoformat(data["last_activity"])

        for msg_data in data.get("messages", []):
            message = SessionMessage(
                message_id=msg_data["message_id"],
                role=MessageRole(msg_data["role"]),
                content=msg_data["content"],
                metadata=msg_data.get("metadata", {}),
            )
            if msg_data.get("timestamp"):
                message.timestamp = datetime.fromisoformat(msg_data["timestamp"])

            for tc_data in msg_data.get("tool_calls", []):
                tool_call = ToolCall(
                    tool_call_id=tc_data["tool_call_id"],
                    name=tc_data["name"],
                    arguments=tc_data["arguments"],
                    result=tc_data.get("result"),
                    error=tc_data.get("error"),
                    status=tc_data.get("status", "pending"),
                )
                if tc_data.get("started_at"):
                    tool_call.started_at = datetime.fromisoformat(tc_data["started_at"])
                if tc_data.get("completed_at"):
                    tool_call.completed_at = datetime.fromisoformat(tc_data["completed_at"])
                message.tool_calls.append(tool_call)

            session.messages.append(message)

        for cp_data in data.get("checkpoints", []):
            checkpoint = SessionCheckpoint(
                checkpoint_id=cp_data["checkpoint_id"],
                session_id=cp_data.get("session_id", ""),
                label=cp_data.get("label", ""),
                description=cp_data.get("description", ""),
                state_snapshot=cp_data.get("state_snapshot", {}),
                parent_checkpoint_id=cp_data.get("parent_checkpoint_id"),
            )
            if cp_data.get("created_at"):
                checkpoint.created_at = datetime.fromisoformat(cp_data["created_at"])
            session.checkpoints.append(checkpoint)

        return session


class SessionStore:
    """Persistent session storage using JSONL files."""

    def __init__(self, storage_dir: Path | str = ".zksato/sessions") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.storage_dir / "index.json"
        self._index: dict[str, dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load session index from disk."""
        if self._index_file.exists():
            try:
                with self._index_file.open("r") as f:
                    self._index = json.load(f)
            except Exception as exc:
                logger.warning("Failed to load session index: %s", exc)
                self._index = {}

    def _save_index(self) -> None:
        """Save session index to disk."""
        try:
            with self._index_file.open("w") as f:
                json.dump(self._index, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save session index: %s", exc)

    def _get_session_file(self, session_id: str) -> Path:
        """Get the session file path."""
        return self.storage_dir / f"{session_id}.jsonl"

    def create_session(
        self,
        project_path: str,
        title: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Create a new session."""
        session = Session(
            project_path=project_path,
            title=title or f"Session {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
            metadata=metadata or {},
        )
        self.save_session(session)
        return session

    def save_session(self, session: Session) -> None:
        """Save session to disk (atomic write)."""
        session.updated_at = datetime.now(UTC)
        session.last_activity = datetime.now(UTC)

        session_file = self._get_session_file(session.session_id)
        temp_file = session_file.with_suffix(".tmp")

        try:
            # Write to temp file first
            with temp_file.open("w") as f:
                for message in session.messages:
                    f.write(
                        json.dumps(
                            {
                                "type": "message",
                                "data": {
                                    "message_id": message.message_id,
                                    "role": message.role.value,
                                    "content": message.content,
                                    "tool_calls": [
                                        {
                                            "tool_call_id": tc.tool_call_id,
                                            "name": tc.name,
                                            "arguments": tc.arguments,
                                            "result": tc.result,
                                            "error": tc.error,
                                            "started_at": tc.started_at.isoformat(),
                                            "completed_at": tc.completed_at.isoformat()
                                            if tc.completed_at
                                            else None,
                                            "status": tc.status,
                                        }
                                        for tc in message.tool_calls
                                    ],
                                    "metadata": message.metadata,
                                    "timestamp": message.timestamp.isoformat(),
                                },
                            }
                        )
                        + "\n"
                    )

                for checkpoint in session.checkpoints:
                    f.write(
                        json.dumps(
                            {
                                "type": "checkpoint",
                                "data": {
                                    "checkpoint_id": checkpoint.checkpoint_id,
                                    "session_id": checkpoint.session_id,
                                    "label": checkpoint.label,
                                    "description": checkpoint.description,
                                    "state_snapshot": checkpoint.state_snapshot,
                                    "created_at": checkpoint.created_at.isoformat(),
                                    "parent_checkpoint_id": checkpoint.parent_checkpoint_id,
                                },
                            }
                        )
                        + "\n"
                    )

                # Write session metadata as last line
                f.write(
                    json.dumps(
                        {
                            "type": "metadata",
                            "data": {
                                "session_id": session.session_id,
                                "project_path": session.project_path,
                                "title": session.title,
                                "status": session.status.value,
                                "metadata": session.metadata,
                                "created_at": session.created_at.isoformat(),
                                "updated_at": session.updated_at.isoformat(),
                                "last_activity": session.last_activity.isoformat(),
                                "total_tokens": session.total_tokens,
                                "total_cost": session.total_cost,
                            },
                        }
                    )
                    + "\n"
                )

            # Atomic rename
            temp_file.replace(session_file)

            # Update index
            self._index[session.session_id] = {
                "session_id": session.session_id,
                "project_path": session.project_path,
                "title": session.title,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "message_count": session.get_message_count(),
                "tool_call_count": session.get_tool_call_count(),
                "total_tokens": session.total_tokens,
                "total_cost": session.total_cost,
            }
            self._save_index()

        except Exception as exc:
            if temp_file.exists():
                temp_file.unlink()
            logger.error("Failed to save session %s: %s", session.session_id, exc)
            raise

    def load_session(self, session_id: str) -> Session | None:
        """Load session from disk."""
        session_file = self._get_session_file(session_id)
        if not session_file.exists():
            return None

        try:
            session = Session(session_id=session_id)
            with session_file.open("r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    record_type = record.get("type")
                    data = record.get("data", {})

                    if record_type == "message":
                        message = SessionMessage(
                            message_id=data["message_id"],
                            role=MessageRole(data["role"]),
                            content=data["content"],
                            metadata=data.get("metadata", {}),
                        )
                        if data.get("timestamp"):
                            message.timestamp = datetime.fromisoformat(data["timestamp"])

                        for tc_data in data.get("tool_calls", []):
                            tool_call = ToolCall(
                                tool_call_id=tc_data["tool_call_id"],
                                name=tc_data["name"],
                                arguments=tc_data["arguments"],
                                result=tc_data.get("result"),
                                error=tc_data.get("error"),
                                status=tc_data.get("status", "pending"),
                            )
                            if tc_data.get("started_at"):
                                tool_call.started_at = datetime.fromisoformat(tc_data["started_at"])
                            if tc_data.get("completed_at"):
                                tool_call.completed_at = datetime.fromisoformat(
                                    tc_data["completed_at"]
                                )
                            message.tool_calls.append(tool_call)

                        session.messages.append(message)

                    elif record_type == "checkpoint":
                        checkpoint = SessionCheckpoint(
                            checkpoint_id=data["checkpoint_id"],
                            session_id=data.get("session_id", ""),
                            label=data.get("label", ""),
                            description=data.get("description", ""),
                            state_snapshot=data.get("state_snapshot", {}),
                            parent_checkpoint_id=data.get("parent_checkpoint_id"),
                        )
                        if data.get("created_at"):
                            checkpoint.created_at = datetime.fromisoformat(data["created_at"])
                        session.checkpoints.append(checkpoint)

                    elif record_type == "metadata":
                        session.project_path = data.get("project_path", "")
                        session.title = data.get("title", "")
                        session.status = SessionStatus(data.get("status", "active"))
                        session.metadata = data.get("metadata", {})
                        if data.get("created_at"):
                            session.created_at = datetime.fromisoformat(data["created_at"])
                        if data.get("updated_at"):
                            session.updated_at = datetime.fromisoformat(data["updated_at"])
                        if data.get("last_activity"):
                            session.last_activity = datetime.fromisoformat(data["last_activity"])
                        session.total_tokens = data.get("total_tokens", 0)
                        session.total_cost = data.get("total_cost", 0.0)

            return session

        except Exception as exc:
            logger.error("Failed to load session %s: %s", session_id, exc)
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            session_file.unlink()
        if session_id in self._index:
            del self._index[session_id]
            self._save_index()
            return True
        return False

    def list_sessions(
        self,
        project_path: str | None = None,
        status: SessionStatus | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List sessions with optional filtering."""
        sessions = list(self._index.values())

        if project_path:
            sessions = [s for s in sessions if s.get("project_path") == project_path]
        if status:
            sessions = [s for s in sessions if s.get("status") == status.value]

        # Sort by last activity (most recent first)
        sessions.sort(key=lambda s: s.get("last_activity", ""), reverse=True)

        return sessions[:limit]

    def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """Get session info from index without loading full session."""
        return self._index.get(session_id)

    def archive_session(self, session_id: str) -> bool:
        """Archive a session."""
        session = self.load_session(session_id)
        if not session:
            return False
        session.status = SessionStatus.ARCHIVED
        self.save_session(session)
        return True

    def recover_interrupted_sessions(self, project_path: str | None = None) -> list[Session]:
        """Find and return sessions that were interrupted (active but stale)."""
        cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        recovered = []

        for session_info in self._index.values():
            if session_info.get("status") != SessionStatus.ACTIVE.value:
                continue
            if project_path and session_info.get("project_path") != project_path:
                continue

            last_activity = session_info.get("last_activity")
            if last_activity:
                try:
                    last_active = datetime.fromisoformat(last_activity)
                    if last_active < cutoff:
                        session = self.load_session(session_info["session_id"])
                        if session:
                            recovered.append(session)
                except Exception:
                    pass

        return recovered


class SessionManager:
    """High-level session management with CLI integration."""

    def __init__(self, storage_dir: Path | str = ".zksato/sessions") -> None:
        self.store = SessionStore(storage_dir)
        self._current_session: Session | None = None

    @property
    def current_session(self) -> Session | None:
        """Get the current active session."""
        return self._current_session

    def create_session(
        self,
        project_path: str,
        title: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Create and set as current session."""
        session = self.store.create_session(project_path, title, metadata)
        self._current_session = session
        return session

    def resume_session(self, session_id: str) -> Session | None:
        """Resume a previous session."""
        session = self.store.load_session(session_id)
        if session:
            session.status = SessionStatus.ACTIVE
            self.store.save_session(session)
            self._current_session = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        return self.store.load_session(session_id)

    def list_sessions(
        self,
        project_path: str | None = None,
        status: SessionStatus | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List sessions."""
        return self.store.list_sessions(project_path, status, limit)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if self._current_session and self._current_session.session_id == session_id:
            self._current_session = None
        return self.store.delete_session(session_id)

    def add_message(self, message: SessionMessage) -> None:
        """Add a message to the current session."""
        if self._current_session:
            self._current_session.add_message(message)
            self.store.save_session(self._current_session)

    def add_checkpoint(
        self, label: str, description: str, state_snapshot: dict[str, Any]
    ) -> SessionCheckpoint | None:
        """Create a checkpoint in the current session."""
        if not self._current_session:
            return None

        checkpoint = SessionCheckpoint(
            label=label,
            description=description,
            state_snapshot=state_snapshot,
        )
        parent = self._current_session.get_latest_checkpoint()
        if parent:
            checkpoint.parent_checkpoint_id = parent.checkpoint_id

        self._current_session.add_checkpoint(checkpoint)
        self.store.save_session(self._current_session)
        return checkpoint

    def get_latest_checkpoint(self) -> SessionCheckpoint | None:
        """Get the latest checkpoint from current session."""
        if self._current_session:
            return self._current_session.get_latest_checkpoint()
        return None

    def export_session(self, session_id: str, output_path: Path) -> bool:
        """Export session to a portable JSON file."""
        session = self.store.load_session(session_id)
        if not session:
            return False

        try:
            with output_path.open("w") as f:
                json.dump(session.to_dict(), f, indent=2)
            return True
        except Exception as exc:
            logger.error("Failed to export session: %s", exc)
            return False

    def import_session(self, input_path: Path) -> Session | None:
        """Import session from a portable JSON file."""
        try:
            with input_path.open("r") as f:
                data = json.load(f)
            session = Session.from_dict(data)
            self.store.save_session(session)
            return session
        except Exception as exc:
            logger.error("Failed to import session: %s", exc)
            return None
