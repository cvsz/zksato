"""Change tracking for git repositories.

Tracks modifications, additions, and deletions in the repository
for multi-agent coordination and audit purposes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from zksato_automation.agent_os.git import GitClient

logger = logging.getLogger(__name__)


@dataclass
class ChangeEntry:
    """A single change entry in the tracking system."""

    path: str
    change_type: str  # "added", "modified", "deleted", "renamed"
    old_path: str | None = None
    new_path: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    actor: str = ""
    hash: str = ""


@dataclass
class RepositoryState:
    """Snapshot of repository state for change tracking."""

    head: str | None = None
    branch: str | None = None
    staged_files: list[str] = field(default_factory=list)
    unstaged_files: list[str] = field(default_factory=list)
    untracked_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "head": self.head,
            "branch": self.branch,
            "staged_files": self.staged_files,
            "unstaged_files": self.unstaged_files,
            "untracked_files": self.untracked_files,
            "modified_files": self.modified_files,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    async def from_git_client(cls, client: GitClient) -> RepositoryState:
        """Create RepositoryState from git client."""
        head_result = await client.run("rev-parse", "HEAD")
        branch_result = await client.run("rev-parse", "--abbrev-ref", "HEAD")

        staged_result = await client.run("diff--cached", "--name-only")
        unstaged_result = await client.run("diff", "--name-only")
        untracked_result = await client.run("ls-files", "--others", "--exclude-standard")

        modified_result = await client.run("status", "--porcelain")

        modified = []
        if modified_result.success and modified_result.stdout.strip():
            # Porcelain format: XY path where X=staging, Y=working
            modified.extend(
                line[3:] for line in modified_result.stdout.strip().split("\n") if len(line) >= 2
            )

        return cls(
            head=head_result.stdout.strip() if head_result.success else None,
            branch=branch_result.stdout.strip() if branch_result.success else None,
            staged_files=staged_result.stdout.strip().split("\n")
            if staged_result.stdout.strip()
            else [],
            unstaged_files=unstaged_result.stdout.strip().split("\n")
            if unstaged_result.stdout.strip()
            else [],
            untracked_files=untracked_result.stdout.strip().split("\n")
            if untracked_result.stdout.strip()
            else [],
            modified_files=modified,
            timestamp=datetime.now(UTC),
        )


class ChangeTracker:
    """Tracks changes in a git repository for multi-agent coordination."""

    def __init__(self, client: GitClient | None = None) -> None:
        self.client = client or GitClient()
        self._history: list[RepositoryState] = []
        self._max_history: int = 100

    async def capture_state(self) -> RepositoryState:
        """Capture current repository state."""
        state = await RepositoryState.from_git_client(self.client)
        self._history.append(state)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]
        return state

    async def get_history(self) -> list[RepositoryState]:
        """Get change history."""
        return self._history

    async def get_diff_between(self, index1: int, index2: int) -> dict[str, Any]:
        """Get diff between two state captures."""
        if index1 < 0 or index2 < 0 or index1 >= len(self._history) or index2 >= len(self._history):
            return {"error": "Invalid history index"}

        state1 = self._history[index1]
        state2 = self._history[index2]

        return {
            "from": state1.to_dict(),
            "to": state2.to_dict(),
            "added": [
                f
                for f in state2.untracked_files + state2.modified_files
                if f not in state1.untracked_files + state1.modified_files
            ],
            "removed": [
                f
                for f in state1.untracked_files + state1.modified_files
                if f not in state2.untracked_files + state2.modified_files
            ],
            "changed": [
                f
                for f in state2.modified_files
                if f in state1.modified_files
                and f in state2.untracked_files + state2.modified_files
            ],
        }


# Global tracker instance
_tracker: ChangeTracker | None = None


def get_tracker(client: GitClient | None = None) -> ChangeTracker:
    """Get or create a ChangeTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = ChangeTracker(client)
    return _tracker
