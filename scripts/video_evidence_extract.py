#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_binary(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"required binary is not installed: {name}")
    return resolved


def probe(path: Path) -> dict[str, Any]:
    ffprobe = require_binary("ffprobe")
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("ffprobe returned a non-object payload")
    return payload


def duration_seconds(payload: dict[str, Any]) -> float:
    raw = payload.get("format", {})
    if not isinstance(raw, dict):
        return 0.0
    try:
        return max(0.0, float(raw.get("duration", 0.0)))
    except (TypeError, ValueError):
        return 0.0


def sample_times(duration: float, interval: float) -> list[float]:
    if duration <= 0 or interval <= 0:
        return []
    times: list[float] = []
    current = 0.0
    while current < duration:
        times.append(round(current, 3))
        current += interval
    final = max(0.0, duration - 0.05)
    if not times or final - times[-1] > interval * 0.25:
        times.append(round(final, 3))
    return times


def extract_frame(video: Path, output: Path, timestamp: float) -> None:
    ffmpeg = require_binary("ffmpeg")
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-y",
            str(output),
        ],
        check=True,
    )


def extract_video(video: Path, output_root: Path, interval: float) -> dict[str, Any]:
    metadata = probe(video)
    duration = duration_seconds(metadata)
    video_root = output_root / video.stem
    frame_root = video_root / "frames"
    frame_root.mkdir(parents=True, exist_ok=True)

    frames: list[dict[str, object]] = []
    for index, timestamp in enumerate(sample_times(duration, interval)):
        name = f"frame-{index:04d}-{timestamp:09.3f}.jpg"
        destination = frame_root / name
        extract_frame(video, destination, timestamp)
        frames.append(
            {
                "index": index,
                "timestamp_seconds": timestamp,
                "path": str(destination.relative_to(output_root)),
            }
        )

    manifest: dict[str, Any] = {
        "source_name": video.name,
        "source_sha256": sha256_file(video),
        "duration_seconds": duration,
        "sample_interval_seconds": interval,
        "ffprobe": metadata,
        "frames": frames,
        "semantic_annotations": [],
        "notes": (
            "Frames are deterministic evidence only. Semantic trading annotations must be "
            "reviewed separately and must distinguish observation from inference."
        ),
    }
    manifest_path = video_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract reproducible metadata and timestamped frames from trading videos",
    )
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("video-evidence"))
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be positive")

    args.output.mkdir(parents=True, exist_ok=True)
    manifests: list[dict[str, Any]] = []
    for video in args.videos:
        if not video.is_file():
            parser.error(f"video not found: {video}")
        manifests.append(extract_video(video, args.output, args.interval))

    index = {
        "schema_version": 1,
        "videos": [
            {
                "source_name": item["source_name"],
                "source_sha256": item["source_sha256"],
                "duration_seconds": item["duration_seconds"],
                "frame_count": len(item["frames"]),
            }
            for item in manifests
        ],
    }
    (args.output / "index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
