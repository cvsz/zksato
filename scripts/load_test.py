#!/usr/bin/env python3
"""Bounded zksato HTTP load probe for SLO verification.

Compatible with both legacy invocation and .github/workflows/performance.yml contract.
Outputs machine-readable performance.json summary and enforces p95/failure SLOs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx


def percentile(samples: list[float], fraction: float) -> float:
    if not samples:
        return 0.0
    index = min(len(samples) - 1, max(0, round((len(samples) - 1) * fraction)))
    return samples[index]


async def run_load_test(
    url: str,
    concurrency: int,
    requests: int,
    api_key: str | None = None,
    max_failures: int = 0,
    max_p95_ms: float = 500.0,
    output_path: str | None = None,
) -> int:
    count = min(max(requests, 1), 50_000)
    concurrency = min(max(concurrency, 1), 500)
    max_failures = min(max(max_failures, 0), count)
    max_p95_ms = max(max_p95_ms, 1.0)

    headers = {"X-API-Key": api_key} if api_key else {}
    semaphore = asyncio.Semaphore(concurrency)
    samples: list[float] = []
    failures = 0
    started = time.perf_counter()

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits, timeout=10.0, headers=headers) as client:

        async def make_request() -> tuple[int, float]:
            async with semaphore:
                req_start = time.perf_counter()
                try:
                    response = await client.get(url)
                    req_duration = (time.perf_counter() - req_start) * 1000
                    return response.status_code, req_duration
                except Exception:
                    req_duration = (time.perf_counter() - req_start) * 1000
                    return 599, req_duration

        tasks = [make_request() for _ in range(count)]
        results = await asyncio.gather(*tasks)

    for status_code, latency_ms in results:
        samples.append(latency_ms)
        if status_code >= 400:
            failures += 1

    elapsed = max(time.perf_counter() - started, 1e-9)
    samples.sort()

    p50 = percentile(samples, 0.50)
    p95 = percentile(samples, 0.95)
    p99 = percentile(samples, 0.99)
    mean_val = statistics.mean(samples) if samples else 0.0
    passed = failures <= max_failures and bool(samples) and p95 <= max_p95_ms

    report = {
        "url": url,
        "requests": count,
        "concurrency": concurrency,
        "completed_samples": len(samples),
        "failures": failures,
        "failure_rate_pct": round((failures / count) * 100, 4),
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(count / elapsed, 2),
        "mean_ms": round(mean_val, 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "max_ms": round(max(samples), 2) if samples else 0.0,
        "thresholds": {
            "max_failures": max_failures,
            "max_p95_ms": max_p95_ms,
        },
        "passed": passed,
    }

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if output_path:
        Path(output_path).write_text(rendered + "\n", encoding="utf-8")

    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded zksato HTTP load probe")
    parser.add_argument("--url", default="http://127.0.0.1:9569/health")
    parser.add_argument(
        "--base-url",
        dest="base_url",
        default=None,
        help="Alias for backward compatibility",
    )
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--max-failures", type=int, default=0)
    parser.add_argument("--max-p95-ms", type=float, default=500.0)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    target_url = args.url
    if args.base_url:
        target_url = f"{args.base_url.rstrip('/')}/health"

    return asyncio.run(
        run_load_test(
            url=target_url,
            concurrency=args.concurrency,
            requests=args.requests,
            api_key=args.api_key,
            max_failures=args.max_failures,
            max_p95_ms=args.max_p95_ms,
            output_path=args.output,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
