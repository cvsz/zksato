"""Git integration for zksato agent engineering platform.

Provides git operations, worktree management, change tracking, and hooks
for multi-agent coordination and automated workflows.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GitError(RuntimeError):
    """Raised when a git operation fails."""

    pass


class GitOperationResult:
    """Result of a git operation."""

    def __init__(
        self,
        success: bool,
        stdout: str = "",
        stderr: str = "",
        returncode: int = -1,
        error: str | None = None,
    ) -> None:
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.error = error

    def __bool__(self) -> bool:
        return self.success

    def __repr__(self) -> str:
        return f"GitOperationResult(success={self.success}, returncode={self.returncode})"


class GitClient:
    """Client for executing git operations."""

    def __init__(self, repo_path: str | Path = ".") -> None:
        self.repo_path = Path(repo_path).resolve()

    async def run(
        self,
        *args: str,
        timeout: float = 30.0,
    ) -> GitOperationResult:
        """Run a git command and return the result."""
        cmd = ["git", *args]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return GitOperationResult(
                success=proc.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                returncode=proc.returncode,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return GitOperationResult(
                success=False,
                stderr="Command timed out",
                returncode=-1,
                error="Command timed out",
            )
        except Exception as exc:
            return GitOperationResult(
                success=False,
                stderr=str(exc),
                returncode=-1,
                error=str(exc),
            )

    def sync_run(
        self,
        *args: str,
        timeout: float = 30.0,
    ) -> GitOperationResult:
        """Synchronously run a git command."""
        cmd = ["git", *args]
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return GitOperationResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return GitOperationResult(
                success=False,
                stderr="Command timed out",
                returncode=-1,
                error="Command timed out",
            )
        except Exception as exc:
            return GitOperationResult(
                success=False,
                stderr=str(exc),
                returncode=-1,
                error=str(exc),
            )

    async def get_status(self) -> dict[str, Any]:
        """Get repository status."""
        result = await self.run("status", "--porcelain")
        return {
            "head": (await self.run("rev-parse", "HEAD")).stdout.strip()
            if (await self.run("rev-parse", "HEAD")).success
            else None,
            "branch": (await self.run("rev-parse", "--abbrev-ref", "HEAD")).stdout.strip()
            if (await self.run("rev-parse", "--abbrev-ref", "HEAD")).success
            else None,
            "modified": result.stdout.strip().split("\n")
            if result.stdout.strip()
            else [],
            "is_dirty": result.returncode == 0 and bool(result.stdout.strip()),
        }

    async def get_log(
        self,
        max_count: int = 50,
        since: str | None = None,
    ) -> GitOperationResult:
        """Get git log entries."""
        cmd = ["log", f"--max-count={max_count}", "--format=%H|%an|%ae|%ad|%s"]
        if since:
            cmd.insert(1, f"--since={since}")
        result = await self.run(*cmd)
        if result.success and result.stdout:
            entries = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 4)
                    entries.append(
                        {
                            "commit": parts[0],
                            "author": parts[1],
                            "email": parts[2],
                            "date": parts[3],
                            "subject": parts[4],
                        }
                    )
            result._entries = entries  # type: ignore[attr-defined]
        return result

    async def get_diff(self) -> GitOperationResult:
        """Get working tree diff."""
        return await self.run("diff")

    async def get_diff_staged(self) -> GitOperationResult:
        """Get staged diff."""
        return await self.run("diff--cached")

    async def commit(
        self,
        message: str,
        author: str | None = None,
        no_verify: bool = False,
    ) -> GitOperationResult:
        """Commit changes."""
        cmd = ["commit", "-m", message]
        if author:
            cmd.extend(["--author", author])
        if no_verify:
            cmd.append("--no-verify")
        return await self.run(*cmd)

    async def add(self, paths: list[str] | None = None) -> GitOperationResult:
        """Add files to staging area."""
        cmd = ["add"]
        if paths:
            cmd.extend(paths)
        return await self.run(*cmd)

    async def branch(self, name: str, create: bool = False) -> GitOperationResult:
        """Create or switch branch."""
        cmd = ["branch"]
        if create:
            cmd.append("-c")
        cmd.append(name)
        return await self.run(*cmd)

    async def checkout(self, ref: str) -> GitOperationResult:
        """Checkout a reference."""
        return await self.run("checkout", ref)

    async def tag(self, name: str, message: str | None = None) -> GitOperationResult:
        """Create a tag."""
        cmd = ["tag", name]
        if message:
            cmd.extend(["-m", message])
        return await self.run(*cmd)

    async def remote(
        self,
        operation: str,
        name: str | None = None,
        url: str | None = None,
    ) -> GitOperationResult:
        """Remote operations (add, remove, rename)."""
        cmd = ["remote", operation]
        if name:
            cmd.append(name)
        if url:
            cmd.append(url)
        return await self.run(*cmd)

    async def worktree(
        self,
        action: str,
        name: str,
        create: bool = False,
        checkout: bool = True,
    ) -> GitOperationResult:
        """Worktree management.
        
        Supported actions:
        - "add <path>": Create a new worktree at <path>
        - "list": List worktrees
        - "remove <path>": Remove a worktree
        - "lock <path>": Lock a worktree
        - "unlock <path>": Unlock a worktree
        """
        if action == "add":
            if create:
                # git worktree add [--detach] [--checkout] <path> [<commit-ish>]
                cmd = ["worktree", "add"]
                if not checkout:
                    cmd.append("--no-checkout")
                cmd.append(name)
                if checkout:
                    cmd.append("main")  # default branch
            else:
                cmd = ["worktree", "list"]
        elif action == "remove":
            cmd = ["worktree", "remove", name]
        elif action == "list":
            cmd = ["worktree", "list"]
        else:
            cmd = ["worktree", action, name]
        
        return await self.run(*cmd)

    async def list_worktrees(self) -> GitOperationResult:
        """List all worktrees."""
        return await self.run("worktree", "list--porcelain")

    async def get_change_tracking_state(self) -> dict[str, Any]:
        """Get change tracking state for the repository."""
        # Get current HEAD
        head_result = await self.run("rev-parse", "HEAD")
        # Get staged changes
        staged_result = await self.run("diff--cached", "--name-only")
        # Get unstaged changes
        unstaged_result = await self.run("diff", "--name-only")
        # Get untracked files
        untracked_result = await self.run("ls-files", "--others", "--exclude-standard")

        return {
            "head": head_result.stdout.strip() if head_result.success else None,
            "staged_files": staged_result.stdout.strip().split("\n")
            if staged_result.stdout.strip()
            else [],
            "unstaged_files": unstaged_result.stdout.strip().split("\n")
            if unstaged_result.stdout.strip()
            else [],
            "untracked_files": untracked_result.stdout.strip().split("\n")
            if untracked_result.stdout.strip()
            else [],
            "timestamp": datetime.now(UTC).isoformat(),
        }


class WorktreeManager:
    """Manages git worktrees for agent isolation."""

    def __init__(self, repo_path: str | Path = ".") -> None:
        self.client = GitClient(repo_path)

    async def create_worktree(
        self,
        name: str,
        base: str = "main",
        checkout: bool = True,
    ) -> GitOperationResult:
        """Create a new worktree for agent isolation."""
        return await self.client.worktree("add", name, create=True, checkout=checkout)

    async def switch_worktree(self, name: str) -> GitOperationResult:
        """Switch to a worktree."""
        return await client.checkout(name)

    async def list_worktrees(self) -> GitOperationResult:
        """List all worktrees."""
        return await self.client.list_worktrees()

    async def remove_worktree(self, name: str, force: bool = False) -> GitOperationResult:
        """Remove a worktree."""
        cmd = ["worktree", "remove"]
        if force:
            cmd.append("--force")
        cmd.append(name)
        return await self.client.run(*cmd)


# Global client instance
_client: GitClient | None = None
_worktree_manager: WorktreeManager | None = None


def get_client(repo_path: str | Path | None = None) -> GitClient:
    """Get or create a GitClient instance."""
    global _client
    if _client is None or (repo_path is not None and _client.repo_path != Path(repo_path).resolve()):
        _client = GitClient(repo_path)
    return _client


def get_worktree_manager(repo_path: str | Path | None = None) -> WorktreeManager:
    """Get or create a WorktreeManager instance."""
    global _worktree_manager
    if _worktree_manager is None or (repo_path is not None and _worktree_manager.client.repo_path != Path(repo_path).resolve()):
        _worktree_manager = WorktreeManager(repo_path)
    return _worktree_manager


async def init() -> GitClient:
    """Initialize the git client for the zksato repository."""
    return get_client()


async def get_state() -> dict[str, Any]:
    """Get current git state."""
    client = get_client()
    return await client.get_change_tracking_state()


# Export main classes
__all__ = [
    "GitError",
    "GitOperationResult",
    "GitClient",
    "WorktreeManager",
    "init",
    "get_state",
]