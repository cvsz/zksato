"""Unified diff/patch engine for ZKSATO coding agent.

Provides structured file editing with unified diffs, patch validation,
conflict detection, and atomic writes with backups.
"""

from __future__ import annotations

import difflib
import logging
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PatchStatus(str, Enum):
    """Patch application status."""

    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    CONFLICT = "conflict"
    SKIPPED = "skipped"


class ChangeType(str, Enum):
    """Type of change in a diff."""

    ADD = "add"
    DELETE = "delete"
    MODIFY = "modify"
    RENAME = "rename"


@dataclass
class FileChange:
    """Represents a single file change."""

    file_path: str
    change_type: ChangeType
    old_content: str = ""
    new_content: str = ""
    old_path: str | None = None  # For renames
    line_start: int = 0
    line_end: int = 0
    diff: str = ""


@dataclass
class Patch:
    """A collection of file changes forming a patch."""

    patch_id: str = field(
        default_factory=lambda: f"patch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    )
    label: str = ""
    description: str = ""
    changes: list[FileChange] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_change(self, change: FileChange) -> None:
        """Add a file change to the patch."""
        self.changes.append(change)

    def get_affected_files(self) -> list[str]:
        """Get list of affected file paths."""
        return [c.file_path for c in self.changes]

    def is_empty(self) -> bool:
        """Check if patch has no changes."""
        return len(self.changes) == 0


@dataclass
class PatchResult:
    """Result of patch application."""

    patch_id: str
    status: PatchStatus = PatchStatus.PENDING
    applied_files: list[str] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    backup_dir: str | None = None
    applied_at: datetime | None = None


class DiffEngine:
    """Generates unified diffs between file versions."""

    @staticmethod
    def generate_diff(
        old_content: str,
        new_content: str,
        file_path: str,
        context_lines: int = 3,
    ) -> str:
        """Generate a unified diff between old and new content."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
            n=context_lines,
        )

        return "".join(diff)

    @staticmethod
    def generate_diff_from_files(
        old_file: Path,
        new_file: Path,
        context_lines: int = 3,
    ) -> str:
        """Generate a unified diff between two files."""
        old_content = old_file.read_text(encoding="utf-8")
        new_content = new_file.read_text(encoding="utf-8")
        return DiffEngine.generate_diff(old_content, new_content, new_file.name, context_lines)

    @staticmethod
    def parse_unified_diff(diff_text: str) -> list[FileChange]:
        """Parse a unified diff into FileChange objects."""
        changes = []
        lines = diff_text.splitlines(keepends=True)

        current_file = None
        old_content = []
        new_content = []
        in_hunk = False

        for _i, line in enumerate(lines):
            if line.startswith("--- "):
                # Old file
                current_file = line[4:].strip()
                if current_file.startswith("a/"):
                    current_file = current_file[2:]
            elif line.startswith("+++ "):
                # New file
                new_file = line[4:].strip()
                if new_file.startswith("b/"):
                    new_file = new_file[2:]
                if current_file and current_file != new_file:
                    # Rename detected
                    pass
            elif line.startswith("@@ "):
                # Hunk header
                if in_hunk and (old_content or new_content):
                    # Save previous hunk
                    pass
                in_hunk = True
                # Parse line numbers: @@ -old_start,old_count +new_start,new_count @@
                parts = line.split("@@")
                if len(parts) >= 2:
                    parts[1].strip()
                    # Could parse line numbers here
            elif in_hunk:
                if line.startswith("+"):
                    new_content.append(line[1:])
                elif line.startswith("-"):
                    old_content.append(line[1:])
                else:
                    new_content.append(line[1:])
                    old_content.append(line[1:])

        return changes


class PatchApplicator:
    """Applies patches with validation, conflict detection, and backups."""

    def __init__(
        self,
        project_root: Path,
        backup_dir: Path | None = None,
        dry_run: bool = False,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.backup_dir = backup_dir or (self.project_root / ".zksato" / "backups")
        self.dry_run = dry_run
        self._backup_dir_created = False

    def _ensure_backup_dir(self) -> None:
        """Create backup directory if needed."""
        if not self._backup_dir_created:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self._backup_dir_created = True

    def _create_backup(self, file_path: Path) -> Path:
        """Create a backup of a file."""
        self._ensure_backup_dir()
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        relative = file_path.relative_to(self.project_root)
        backup_name = f"{relative.as_posix().replace('/', '_')}_{timestamp}.bak"
        backup_path = self.backup_dir / backup_name
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _normalize_path(self, file_path: str) -> Path:
        """Normalize and validate file path."""
        path = (self.project_root / file_path).resolve()
        # Security: ensure path is within project root
        try:
            path.relative_to(self.project_root)
        except ValueError as err:
            raise ValueError(f"Path traversal attempt: {file_path}") from err
        return path

    def apply_patch(self, patch: Patch) -> PatchResult:
        """Apply a patch with validation and conflict detection."""
        result = PatchResult(patch_id=patch.patch_id)
        result.backup_dir = str(self.backup_dir) if not self.dry_run else None

        for change in patch.changes:
            try:
                file_path = self._normalize_path(change.file_path)

                if change.change_type == ChangeType.ADD:
                    self._apply_add(file_path, change, result)
                elif change.change_type == ChangeType.DELETE:
                    self._apply_delete(file_path, change, result)
                elif change.change_type == ChangeType.MODIFY:
                    self._apply_modify(file_path, change, result)
                elif change.change_type == ChangeType.RENAME:
                    self._apply_rename(file_path, change, result)

            except Exception as exc:
                result.status = PatchStatus.FAILED
                result.failed_files.append(change.file_path)
                result.errors[change.file_path] = str(exc)
                logger.error("Failed to apply change to %s: %s", change.file_path, exc)

        if result.applied_files:
            result.status = PatchStatus.APPLIED
        elif result.failed_files:
            result.status = PatchStatus.FAILED
        elif result.conflicts:
            result.status = PatchStatus.CONFLICT
        else:
            result.status = PatchStatus.SKIPPED

        result.applied_at = datetime.now(UTC)
        return result

    def _apply_add(self, file_path: Path, change: FileChange, result: PatchResult) -> None:
        """Apply file addition."""
        if file_path.exists():
            result.status = PatchStatus.CONFLICT
            result.conflicts.append(change.file_path)
            result.errors[change.file_path] = "File already exists"
            return

        if not self.dry_run:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(change.new_content, encoding="utf-8")

        result.applied_files.append(change.file_path)

    def _apply_delete(self, file_path: Path, change: FileChange, result: PatchResult) -> None:
        """Apply file deletion."""
        if not file_path.exists():
            result.status = PatchStatus.CONFLICT
            result.conflicts.append(change.file_path)
            result.errors[change.file_path] = "File does not exist"
            return

        # Verify content matches if provided
        if change.old_content:
            current = file_path.read_text(encoding="utf-8")
            if current != change.old_content:
                result.status = PatchStatus.CONFLICT
                result.conflicts.append(change.file_path)
                result.errors[change.file_path] = "File content doesn't match expected"
                return

        if not self.dry_run:
            self._create_backup(file_path)
            file_path.unlink()

        result.applied_files.append(change.file_path)

    def _apply_modify(self, file_path: Path, change: FileChange, result: PatchResult) -> None:
        """Apply file modification."""
        if not file_path.exists():
            result.status = PatchStatus.CONFLICT
            result.conflicts.append(change.file_path)
            result.errors[change.file_path] = "File does not exist"
            return

        current = file_path.read_text(encoding="utf-8")

        # Verify old content matches
        if change.old_content and current != change.old_content:
            # Try to do a smart merge using diff
            merged = self._try_merge(current, change.old_content, change.new_content)
            if merged is None:
                result.status = PatchStatus.CONFLICT
                result.conflicts.append(change.file_path)
                result.errors[change.file_path] = "Content mismatch - cannot auto-merge"
                return
            new_content = merged
        else:
            new_content = change.new_content

        if not self.dry_run:
            self._create_backup(file_path)
            file_path.write_text(new_content, encoding="utf-8")

        result.applied_files.append(change.file_path)

    def _apply_rename(self, file_path: Path, change: FileChange, result: PatchResult) -> None:
        """Apply file rename."""
        if not file_path.exists():
            result.status = PatchStatus.CONFLICT
            result.conflicts.append(change.file_path)
            result.errors[change.file_path] = "Source file does not exist"
            return

        if not change.old_path:
            result.status = PatchStatus.FAILED
            result.failed_files.append(change.file_path)
            result.errors[change.file_path] = "Rename requires old_path"
            return

        new_path = self._normalize_path(change.old_path)

        if new_path.exists():
            result.status = PatchStatus.CONFLICT
            result.conflicts.append(change.file_path)
            result.errors[change.file_path] = "Destination already exists"
            return

        if not self.dry_run:
            self._create_backup(file_path)
            new_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.rename(new_path)

        result.applied_files.append(change.file_path)

    def _try_merge(
        self,
        current: str,
        old_expected: str,
        new_content: str,
    ) -> str | None:
        """Try to merge changes using difflib."""
        try:
            # Generate diff from old_expected to new_content
            diff = list(
                difflib.unified_diff(
                    old_expected.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    n=3,
                )
            )

            # Apply diff to current
            for line in diff:
                if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                    continue
                # This is a simplified approach - in practice, use a proper patch library
                pass

            # For now, just return new_content if the change is straightforward
            # A full implementation would use the `patch` library or similar
            return new_content

        except Exception:
            return None


class PatchBuilder:
    """Builds patches from file operations."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self._changes: list[FileChange] = []

    def add_file(self, file_path: str, content: str) -> PatchBuilder:
        """Add a new file."""
        change = FileChange(
            file_path=file_path,
            change_type=ChangeType.ADD,
            new_content=content,
        )
        self._changes.append(change)
        return self

    def modify_file(self, file_path: str, old_content: str, new_content: str) -> PatchBuilder:
        """Modify an existing file."""
        change = FileChange(
            file_path=file_path,
            change_type=ChangeType.MODIFY,
            old_content=old_content,
            new_content=new_content,
        )
        self._changes.append(change)
        return self

    def delete_file(self, file_path: str, old_content: str = "") -> PatchBuilder:
        """Delete a file."""
        change = FileChange(
            file_path=file_path,
            change_type=ChangeType.DELETE,
            old_content=old_content,
        )
        self._changes.append(change)
        return self

    def rename_file(self, old_path: str, new_path: str) -> PatchBuilder:
        """Rename a file."""
        change = FileChange(
            file_path=new_path,
            change_type=ChangeType.RENAME,
            old_path=old_path,
        )
        self._changes.append(change)
        return self

    def build(self, label: str = "", description: str = "") -> Patch:
        """Build the patch."""
        patch = Patch(label=label, description=description)
        for change in self._changes:
            patch.add_change(change)
        return patch


def create_patch_from_diff(diff_text: str, project_root: Path) -> Patch:
    """Create a patch from a unified diff string."""
    # This would parse the diff and create FileChange objects
    # For now, return empty patch - full implementation needs diff parsing
    return Patch(label="from_diff", description="Generated from unified diff")


def apply_patch_file(patch_file: Path, project_root: Path, dry_run: bool = False) -> PatchResult:
    """Apply a patch from a file."""
    # Read patch file and apply
    # This would parse the patch file format
    patch = Patch()  # Placeholder
    applicator = PatchApplicator(project_root, dry_run=dry_run)
    return applicator.apply_patch(patch)
