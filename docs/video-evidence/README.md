# Trading-video evidence

This directory stores **small, reviewable evidence manifests**, not source videos.

`three-clips.json` identifies the exact three user-supplied recordings by SHA-256 and separates frame-visible observations from strategy inference. Media files and extracted frames are intentionally not committed.

For a new recording, run:

```bash
python scripts/video_evidence_extract.py video.mp4 --output video-evidence --interval 1.0
```

The extractor writes ffprobe metadata, SHA-256 identity, timestamped frames and a JSON manifest. Semantic annotations still require review; a video montage is not sufficient evidence of profitability or production safety.

When converting video behavior into repository logic:

1. record direct observations first;
2. label every hidden-rule reconstruction as inference;
3. convert the inference into deterministic, testable rules;
4. add hard risk/exposure/idempotency limits before any simulation;
5. validate in replay/backtest/walk-forward;
6. keep research code outside broker authority;
7. use Settrade Sandbox/UAT for broker-specific verification;
8. preserve explicit operator authorization for any separately approved live-equity canary.
