from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "environments" / "requirements.json"


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def test_environment_manifest_has_expected_protected_domains() -> None:
    manifest = _manifest()
    assert manifest["schema_version"] == 1
    assert manifest["repository"] == "cvsz/zksato"
    environments = manifest["environments"]
    assert set(environments) == {"uat", "production", "release"}

    assert environments["uat"]["deployment"] is False
    assert environments["production"]["deployment"] is False
    assert environments["release"]["deployment"] is True

    assert environments["uat"]["branch_policies"] == [{"name": "main", "type": "branch"}]
    assert environments["production"]["branch_policies"] == [{"name": "main", "type": "branch"}]
    assert environments["release"]["branch_policies"] == [{"name": "v*", "type": "tag"}]


def test_only_workflow_scoped_application_keys_are_required_in_github() -> None:
    manifest = _manifest()
    environments = manifest["environments"]
    required = {
        secret
        for environment in environments.values()
        for secret in environment.get("required_secrets", [])
    }
    assert required == {
        "ZKSATO_UAT_API_KEY",
        "ZKSATO_PRODUCTION_RISK_API_KEY",
    }

    forbidden = set(
        manifest["runtime_secret_boundary"]["do_not_install_as_actions_environment_secrets"]
    )
    assert required.isdisjoint(forbidden)
    assert "ZKSATO_SETTRADE_APP_SECRET" in forbidden
    assert "ZKSATO_SETTRADE_PIN" in forbidden
    assert "ZKSATO_DATABASE_URL" in forbidden
    assert "ZKSATO_SESSION_SECRET" in forbidden


def test_environment_url_variables_are_explicit_and_non_secret() -> None:
    manifest = _manifest()
    environments = manifest["environments"]
    assert environments["uat"]["required_variables"] == ["ZKSATO_UAT_BASE_URL"]
    assert environments["production"]["required_variables"] == ["ZKSATO_PRODUCTION_BASE_URL"]
    assert environments["release"]["required_variables"] == []


def test_uat_workflow_uses_non_deployment_environment_and_safe_override() -> None:
    workflow = _workflow("uat-certification.yml")
    assert "name: uat" in workflow
    assert "deployment: false" in workflow
    assert "vars.ZKSATO_UAT_BASE_URL" in workflow
    assert "secrets.ZKSATO_UAT_API_KEY" in workflow
    assert "Missing UAT base URL" in workflow
    assert "https://" in workflow


def test_production_workflow_stays_non_executing_and_fail_closed() -> None:
    workflow = _workflow("production-readiness.yml")
    assert "name: production" in workflow
    assert "deployment: false" in workflow
    assert "vars.ZKSATO_PRODUCTION_BASE_URL" in workflow
    assert "secrets.ZKSATO_PRODUCTION_RISK_API_KEY" in workflow
    assert "READINESS_ONLY" in workflow
    assert "/v1/production/readiness" in workflow
    assert "/v1/production/canary-plan" in workflow
    assert "/v1/orders" not in workflow
    assert 'plan.get("autonomous_execution") is False' in workflow
    assert 'plan.get("maximum_orders") == 1' in workflow


def test_release_workflow_is_bound_to_release_environment() -> None:
    workflow = _workflow("release.yml")
    assert "name: release" in workflow
    assert "tags:" in workflow
    assert '      - "v*"' in workflow
    assert "packages: write" in workflow
    assert "attestations: write" in workflow
    assert "vars.ENABLE_ATTESTATIONS" in workflow


def test_safe_capability_defaults_are_disabled_until_verified() -> None:
    manifest = _manifest()
    assert manifest["repository_variables"] == {
        "ENABLE_CODEQL": "false",
        "ENABLE_DEPENDENCY_REVIEW": "false",
        "ENABLE_ATTESTATIONS": "false",
    }
    assert manifest["environments"]["release"]["managed_variables"] == {
        "ENABLE_ATTESTATIONS": "false"
    }
