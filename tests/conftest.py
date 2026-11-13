"""Shared pytest fixtures.

CI and clean developer shells do not have ZKSATO_DATABASE_URL (nor the other
ZKSATO_* env vars) that a developer-local .env provides. Settings validation
correctly fails closed when non-paper modes lack durable storage, so tests
that construct Settings directly must control the ambient environment
themselves rather than depend on shell state.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_zksato_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ambient ZKSATO_* vars so Settings tests are deterministic."""
    import os

    for key in list(os.environ):
        if key.startswith("ZKSATO_"):
            monkeypatch.delenv(key, raising=False)
