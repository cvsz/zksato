from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "github_environment_admin.py"
MANIFEST = ROOT / ".github" / "environments" / "requirements.json"


def _load_module() -> ModuleType:
    name = "github_environment_admin_testmodule"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeApi:
    def __init__(self, module: ModuleType, responses: dict[str, Any]) -> None:
        self.module = module
        self.responses = responses
        self.posts: list[tuple[str, dict[str, Any]]] = []
        self.puts: list[tuple[str, dict[str, Any]]] = []
        self.patches: list[tuple[str, dict[str, Any]]] = []

    def get(self, path: str) -> Any:
        return self.responses.get(path, self.module.ApiResult(False, 404, error="not found"))

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        self.puts.append((path, payload))
        return self.module.ApiResult(True, 200, data={})

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        self.posts.append((path, payload))
        return self.module.ApiResult(True, 200, data={})

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        self.patches.append((path, payload))
        return self.module.ApiResult(True, 204)


def test_release_policy_audit_does_not_require_type_echo() -> None:
    module = _load_module()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    spec = manifest["environments"]["release"]
    base = "/repos/cvsz/zksato"
    path = f"{base}/environments/release"
    api = FakeApi(
        module,
        {
            path: module.ApiResult(
                True,
                200,
                data={
                    "deployment_branch_policy": {
                        "protected_branches": False,
                        "custom_branch_policies": True,
                    },
                    "protection_rules": [],
                },
            ),
            f"{path}/deployment-branch-policies?per_page=100": module.ApiResult(
                True,
                200,
                data={"branch_policies": [{"id": 1, "name": "v*"}]},
            ),
            f"{path}/secrets?per_page=100": module.ApiResult(
                True,
                200,
                data={"secrets": []},
            ),
            f"{path}/variables?per_page=30": module.ApiResult(
                True,
                200,
                data={"variables": [{"name": "ENABLE_ATTESTATIONS", "value": "false"}]},
            ),
        },
    )

    report = module.audit_environment(api, base, "release", spec)

    assert report["blocking"] == []
    assert any("required-reviewer" in warning for warning in report["warnings"])


def test_apply_creates_tag_policy_using_manifest_type() -> None:
    module = _load_module()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    spec = manifest["environments"]["release"]
    base = "/repos/cvsz/zksato"
    path = f"{base}/environments/release"
    api = FakeApi(
        module,
        {
            f"{path}/deployment-branch-policies?per_page=100": module.ApiResult(
                True,
                200,
                data={"branch_policies": []},
            ),
            f"{path}/variables/ENABLE_ATTESTATIONS": module.ApiResult(False, 404),
        },
    )

    warnings = module.ensure_environment(api, base, "release", spec, reviewers=None)

    assert warnings == []
    assert (
        f"{path}/deployment-branch-policies",
        {"name": "v*", "type": "tag"},
    ) in api.posts
    assert (
        f"{path}/variables",
        {"name": "ENABLE_ATTESTATIONS", "value": "false"},
    ) in api.posts


def test_repo_base_rejects_ambiguous_repository_names() -> None:
    module = _load_module()

    assert module.repo_base("cvsz/zksato") == "/repos/cvsz/zksato"

    for invalid in ("zksato", "cvsz/", "/zksato", "cvsz/zksato/extra"):
        try:
            module.repo_base(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected invalid repository name to fail: {invalid}")
