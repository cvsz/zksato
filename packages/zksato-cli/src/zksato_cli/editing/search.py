"""Search and grep tools for ZKSATO coding agent.

Provides ripgrep-based code search, symbol references, and diagnostics.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""

    file_path: str
    line_number: int
    line: str
    match_start: int
    match_end: int
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)


@dataclass
class SearchResults:
    """Collection of search results."""

    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_matches: int = 0
    files_with_matches: int = 0
    elapsed_ms: float = 0.0
    truncated: bool = False


class RipgrepSearcher:
    """Fast code search using ripgrep."""

    def __init__(
        self,
        project_root: Path,
        rg_path: str = "rg",
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.rg_path = rg_path
        self._check_rg()

    def _check_rg(self) -> None:
        """Check if ripgrep is available."""
        try:
            subprocess.run(
                [self.rg_path, "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as err:
            raise RuntimeError("ripgrep (rg) not found. Please install ripgrep.") from err

    def search(
        self,
        pattern: str,
        *,
        file_pattern: str | None = None,
        case_sensitive: bool = False,
        whole_word: bool = False,
        regex: bool = True,
        max_results: int = 1000,
        context_lines: int = 2,
        include_hidden: bool = False,
        max_filesize: str = "10M",
    ) -> SearchResults:
        """Search for pattern in project files."""
        import time

        start = time.time()

        args = [self.rg_path]

        # Output format
        args.extend(["--json", "--with-filename", "--line-number", "--column"])

        # Pattern options
        if not regex:
            args.append("--fixed-strings")
        if case_sensitive:
            args.append("--case-sensitive")
        else:
            args.append("--ignore-case")
        if whole_word:
            args.append("--word-regexp")

        # Context
        if context_lines > 0:
            args.extend(["--context", str(context_lines)])

        # Limits
        args.extend(["--max-count", str(max_results)])
        args.extend(["--max-filesize", max_filesize])

        # File filtering
        if file_pattern:
            args.extend(["--glob", file_pattern])

        if include_hidden:
            args.append("--hidden")

        # Exclude patterns
        args.extend(
            [
                "--glob",
                "!.git/**",
                "--glob",
                "!__pycache__/**",
                "--glob",
                "!.venv/**",
                "--glob",
                "!venv/**",
                "--glob",
                "!node_modules/**",
                "--glob",
                "!target/**",
                "--glob",
                "!.pytest_cache/**",
                "--glob",
                "!dist/**",
                "--glob",
                "!build/**",
            ]
        )

        args.extend([pattern, str(self.project_root)])

        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Ripgrep search timed out")
            return SearchResults(
                query=pattern,
                elapsed_ms=(time.time() - start) * 1000,
                truncated=True,
            )

        results = SearchResults(query=pattern)
        files_seen = set()

        for line in proc.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                import json

                data = json.loads(line)

                if data.get("type") == "match":
                    match_data = data["data"]
                    file_path = match_data["path"]["text"]
                    line_number = match_data["line_number"]
                    line_text = match_data["lines"]["text"]
                    match = match_data.get("match", {})

                    # Get absolute path
                    abs_path = Path(file_path).resolve()
                    try:
                        rel_path = abs_path.relative_to(self.project_root)
                    except ValueError:
                        rel_path = Path(file_path)

                    match_start = match.get("start", 0)
                    match_end = match.get("end", 0)

                    # Extract context
                    context = match_data.get("context", [])
                    context_before = [
                        c["text"] for c in context if c.get("line_number", 0) < line_number
                    ]
                    context_after = [
                        c["text"] for c in context if c.get("line_number", 0) > line_number
                    ]

                    result = SearchResult(
                        file_path=str(rel_path),
                        line_number=line_number,
                        line=line_text.rstrip("\n"),
                        match_start=match_start,
                        match_end=match_end,
                        context_before=context_before[-context_lines:],
                        context_after=context_after[:context_lines],
                    )
                    results.results.append(result)
                    files_seen.add(str(rel_path))

            except Exception as exc:
                logger.debug("Failed to parse rg output: %s", exc)
                continue

        results.total_matches = len(results.results)
        results.files_with_matches = len(files_seen)
        results.elapsed_ms = (time.time() - start) * 1000
        results.truncated = len(results.results) >= max_results

        return results

    def search_symbol(
        self,
        symbol: str,
        *,
        language: str | None = None,
        kind: str | None = None,
    ) -> SearchResults:
        """Search for a symbol definition or reference."""
        # Build pattern for symbol
        patterns = [
            rf"\bdef\s+{re.escape(symbol)}\b",  # Python function
            rf"\bclass\s+{re.escape(symbol)}\b",  # Python class
            rf"\bfn\s+{re.escape(symbol)}\b",  # Rust function
            rf"\bfunction\s+{re.escape(symbol)}\b",  # JS function
            rf"\bconst\s+{re.escape(symbol)}\b",  # JS const
            rf"\blet\s+{re.escape(symbol)}\b",  # JS let
            rf"\bvar\s+{re.escape(symbol)}\b",  # JS var
            rf"type\s+{re.escape(symbol)}\b",  # Go/TypeScript type
            rf"interface\s+{re.escape(symbol)}\b",  # TS interface
        ]
        pattern = "|".join(patterns)

        file_pattern = None
        if language:
            ext_map = {
                "python": "*.py",
                "rust": "*.rs",
                "javascript": "*.js",
                "typescript": "*.ts",
                "go": "*.go",
                "java": "*.java",
            }
            file_pattern = ext_map.get(language.lower())

        return self.search(pattern, file_pattern=file_pattern, regex=True)


class PythonSymbolIndexer:
    """Python-specific symbol indexing using AST."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()

    def find_definitions(self, symbol: str) -> list[SearchResult]:
        """Find symbol definitions in Python files."""
        import ast

        results = []

        for py_file in self.project_root.rglob("*.py"):
            if any(part.startswith(".") for part in py_file.parts):
                continue
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    name = None
                    line_no = 0

                    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                        name = node.name
                        line_no = node.lineno

                    if name == symbol:
                        lines = content.splitlines()
                        line_text = lines[line_no - 1] if line_no <= len(lines) else ""

                        results.append(
                            SearchResult(
                                file_path=str(py_file.relative_to(self.project_root)),
                                line_number=line_no,
                                line=line_text.strip(),
                                match_start=line_text.find(symbol),
                                match_end=line_text.find(symbol) + len(symbol),
                            )
                        )

            except Exception as exc:
                logger.debug("Failed to parse %s: %s", py_file, exc)

        return results

    def find_references(self, symbol: str) -> list[SearchResult]:
        """Find symbol references in Python files."""
        # This would require more sophisticated analysis
        # For now, fall back to text search
        return []


class SymbolSearcher:
    """Multi-language symbol searcher."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.rg = RipgrepSearcher(project_root)
        self.python_indexer = PythonSymbolIndexer(project_root)

    def find_definition(self, symbol: str, language: str | None = None) -> SearchResults:
        """Find symbol definition."""
        if language == "python":
            defs = self.python_indexer.find_definitions(symbol)
            return SearchResults(query=symbol, results=defs)
        else:
            return self.rg.search_symbol(symbol, language=language)

    def find_references(self, symbol: str, language: str | None = None) -> SearchResults:
        """Find symbol references."""
        # For now, use text search
        return self.rg.search(rf"\b{re.escape(symbol)}\b", regex=True)


class DiagnosticCollector:
    """Collects diagnostics (errors, warnings) from various sources."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()

    def run_python_diagnostics(self) -> list[dict[str, Any]]:
        """Run Python diagnostics using pyright/mypy/ruff."""
        diagnostics = []

        # Try ruff
        try:
            proc = subprocess.run(
                ["ruff", "check", "--output-format=json", str(self.project_root)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.stdout:
                import json

                diagnostics.extend(
                    {
                        "file": issue.get("filename", ""),
                        "line": issue.get("location", {}).get("row", 0),
                        "column": issue.get("location", {}).get("column", 0),
                        "message": issue.get("message", ""),
                        "code": issue.get("code", ""),
                        "severity": "error"
                        if "error" in issue.get("code", "").lower()
                        else "warning",
                        "source": "ruff",
                    }
                    for issue in json.loads(proc.stdout)
                )
        except Exception as exc:
            logger.debug("Ruff diagnostics failed: %s", exc)

        # Try mypy
        try:
            proc = subprocess.run(
                ["mypy", "--output=json", str(self.project_root)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.stdout:
                import json

                diagnostics.extend(
                    {
                        "file": issue.get("file", ""),
                        "line": issue.get("line", 0),
                        "column": issue.get("column", 0),
                        "message": issue.get("message", ""),
                        "code": issue.get("code", ""),
                        "severity": "error" if issue.get("severity") == "error" else "warning",
                        "source": "mypy",
                    }
                    for issue in json.loads(proc.stdout)
                )
        except Exception as exc:
            logger.debug("Mypy diagnostics failed: %s", exc)

        return diagnostics

    def run_typescript_diagnostics(self) -> list[dict[str, Any]]:
        """Run TypeScript diagnostics using tsc."""
        diagnostics = []
        try:
            proc = subprocess.run(
                ["npx", "tsc", "--noEmit", "--pretty", "false"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            # Parse tsc output
            for line in proc.stdout.splitlines():
                if ":" in line and ("error" in line or "warning" in line):
                    # Simplified parsing
                    pass
        except Exception as exc:
            logger.debug("TSC diagnostics failed: %s", exc)
        return diagnostics

    def collect_all(self) -> list[dict[str, Any]]:
        """Collect all diagnostics."""
        all_diagnostics = []
        all_diagnostics.extend(self.run_python_diagnostics())
        all_diagnostics.extend(self.run_typescript_diagnostics())
        return all_diagnostics
