from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
SCRIPTS_DIR = REPO_ROOT / ".github" / "scripts"


def test_vulnerable_reviewer_workflows_do_not_exist() -> None:
    forbidden_files = [
        WORKFLOWS_DIR / "automated-audit-review-approve.yml",
        WORKFLOWS_DIR / "auto-fix-open-prs.yml",
        SCRIPTS_DIR / "post-review-comment.sh",
    ]
    for forbidden in forbidden_files:
        assert not forbidden.exists(), (
            f"Forbidden insecure workflow/script file must not exist: {forbidden}"
        )


def test_no_workflow_exposes_reviewer_pat_or_signing_secrets() -> None:
    assert WORKFLOWS_DIR.exists(), "Workflows directory must exist"
    workflow_files = list(WORKFLOWS_DIR.glob("*.yml")) + list(WORKFLOWS_DIR.glob("*.yaml"))
    assert len(workflow_files) > 0, "Expected workflow files to inspect"

    forbidden_patterns = [
        re.compile(r"POLIEDBC_PAT", re.IGNORECASE),
        re.compile(r"GPG_SIGNING_KEY", re.IGNORECASE),
        re.compile(r"GPG_PASSPHRASE", re.IGNORECASE),
    ]

    for wf in workflow_files:
        content = wf.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert not pattern.search(content), (
                f"Workflow {wf.name} contains forbidden secret reference matching {pattern.pattern}"
            )


def test_pr_triggered_workflows_do_not_use_privileged_secrets_or_review_credentials() -> None:
    for wf in WORKFLOWS_DIR.glob("*.yml"):
        content = wf.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(content)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        triggers = data.get("on") or data.get(True) or {}
        if isinstance(triggers, list):
            trigger_keys = set(triggers)
        elif isinstance(triggers, dict):
            trigger_keys = set(triggers.keys())
        elif isinstance(triggers, str):
            trigger_keys = {triggers}
        else:
            trigger_keys = set()

        is_pr_triggered = any(t in trigger_keys for t in ("pull_request", "pull_request_target"))

        if is_pr_triggered:
            # PR workflows must not reference any PAT secret or signing secret
            assert "secrets.POLIEDBC" not in content
            assert "gh pr review" not in content, (
                f"Workflow {wf.name} triggered by PR must not execute automated 'gh pr review'"
            )
            assert "commit.gpgsign false" not in content, (
                f"Workflow {wf.name} must not disable commit signing for fake commits"
            )
