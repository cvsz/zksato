#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from zksato.video_ea import (
    VideoDerivedEaPlanner,
    VideoEaActivationRequest,
    VideoEaPlanRequest,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a non-executing PA/grid research plan from OHLC candles",
    )
    parser.add_argument("input", type=Path, help="JSON file matching VideoEaPlanRequest")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--previous-price", type=float, default=None)
    parser.add_argument("--current-price", type=float, default=None)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    request = VideoEaPlanRequest.model_validate(payload)
    planner = VideoDerivedEaPlanner()
    plan = planner.plan(request)
    result: dict[str, object] = {"plan": plan.model_dump(mode="json")}

    if (args.previous_price is None) != (args.current_price is None):
        parser.error("--previous-price and --current-price must be provided together")
    if args.previous_price is not None and args.current_price is not None:
        activation = planner.activate(
            VideoEaActivationRequest(
                plan=plan,
                previous_price=args.previous_price,
                current_price=args.current_price,
            )
        )
        result["activation"] = activation.model_dump(mode="json")

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
