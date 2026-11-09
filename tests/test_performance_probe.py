"""Unit tests for the bounded performance load probe script."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from scripts.load_test import percentile, run_load_test


def test_percentile_empty_and_valid() -> None:
    assert percentile([], 0.95) == 0.0
    samples = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(samples, 0.50) == 30.0
    assert percentile(samples, 0.95) == 50.0


@pytest.mark.asyncio
async def test_run_load_test_success_output(tmp_path: Path) -> None:
    output_file = tmp_path / "perf.json"

    mock_resp = httpx.Response(200, request=httpx.Request("GET", "http://test/health"))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        exit_code = await run_load_test(
            url="http://test/health",
            concurrency=2,
            requests=10,
            max_failures=0,
            max_p95_ms=500.0,
            output_path=str(output_file),
        )

        assert exit_code == 0
        assert output_file.exists()
        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert data["passed"] is True
        assert data["requests"] == 10
        assert data["failures"] == 0
        assert data["completed_samples"] == 10
        assert data["p95_ms"] <= 500.0


@pytest.mark.asyncio
async def test_run_load_test_failure_slo(tmp_path: Path) -> None:
    output_file = tmp_path / "perf_fail.json"

    mock_resp = httpx.Response(500, request=httpx.Request("GET", "http://test/health"))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        exit_code = await run_load_test(
            url="http://test/health",
            concurrency=2,
            requests=5,
            max_failures=0,
            max_p95_ms=500.0,
            output_path=str(output_file),
        )

        assert exit_code == 1
        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert data["passed"] is False
        assert data["failures"] == 5
