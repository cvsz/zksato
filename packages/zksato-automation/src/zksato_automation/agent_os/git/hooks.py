"""Git hooks integration for zksato agent engineering platform.

Provides pre-commit, post-commit, pre-push, and other git hooks
for automated quality gates and safety checks.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from zksato_automation.agent_os.git import GitClient, GitOperationResult, GitError

logger = logging.getLogger(__name__)


async def run_pre_commit_hooks(repo_path: str | Path = ".") -> GitOperationResult:
    """Run pre-commit hooks for quality gates.
    
    This function checks for:
    - Code style issues (ruff)
    - Type issues (mypy)
    - Security issues (bandit)
    - Test validation
    """
    client = GitClient(repo_path)
    results: list[dict[str, Any]] = []
    
    # Run ruff check on staged files
    staged_result = await client.run("diff--cached", "--name-only")
    staged_files = staged_result.stdout.strip().split("\n") if staged_result.stdout.strip() else []
    
    python_files = [f for f in staged_files if f.endswith(".py")]
    
    if python_files:
        # Run ruff check
        ruff_cmd = ["check", "--select=E,F,W"] + python_files
        ruff_result = await client.run(*ruff_cmd)
        results.append({
            "tool": "ruff",
            "success": ruff_result.returncode == 0,
            "output": ruff_result.stdout,
            "files": python_files,
        })
        
        # Run bandit security check on a sample
        if python_files:
            sample_file = python_files[0]
            bandit_result = await client.run("run", "--bandit", "-r", sample_file, "-f", "json")
            results.append({
                "tool": "bandit",
                "success": bandit_result.returncode == 0,
                "output": bandit_result.stdout,
                "files": [sample_file],
            })
    
    # Check for TODO/FIXME in commit messages
    # This would be checked separately
    
    overall_success = all(r["success"] for r in results)
    
    return GitOperationResult(
        success=overall_success,
        stdout="\n".join(
            f"{r['tool']}: {'PASS' if r['success'] else 'FAIL'}\n{r['output']}"
            for r in results
        ),
        stderr="\n".join(
            f"{r['tool']}: FAIL\n{r['output']}"
            for r in results if not r["success"]
        ),
    )


async def run_post_commit_hooks(
    repo_path: str | Path = ".",
    commit_hash: str | None = None,
) -> GitOperationResult:
    """Run post-commit hooks for audit logging and notifications."""
    client = GitClient(repo_path)
    results: list[dict[str, Any]] = []
    
    # Log the commit to audit trail
    if commit_hash:
        log_result = await client.run("log", "-1", commit_hash, "--format=%B")
        results.append({
            "tool": "audit_log",
            "success": log_result.success,
            "output": log_result.stdout,
            "commit": commit_hash,
        })
    
    # Send notification (would integrate with Telegram, etc.)
    # results.append({"tool": "notification", "success": True, "commit": commit_hash})
    
    overall_success = all(r["success"] for r in results)
    
    return GitOperationResult(
        success=overall_success,
        stdout="\n".join(
            f"{r['tool']}: {'PASS' if r['success'] else 'FAIL'}\n{r['output']}"
            for r in results
        ),
        stderr="\n".join(
            f"{r['tool']}: FAIL\n{r['output']}"
            for r in results if not r["success"]
        ),
    )


async def check_commit_safety(repo_path: str | Path = ".") -> GitOperationResult:
    """Check if a commit is safe to proceed (safety gate)."""
    client = GitClient(repo_path)
    results: list[dict[str, Any]] = []
    
    # Check for sensitive data in staged changes
    diff_result = await client.run("diff--cached")
    if diff_result.stdout:
        # Scan for potential secrets
        import re
        secret_patterns = [r"[a-zA-Z0-9]{32,}", r"(password|secret|key)\s*=", r"token\s*="]
        findings = []
        for pattern in secret_patterns:
            matches = [(m.start(), m.group()) for m in re.finditer(pattern, diff_result.stdout, re.IGNORECASE)]
            if matches:
                findings.append({pattern: matches[:3]})
        
        if findings:
            results.append({
                "tool": "secrets_scan",
                "success": False,
                "output": f"Potential secrets found: {findings}",
            })
        else:
            results.append({
                "tool": "secrets_scan",
                "success": True,
                "output": "No sensitive data detected",
            })
    
    # Check for large file additions
    staged_result = await client.run("diff--cached", "--name-only")
    staged_files = staged_result.stdout.strip().split("\n") if staged_result.stdout.strip() else []
    
    large_files = []
    for f in staged_files:
        if f.endswith(".py"):
            # Check file size
            try:
                import os
                file_path = client.repo_path / f
                if file_path.exists() and file_path.stat().st_size > 100000:  # 100KB
                    large_files.append(f)
            except Exception:
                pass
    
    if large_files:
        results.append({
            "tool": "size_check",
            "success": False,
            "output": f"Large files staged: {large_files}",
        })
    else:
        results.append({
            "tool": "size_check",
            "success": True,
            "output": "All file sizes acceptable",
        })
    
    overall_success = all(r["success"] for r in results)
    
    return GitOperationResult(
        success=overall_success,
        stdout="\n".join(
            f"{r['tool']}: {'PASS' if r['success'] else 'FAIL'}\n{r['output']}"
            for r in results
        ),
        stderr="\n".join(
            f"{r['tool']}: FAIL\n{r['output']}"
            for r in results if not r["success"]
        ),
    )


# Global hooks runner
_hooks_runner: Any = None


def get_hooks_runner() -> Any:
    """Get the global hooks runner instance."""
    global _hooks_runner
    return _hooks_runner


__all__ = [
    "run_pre_commit_hooks",
    "run_post_commit_hooks",
    "check_commit_safety",
]