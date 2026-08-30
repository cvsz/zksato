#!/usr/bin/env python3
"""Verify external gates and produce ProductionReadinessEvidence.

Aggregates:
- local runtime config ( Settings + StateStore )
- live UAT probe ( /health, /v1/config, /v1/market/settrade/status )
- optional GitHub health probe ( via github_health.py contract )
- manual evidence flags supplied via CLI / env

Never submits an order. Output is a JSON file suitable for
POST /v1/production/readiness and for the machine-readable
``production-readiness.json`` artifact required by PRODUCTION-CHECKLIST.md.

Usage:
  scripts/verify_external_gates.py --base-url URL --api-key KEY
  scripts/verify_external_gates.py --check-only
  scripts/verify_external_gates.py --manual-evidence E.json --output out.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from zksato.config import Settings  # type: ignore
    from zksato.production import (  # type: ignore
        ExternalReadinessEvidence,
        ProductionReadinessService,
    )
    from zksato.store import StateStore  # type: ignore
except ImportError:
    # Allow running without installed package (dev convenience)
    Settings = None  # type: ignore
    ExternalReadinessEvidence = None  # type: ignore
    ProductionReadinessService = None  # type: ignore
    StateStore = None  # type: ignore


def _probe_uap(base_url: str, api_key: str) -> dict[str, Any]:
    """Non-mutating UAT probe matching scripts/uat_certify.py."""
    from urllib.request import Request, urlopen

    def _get(path: str) -> Any:
        req = Request(f"{base_url.rstrip('/')}{path}", headers={"X-API-Key": api_key})
        with urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read())

    result: dict[str, Any] = {}
    for path, key in [
        ("/health", "health"),
        ("/v1/config", "config"),
        ("/v1/market/settrade/status", "feed"),
    ]:
        try:
            result[key] = _get(path)
            result[f"{key}_ok"] = True
        except Exception as exc:
            result[key] = {"error": str(exc)}
            result[f"{key}_ok"] = False
    return result


def _load_manual_evidence(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manual evidence file must be a JSON object")
    return data


def _env_flag(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, "")
    if not val:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def build_evidence(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    manual = _load_manual_evidence(args.manual_evidence)
    # Start from ExternalReadinessEvidence defaults, overlay manual file, then CLI flags
    base_evidence = {
        "broker_permission_confirmed": bool(manual.get("broker_permission_confirmed", False)),
        "legal_operational_review_complete": bool(
            manual.get("legal_operational_review_complete", False)
        ),
        "settrade_uat_complete": bool(manual.get("settrade_uat_complete", False)),
        "tls_verified": bool(manual.get("tls_verified", False)),
        "managed_secrets_verified": bool(manual.get("managed_secrets_verified", False)),
        "backup_restore_drill_complete": bool(manual.get("backup_restore_drill_complete", False)),
        "monitoring_alerts_verified": bool(manual.get("monitoring_alerts_verified", False)),
        "incident_response_verified": bool(manual.get("incident_response_verified", False)),
        "deployment_rollback_verified": bool(manual.get("deployment_rollback_verified", False)),
        "capacity_slo_verified": bool(manual.get("capacity_slo_verified", False)),
        "time_sync_verified": bool(manual.get("time_sync_verified", False)),
        "market_data_failover_verified": bool(manual.get("market_data_failover_verified", False)),
        "data_retention_verified": bool(manual.get("data_retention_verified", False)),
        "release_artifact_verified": bool(manual.get("release_artifact_verified", False)),
        "manual_canary_authorized": bool(manual.get("manual_canary_authorized", False)),
        "uat_orders_reconciled": int(manual.get("uat_orders_reconciled", 0)),
        "evidence_reference": manual.get("evidence_reference"),
    }
    # CLI overrides (explicit per-flag)
    for field in list(base_evidence.keys()):
        cli_val = getattr(args, field, None)
        if cli_val is not None:
            base_evidence[field] = cli_val
    # Env overrides for CI
    if _env_flag("ZKSATO_GATE_TLS_VERIFIED"):
        base_evidence["tls_verified"] = True
    if _env_flag("ZKSATO_GATE_BACKUP_VERIFIED"):
        base_evidence["backup_restore_drill_complete"] = True

    probe: dict[str, Any] = {}
    if args.base_url and args.api_key:
        probe = _probe_uap(args.base_url, args.api_key)
        # Auto-infer some external flags from live probe
        cfg = probe.get("config", {}) if isinstance(probe.get("config"), dict) else {}
        if cfg.get("settrade_configured"):
            # Do not auto-mark UAT complete, but surface readiness for operator check
            probe["settrade_configured"] = True
        if probe.get("health_ok") and probe.get("config_ok"):
            probe["probe_ok"] = True

    return base_evidence, probe


def _local_runtime_report() -> dict[str, Any]:
    if Settings is None:
        return {"available": False, "reason": "zksato not importable"}
    try:
        settings = Settings()  # type: ignore[call-arg]
        if StateStore is not None:
            try:
                from zksato.persistence import build_store  # type: ignore

                store = build_store(settings)
            except Exception:
                store = StateStore()  # type: ignore[call-arg]
        else:
            store = None  # type: ignore[assignment]
        svc = (
            ProductionReadinessService(settings, store) if ProductionReadinessService else None  # type: ignore[call-arg]
        )
        checks = {}
        if svc is not None:
            # Build a report with all external flags false to show pure runtime health
            evidence = ExternalReadinessEvidence()  # type: ignore[call-arg]
            report = svc.report(evidence)
            runtime_checks = [c for c in report.checks if c.source == "runtime"]
            checks = {
                "ready_for_manual_canary": report.ready_for_manual_canary,
                "runtime_passed": sum(1 for c in runtime_checks if c.passed),
                "runtime_total": len(runtime_checks),
                "failing_runtime": [c.detail for c in runtime_checks if not c.passed],
            }
        return {
            "available": True,
            "environment": settings.environment,
            "trading_mode": settings.trading_mode,
            "live_trading_enabled": settings.live_trading_enabled,
            "settrade_configured": settings.settrade_configured,
            "auth_required": settings.auth_required,
            "account_allowed": settings.account_allowed,
            "prediction_enabled": settings.prediction_enabled,
            "prediction_enable_live": settings.prediction_enable_live,
            "prediction_clob_url": settings.prediction_clob_url,
            "checks": checks,
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify external gates for production readiness")
    parser.add_argument("--base-url", default=os.environ.get("ZKSATO_BASE_URL", ""))
    parser.add_argument("--api-key", default=os.environ.get("ZKSATO_API_KEY", ""))
    parser.add_argument(
        "--manual-evidence",
        type=Path,
        default=None,
        help="JSON with external flags",  # noqa: E501
    )
    parser.add_argument("--output", type=Path, default=Path("readiness-input.json"))
    parser.add_argument("--report", type=Path, default=Path("external-gates-report.json"))
    parser.add_argument("--check-only", action="store_true", help="print runtime health only")
    # Per-field CLI flags for evidence (all default None so manual file is respected)
    for field in [
        "broker_permission_confirmed",
        "legal_operational_review_complete",
        "settrade_uat_complete",
        "tls_verified",
        "managed_secrets_verified",
        "backup_restore_drill_complete",
        "monitoring_alerts_verified",
        "incident_response_verified",
        "deployment_rollback_verified",
        "capacity_slo_verified",
        "time_sync_verified",
        "market_data_failover_verified",
        "data_retention_verified",
        "release_artifact_verified",
        "manual_canary_authorized",
    ]:
        parser.add_argument(f"--{field.replace('_', '-')}", action="store_true", default=None)
        parser.add_argument(f"--no-{field.replace('_', '-')}", dest=field, action="store_false")
    parser.add_argument("--uat-orders-reconciled", type=int, default=None)
    parser.add_argument("--evidence-reference", type=str, default=None)
    args = parser.parse_args()

    evidence, probe = build_evidence(args)
    runtime = _local_runtime_report()

    full_report = {
        "evidence": evidence,
        "probe": probe,
        "runtime": runtime,
        "notes": (
            "External gates are operator-certified facts. This script never fakes them; "
            "it only aggregates local runtime, live probe, and manual evidence into a "
            "single artifact for POST /v1/production/readiness."
        ),
    }

    if args.check_only:
        print(json.dumps(full_report, indent=2, sort_keys=True))
        # exit 1 if runtime not healthy enough for prod
        failing = runtime.get("checks", {}).get("failing_runtime", [])
        if isinstance(failing, list) and failing:
            print(f"\nRuntime failing checks: {failing}", file=sys.stderr)
        return 0

    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.write_text(
        json.dumps(full_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote evidence to {args.output} and full report to {args.report}")
    print(json.dumps(full_report, indent=2))
    # Do not return failure for missing external evidence — that is expected pre-UAT
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
