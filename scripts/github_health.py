from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.github.com"
CORE_WORKFLOWS = {"CI", "Governance", "Security", "Container"}
ENVIRONMENT_MANIFEST = Path(".github/environments/requirements.json")


def _get(path: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "zksato-repository-health",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {"available": True, "status": response.status, "data": payload}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        return {"available": False, "status": exc.code, "error": detail}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"available": False, "status": None, "error": str(exc)}


def _required_environments() -> set[str]:
    if not ENVIRONMENT_MANIFEST.exists():
        return set()
    payload = json.loads(ENVIRONMENT_MANIFEST.read_text(encoding="utf-8"))
    environments = payload.get("environments", {})
    if not isinstance(environments, dict):
        raise ValueError("GitHub environment manifest environments must be an object")
    return {str(name) for name in environments}


def build_report(repository: str, token: str) -> tuple[dict[str, Any], list[str]]:
    owner, repo = repository.split("/", 1)
    base = f"/repos/{owner}/{repo}"
    probes = {
        "repository": _get(base, token),
        "actions_permissions": _get(f"{base}/actions/permissions", token),
        "workflows": _get(f"{base}/actions/workflows?per_page=100", token),
        "environments": _get(f"{base}/environments", token),
        "main_protection": _get(f"{base}/branches/main/protection", token),
        "rulesets": _get(f"{base}/rulesets", token),
        "code_scanning": _get(f"{base}/code-scanning/alerts?per_page=1", token),
        "secret_scanning": _get(f"{base}/secret-scanning/alerts?per_page=1", token),
        "dependabot_alerts": _get(f"{base}/dependabot/alerts?per_page=1", token),
    }
    blocking: list[str] = []
    repo_probe = probes["repository"]
    if not repo_probe["available"]:
        blocking.append("repository metadata is not readable")
    else:
        data = repo_probe["data"]
        if data.get("default_branch") != "main":
            blocking.append("default branch is not main")
        if data.get("archived"):
            blocking.append("repository is archived")

    workflow_probe = probes["workflows"]
    active: set[str] = set()
    if workflow_probe["available"]:
        active = {
            item.get("name", "")
            for item in workflow_probe["data"].get("workflows", [])
            if item.get("state") == "active"
        }
        missing = sorted(CORE_WORKFLOWS - active)
        if missing:
            blocking.append(f"core workflows are not active: {', '.join(missing)}")
    else:
        blocking.append("workflow inventory is not readable")

    required_environments = _required_environments()
    observed_environments: set[str] = set()
    environment_probe = probes["environments"]
    if environment_probe["available"]:
        observed_environments = {
            str(item.get("name", ""))
            for item in environment_probe["data"].get("environments", [])
            if isinstance(item, dict)
        }
        missing_environments = sorted(required_environments - observed_environments)
        if missing_environments:
            blocking.append(
                "required GitHub environments are missing: " + ", ".join(missing_environments)
            )

    report = {
        "repository": repository,
        "source_controlled_checks": {
            "core_workflows_required": sorted(CORE_WORKFLOWS),
            "active_workflows": sorted(active),
            "required_environments": sorted(required_environments),
            "observed_environments": sorted(observed_environments),
            "blocking": blocking,
        },
        "capability_probes": probes,
    }
    return report, blocking


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit GitHub repository controls without mutating settings"
    )
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--output", default="repository-health.json")
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not args.repository or "/" not in args.repository:
        raise SystemExit("--repository or GITHUB_REPOSITORY is required")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")

    report, blocking = build_report(args.repository, token)
    Path(args.output).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["source_controlled_checks"], indent=2))
    for name, probe in report["capability_probes"].items():
        state = "available" if probe["available"] else f"unavailable ({probe.get('status')})"
        print(f"{name}: {state}")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
