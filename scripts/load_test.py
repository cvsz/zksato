#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen


def hit(url: str, api_key: str | None) -> tuple[int, float]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    quote = {
        "symbol": f"MOCK{random.randint(1, 100)}",
        "last": round(random.uniform(10, 100), 2),
        "bid": round(random.uniform(9, 100), 2),
        "offer": round(random.uniform(10, 101), 2),
        "volume": random.randint(100, 10000),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    data = json.dumps(quote).encode("utf-8")
    request = Request(url, data=data, headers=headers, method="POST")
    started = time.perf_counter()
    with urlopen(request, timeout=10) as response:  # noqa: S310
        response.read()
        status = response.status
    return status, (time.perf_counter() - started) * 1000


def percentile(samples: list[float], fraction: float) -> float:
    if not samples:
        return 0.0
    index = min(len(samples) - 1, max(0, int((len(samples) - 1) * fraction)))
    return samples[index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded zksato HTTP load probe")
    parser.add_argument("--url", default="http://127.0.0.1:9569/v1/market/quote")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--api-key")
    parser.add_argument("--max-failures", type=int, default=0)
    parser.add_argument("--max-p95-ms", type=float, default=500.0)
    parser.add_argument("--output")
    args = parser.parse_args()

    count = min(max(args.requests, 1), 10_000)
    concurrency = min(max(args.concurrency, 1), 200)
    max_failures = min(max(args.max_failures, 0), count)
    max_p95_ms = max(args.max_p95_ms, 1.0)
    samples: list[float] = []
    failures = 0
    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(hit, args.url, args.api_key) for _ in range(count)]
        for future in as_completed(futures):
            try:
                status, latency = future.result()
                samples.append(latency)
                if status >= 400:
                    failures += 1
            except Exception:  # bounded diagnostic tool; each failure is counted
                failures += 1

    elapsed = max(time.perf_counter() - started, 1e-9)
    samples.sort()
    p50 = percentile(samples, 0.50)
    p95 = percentile(samples, 0.95)
    p99 = percentile(samples, 0.99)
    report = {
        "url": args.url,
        "requests": count,
        "concurrency": concurrency,
        "completed_samples": len(samples),
        "failures": failures,
        "failure_rate_pct": round((failures / count) * 100, 4),
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(count / elapsed, 2),
        "mean_ms": round(statistics.mean(samples), 2) if samples else 0.0,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "max_ms": round(max(samples), 2) if samples else 0.0,
        "thresholds": {
            "max_failures": max_failures,
            "max_p95_ms": max_p95_ms,
        },
        "passed": failures <= max_failures and bool(samples) and p95 <= max_p95_ms,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
