#!/usr/bin/env python3
"""Verify external gate readiness and generate operator checklist.

This script does NOT fabricate external evidence. It only reports what is
still missing from the operator/broker/legal/platform side and validates
that internal prerequisites are met.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


REQUIRED_FILES = [
    "docs/templates/PRODUCTION-READINESS-EVIDENCE.md",
    "docs/templates/UAT-EVIDENCE.md",
    "docs/DR-RUNBOOK.md",
    "docs/OPERATOR-HANDOFF.md",
    "docs/UAT-CERTIFICATION.md",
    "docs/PRODUCTION-READINESS.md",
]


@dataclass
class Gate:
    name: str
    owner: str
    internal_prerequisites: list[str] = field(default_factory=list)
    evidence_artifact: str = ""
    blocking: bool = True


GATES = [
    Gate(
        name="Binance testnet connectivity",
        owner="Operator",
        evidence_artifact="secrets/testnet-binance-api-key.txt",
        blocking=False,
        internal_prerequisites=[
            "CCXT sandbox mode enabled",
            "Testnet API key/secret present in secrets/ or /run/secrets",
            "Binance testnet endpoint reachable",
        ],
    ),
    Gate(
        name="TFEX broker UAT certification",
        owner="Operator + broker",
        evidence_artifact="docs/templates/UAT-EVIDENCE.md",
        blocking=True,
        internal_prerequisites=[
            "Settrade v2 SDK installed",
            "Sandbox credentials loaded",
            "UAT account available",
        ],
    ),
    Gate(
        name="Production alert/RPO/RTO restore evidence",
        owner="Operator",
        evidence_artifact="docs/templates/PRODUCTION-READINESS-EVIDENCE.md",
        blocking=True,
        internal_prerequisites=[
            "Prometheus + alert delivery configured",
            "Backup/restore scripts tested",
            "Monitoring pipeline operational",
        ],
    ),
    Gate(
        name="GitHub protected environments/rulesets/merge queue",
        owner="GitHub admin",
        evidence_artifact="docs/GITHUB-ENVIRONMENTS.md",
        blocking=False,
        internal_prerequisites=[
            "CodeQL enabled",
            "Dependency Review enabled",
            "Secret Protection enabled",
        ],
    ),
    Gate(
        name="Broker/legal/TLS/secrets/monitoring/backup authorization",
        owner="Operator + legal",
        evidence_artifact="docs/templates/PRODUCTION-READINESS-EVIDENCE.md",
        blocking=True,
        internal_prerequisites=[
            "TLS certificate chain valid",
            "Secrets rotation schedule tested",
            "Backup/restore drill completed",
        ],
    ),
    Gate(
        name="Manual live canary plan",
        owner="Operator",
        evidence_artifact="docs/PRODUCTION-READINESS.md",
        blocking=True,
        internal_prerequisites=[
            "Four-eyes approval flow tested",
            "Kill switch operational",
            "Reconciliation converges",
        ],
    ),
]


def check_files_exist() -> list[str]:
    missing = []
    for path in REQUIRED_FILES:
        if not Path(path).exists():
            missing.append(path)
    return missing


def check_binance_testnet_credentials() -> tuple[bool, str]:
    import os

    api_key = os.getenv("ZKSATO_CCXT_BINANCE_TESTNET_API_KEY") or os.getenv(
        "ZKSATO_CCXT_BINANCE_API_KEY"
    )
    api_secret = os.getenv("ZKSATO_CCXT_BINANCE_TESTNET_API_SECRET") or os.getenv(
        "ZKSATO_CCXT_BINANCE_SECRET"
    )

    if not api_key or not api_secret:
        secrets_dir = Path(os.getenv("ZKSATO_SECRET_DIR", "secrets"))
        key_file = secrets_dir / "testnet-binance-api-key.txt"
        secret_file = secrets_dir / "testnet-binance-api-secret.txt"
        if key_file.exists() and secret_file.exists():
            api_key = key_file.read_text(encoding="utf-8").strip()
            api_secret = secret_file.read_text(encoding="utf-8").strip()

    if api_key and api_secret:
        return True, "present"
    return False, "missing"


def _extract_runtime_version(text: str) -> str | None:
    for line in text.splitlines():
        if "__version__ =" not in line:
            continue
        value = line.split("=", 1)[1].strip()
        if value.startswith('"') and value.endswith('"'):
            return value.strip('"')
        if value.startswith("'") and value.endswith("'"):
            return value.strip("'")
        if "version(" in value:
            # __version__ = version("zksato")
            try:
                from importlib.metadata import version as pkg_version

                return pkg_version("zksato")
            except Exception:
                return None
    return None


def _runtime_version() -> str | None:
    try:
        venv_python = _venv_python()
        import subprocess

        result = subprocess.run(
            [venv_python, "-c", "from importlib.metadata import version; print(version('zksato'))"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _venv_python() -> str:
    venv = Path(".venv/bin/python")
    if venv.exists():
        return str(venv)
    return sys.executable


def check_version_sync() -> tuple[bool, str, str]:
    try:
        with Path("pyproject.toml").open("rb") as handle:
            project_version = tomllib.load(handle)["project"]["version"]
    except Exception as exc:
        return False, "", f"pyproject.toml unreadable: {exc}"

    runtime_version = _runtime_version()
    if runtime_version is None:
        runtime_version = _extract_runtime_version(Path("src/zksato/__init__.py").read_text(encoding="utf-8"))
    if runtime_version is None:
        return False, project_version, "not found"
    return project_version == runtime_version, project_version, runtime_version


def check_tests_pass() -> bool:
    import subprocess

    result = subprocess.run(
        [_venv_python(), "-m", "pytest", "-m", "not uat and not performance", "-q"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )
    return result.returncode == 0


def main() -> int:
    root = Path.cwd()
    print(f"External gate readiness check\nRoot: {root}\n")

    # Check internal prerequisites
    missing_files = check_files_exist()
    version_ok, project_ver, runtime_ver = check_version_sync()
    tests_ok = check_tests_pass()
    binance_testnet_ok, binance_testnet_status = check_binance_testnet_credentials()

    print("Internal prerequisites")
    print(f"  Documentation files: {'OK' if not missing_files else 'MISSING'}")
    if missing_files:
        for path in missing_files:
            print(f"    - {path}")
    print(f"  Version sync (pyproject={project_ver}, runtime={runtime_ver}): {'OK' if version_ok else 'MISMATCH'}")
    print(f"  Tests passing: {'OK' if tests_ok else 'FAILED'}")
    print(f"  Binance testnet credentials: {'OK' if binance_testnet_ok else 'MISSING'} ({binance_testnet_status})")

    if missing_files or not version_ok or not tests_ok:
        print("\nFix internal prerequisites before requesting external evidence.")
        return 1

    print("\nExternal gates (operator action required)")
    for gate in GATES:
        status = "BLOCKING" if gate.blocking else "non-blocking"
        print(f"\n  [{status}] {gate.name}")
        print(f"    Owner: {gate.owner}")
        print(f"    Evidence artifact: {gate.evidence_artifact}")
        print(f"    Internal prerequisites:")
        for prereq in gate.internal_prerequisites:
            print(f"      - {prereq} [operator must verify]")

    print("\nNext steps for operator:")
    print("  1. Open docs/OPERATOR-HANDOFF.md")
    print("  2. Execute actions in order")
    print("  3. Archive evidence in the referenced templates")
    print("  4. Re-run this script after each gate is completed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
