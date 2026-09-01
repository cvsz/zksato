#!/usr/bin/env python3
"""Simple load test script for zksato SLO verification.

This script is not a pytest test. Run it manually during performance testing
or as part of a CI job with the `performance` marker.

Usage:
    python scripts/load_test.py --base-url http://127.0.0.1:9569 --concurrency 10 --requests 100
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time

import httpx


async def run_load_test(base_url: str, concurrency: int, requests: int) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def make_request() -> float:
            async with semaphore:
                start = time.perf_counter()
                try:
                    await client.get("/health")
                    duration = time.perf_counter() - start
                    return duration
                except Exception:
                    return float("inf")

        tasks = [make_request() for _ in range(requests)]
        durations = await asyncio.gather(*tasks)

    successful = [d for d in durations if d != float("inf")]
    failed = len(durations) - len(successful)

    if not successful:
        print("All requests failed!")
        return

    print(f"Total requests: {requests}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {failed}")
    print(f"Min: {min(successful) * 1000:.2f} ms")
    print(f"Max: {max(successful) * 1000:.2f} ms")
    print(f"Mean: {statistics.mean(successful) * 1000:.2f} ms")
    print(f"Median: {statistics.median(successful) * 1000:.2f} ms")
    print(f"P95: {statistics.quantiles(successful, n=20)[18] * 1000:.2f} ms")
    print(f"P99: {statistics.quantiles(successful, n=100)[98] * 1000:.2f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="zksato load test")
    parser.add_argument("--base-url", default="http://127.0.0.1:9569")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()

    asyncio.run(run_load_test(args.base_url, args.concurrency, args.requests))


if __name__ == "__main__":
    main()
