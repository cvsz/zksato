#!/usr/bin/env python3
from __future__ import annotations

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen


def hit(url: str, api_key: str | None) -> tuple[int, float]:
    headers = {"X-API-Key": api_key} if api_key else {}
    request = Request(url, headers=headers)
    started = time.perf_counter()
    with urlopen(request, timeout=10) as response:  # noqa: S310 - operator-selected local endpoint
        response.read()
        status = response.status
    return status, (time.perf_counter() - started) * 1000


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded zksato HTTP load probe")
    parser.add_argument("--url", default="http://127.0.0.1:9569/health")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--api-key")
    args = parser.parse_args()
    count = min(max(args.requests, 1), 10000)
    concurrency = min(max(args.concurrency, 1), 200)
    samples: list[float] = []
    failures = 0
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
    samples.sort()
    p95 = samples[min(len(samples) - 1, int(len(samples) * 0.95))] if samples else 0
    print({
        "requests": count,
        "failures": failures,
        "mean_ms": round(statistics.mean(samples), 2) if samples else 0,
        "p95_ms": round(p95, 2),
    })
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
