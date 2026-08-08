#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from urllib.request import Request, urlopen


def get_json(url: str, api_key: str) -> dict[str, object]:
    request = Request(url, headers={"X-API-Key": api_key})
    with urlopen(request, timeout=15) as response:  # noqa: S310 - operator-selected UAT endpoint
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object from {url}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Non-mutating Settrade UAT certification probe")
    parser.add_argument("--base-url", default="http://127.0.0.1:9569")
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()
    health = get_json(f"{args.base_url}/health", args.api_key)
    config = get_json(f"{args.base_url}/v1/config", args.api_key)
    feed = get_json(f"{args.base_url}/v1/market/settrade/status", args.api_key)
    evidence = {"health": health, "config": config, "feed": feed}
    print(json.dumps(evidence, indent=2, sort_keys=True))
    if config.get("trading_mode") != "sandbox":
        print("UAT certification requires ZKSATO_TRADING_MODE=sandbox")
        return 2
    if not config.get("settrade_configured"):
        print("Settrade credentials are incomplete")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
