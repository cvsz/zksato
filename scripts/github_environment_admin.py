from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

API = "https://api.github.com"
DEFAULT_MANIFEST = Path(".github/environments/requirements.json")


@dataclass
class ApiResult:
    ok: bool
    status: int | None
    data: Any = None
    error: str | None = None


class GitHubApi:
    def __init__(self, token: str, api_version: str) -> None:
        self.token = token
        self.api_version = api_version

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> ApiResult:
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{API}{path}",
            method=method,
            data=body,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": self.api_version,
                "User-Agent": "zksato-github-environment-admin",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else None
                return ApiResult(True, response.status, data=data)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:4000]
            return ApiResult(False, exc.code, error=detail)
        except (urllib.error.URLError, TimeoutError) as exc:
            return ApiResult(False, None, error=str(exc))

    def get(self, path: str) -> ApiResult:
        return self.request("GET", path)

    def put(self, path: str, payload: dict[str, Any]) -> ApiResult:
        return self.request("PUT", path, payload)

    def post(self, path: str, payload: dict[str, Any]) -> ApiResult:
        return self.request("POST", path, payload)

    def patch(self, path: str, payload: dict[str, Any]) -> ApiResult:
        return self.request("PATCH", path, payload)


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported environment-requirements schema")
    if not isinstance(payload.get("environments"), dict) or not payload["environments"]:
        raise ValueError("manifest requires at least one environment")
    return payload


def repo_base(repository: str) -> str:
    owner, sep, repo = repository.partition("/")
    if not sep or not owner or not repo or "/" in repo:
        raise ValueError("repository must use owner/name form")
    return f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"


def environment_path(base: str, name: str) -> str:
    return f"{base}/environments/{urllib.parse.quote(name, safe='')}"


def names_from(result: ApiResult, key: str) -> set[str] | None:
    if not result.ok or not isinstance(result.data, dict):
        return None
    rows = result.data.get(key, [])
    if not isinstance(rows, list):
        return None
    return {str(item.get("name", "")) for item in rows if isinstance(item, dict)}


def audit_environment(
    api: GitHubApi,
    base: str,
    name: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    path = environment_path(base, name)
    env_result = api.get(path)
    report: dict[str, Any] = {
        "exists": env_result.ok,
        "environment_status": env_result.status,
        "blocking": [],
        "warnings": [],
    }
    if not env_result.ok:
        report["blocking"].append(f"environment {name!r} does not exist or is unreadable")
        report["environment_error"] = env_result.error
        return report

    env_data = env_result.data if isinstance(env_result.data, dict) else {}
    expected_policy = spec["deployment_branch_policy"]
    actual_policy = env_data.get("deployment_branch_policy")
    if actual_policy != expected_policy:
        report["blocking"].append(
            f"deployment branch policy mismatch: expected {expected_policy}, got {actual_policy}"
        )

    policies_result = api.get(f"{path}/deployment-branch-policies?per_page=100")
    report["branch_policy_status"] = policies_result.status
    if policies_result.ok and isinstance(policies_result.data, dict):
        actual = {
            (str(row.get("name", "")), str(row.get("type", "branch")))
            for row in policies_result.data.get("branch_policies", [])
            if isinstance(row, dict)
        }
        expected = {
            (str(row["name"]), str(row.get("type", "branch")))
            for row in spec.get("branch_policies", [])
        }
        missing = sorted(expected - actual)
        if missing:
            report["blocking"].append(f"missing deployment branch/tag policies: {missing}")
        extras = sorted(actual - expected)
        if extras:
            report["warnings"].append(f"extra deployment branch/tag policies: {extras}")
    else:
        report["warnings"].append(
            f"branch policies could not be audited (status={policies_result.status})"
        )

    secrets_result = api.get(f"{path}/secrets?per_page=100")
    report["secret_inventory_status"] = secrets_result.status
    secret_names = names_from(secrets_result, "secrets")
    if secret_names is None:
        report["warnings"].append(
            f"environment secret names could not be audited (status={secrets_result.status})"
        )
    else:
        required = set(spec.get("required_secrets", []))
        missing = sorted(required - secret_names)
        if missing:
            report["blocking"].append(f"missing required environment secrets: {missing}")
        report["present_secret_names"] = sorted(secret_names)

    variables_result = api.get(f"{path}/variables?per_page=30")
    report["variable_inventory_status"] = variables_result.status
    variable_names = names_from(variables_result, "variables")
    if variable_names is None:
        report["warnings"].append(
            f"environment variables could not be audited (status={variables_result.status})"
        )
    else:
        required = set(spec.get("required_variables", []))
        missing = sorted(required - variable_names)
        if missing:
            report["blocking"].append(f"missing required environment variables: {missing}")
        managed = spec.get("managed_variables", {})
        values = {
            str(row.get("name", "")): str(row.get("value", ""))
            for row in variables_result.data.get("variables", [])
            if isinstance(row, dict)
        }
        wrong = {
            key: {"expected": value, "actual": values.get(key)}
            for key, value in managed.items()
            if values.get(key) != value
        }
        if wrong:
            report["blocking"].append(f"managed environment variable mismatch: {wrong}")

    protection_rules = env_data.get("protection_rules", [])
    has_reviewer_rule = any(
        isinstance(rule, dict) and rule.get("type") == "required_reviewers"
        for rule in protection_rules
    )
    recommended = spec.get("recommended_protection", {})
    if recommended.get("required_reviewers") and not has_reviewer_rule:
        report["warnings"].append(
            "required-reviewer protection is not configured; for this private repository it may be plan-gated"
        )

    return report


def audit(
    api: GitHubApi,
    repository: str,
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    base = repo_base(repository)
    environment_reports: dict[str, Any] = {}
    blocking: list[str] = []
    for name, spec in manifest["environments"].items():
        report = audit_environment(api, base, name, spec)
        environment_reports[name] = report
        blocking.extend(f"{name}: {item}" for item in report["blocking"])

    repository_variables = api.get(f"{base}/actions/variables?per_page=100")
    repo_var_report: dict[str, Any] = {
        "status": repository_variables.status,
        "blocking": [],
        "warnings": [],
    }
    if repository_variables.ok and isinstance(repository_variables.data, dict):
        values = {
            str(row.get("name", "")): str(row.get("value", ""))
            for row in repository_variables.data.get("variables", [])
            if isinstance(row, dict)
        }
        for name, expected in manifest.get("repository_variables", {}).items():
            if values.get(name) != expected:
                repo_var_report["blocking"].append(
                    f"{name} expected {expected!r}, got {values.get(name)!r}"
                )
    else:
        repo_var_report["warnings"].append(
            "repository variables are not readable with this token; cannot certify them"
        )
    blocking.extend(f"repository variable: {item}" for item in repo_var_report["blocking"])

    report = {
        "repository": repository,
        "api_version": manifest["api_version"],
        "environments": environment_reports,
        "repository_variables": repo_var_report,
        "blocking": blocking,
        "ready": not blocking,
    }
    return report, blocking


def ensure_environment(
    api: GitHubApi,
    base: str,
    name: str,
    spec: dict[str, Any],
    reviewers: list[dict[str, Any]] | None,
) -> list[str]:
    warnings: list[str] = []
    path = environment_path(base, name)
    payload: dict[str, Any] = {
        "deployment_branch_policy": spec["deployment_branch_policy"],
    }
    if reviewers:
        payload["reviewers"] = reviewers
        payload["prevent_self_review"] = True
    result = api.put(path, payload)
    if not result.ok and reviewers and result.status in {403, 422}:
        # Private repositories on non-Enterprise plans may not expose reviewer/wait rules.
        warnings.append(
            f"{name}: reviewer protection unavailable (status={result.status}); applying branch policy without reviewer rule"
        )
        result = api.put(path, {"deployment_branch_policy": spec["deployment_branch_policy"]})
    if not result.ok:
        raise RuntimeError(f"failed to create/update environment {name}: {result.status} {result.error}")

    policies_result = api.get(f"{path}/deployment-branch-policies?per_page=100")
    if not policies_result.ok:
        raise RuntimeError(
            f"failed to list deployment policies for {name}: {policies_result.status} {policies_result.error}"
        )
    existing = {
        (str(row.get("name", "")), str(row.get("type", "branch")))
        for row in policies_result.data.get("branch_policies", [])
        if isinstance(row, dict)
    }
    for policy in spec.get("branch_policies", []):
        item = (str(policy["name"]), str(policy.get("type", "branch")))
        if item in existing:
            continue
        created = api.post(
            f"{path}/deployment-branch-policies",
            {"name": item[0], "type": item[1]},
        )
        if not created.ok and created.status != 303:
            raise RuntimeError(
                f"failed to create deployment policy {name}:{item}: {created.status} {created.error}"
            )

    for variable, value in spec.get("managed_variables", {}).items():
        existing_var = api.get(f"{path}/variables/{urllib.parse.quote(variable, safe='')}")
        if existing_var.ok:
            updated = api.patch(
                f"{path}/variables/{urllib.parse.quote(variable, safe='')}",
                {"name": variable, "value": value},
            )
            if not updated.ok:
                warnings.append(
                    f"{name}: could not update environment variable {variable} (status={updated.status})"
                )
        elif existing_var.status == 404:
            created = api.post(f"{path}/variables", {"name": variable, "value": value})
            if not created.ok:
                warnings.append(
                    f"{name}: could not create environment variable {variable} (status={created.status})"
                )
        else:
            warnings.append(
                f"{name}: environment variables are inaccessible (status={existing_var.status})"
            )
    return warnings


def resolve_reviewers(api: GitHubApi, logins: list[str]) -> list[dict[str, Any]]:
    reviewers: list[dict[str, Any]] = []
    for login in logins:
        result = api.get(f"/users/{urllib.parse.quote(login)}")
        if not result.ok or not isinstance(result.data, dict):
            raise RuntimeError(f"unable to resolve reviewer {login!r}: {result.status} {result.error}")
        reviewers.append({"type": "User", "id": int(result.data["id"])})
    if len(reviewers) > 6:
        raise ValueError("GitHub supports at most six required environment reviewers")
    return reviewers


def ensure_repository_variables(
    api: GitHubApi,
    base: str,
    variables: dict[str, str],
) -> list[str]:
    warnings: list[str] = []
    for name, value in variables.items():
        item = api.get(f"{base}/actions/variables/{urllib.parse.quote(name, safe='')}")
        if item.ok:
            result = api.patch(
                f"{base}/actions/variables/{urllib.parse.quote(name, safe='')}",
                {"name": name, "value": value},
            )
        elif item.status == 404:
            result = api.post(f"{base}/actions/variables", {"name": name, "value": value})
        else:
            warnings.append(f"repository variable {name} is inaccessible (status={item.status})")
            continue
        if not result.ok:
            warnings.append(f"could not set repository variable {name} (status={result.status})")
    return warnings


def apply(
    api: GitHubApi,
    repository: str,
    manifest: dict[str, Any],
    reviewer_logins: list[str],
) -> list[str]:
    base = repo_base(repository)
    reviewers = resolve_reviewers(api, reviewer_logins) if reviewer_logins else None
    warnings: list[str] = []
    for name, spec in manifest["environments"].items():
        warnings.extend(ensure_environment(api, base, name, spec, reviewers))
    warnings.extend(
        ensure_repository_variables(api, base, manifest.get("repository_variables", {}))
    )
    return warnings


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit or bootstrap the source-controlled GitHub environment contract."
    )
    parser.add_argument("command", choices=["audit", "apply"])
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN" if os.environ.get("GITHUB_ACTIONS") else "GH_TOKEN",
        help="environment variable containing the GitHub token",
    )
    parser.add_argument(
        "--reviewer",
        action="append",
        default=[],
        help="GitHub login to configure as a required reviewer when the plan supports it",
    )
    parser.add_argument("--output", type=Path, default=Path("github-environments.json"))
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    repository = args.repository or str(manifest["repository"])
    if repository != manifest["repository"]:
        raise SystemExit(
            f"repository mismatch: manifest={manifest['repository']} requested={repository}"
        )
    token = os.environ.get(args.token_env, "")
    if not token:
        raise SystemExit(f"{args.token_env} is required")

    api = GitHubApi(token, str(manifest["api_version"]))
    if args.command == "apply":
        warnings = apply(api, repository, manifest, args.reviewer)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)

    report, blocking = audit(api, repository, manifest)
    write_report(args.output, report)
    print(json.dumps({"ready": not blocking, "blocking": blocking}, indent=2))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
