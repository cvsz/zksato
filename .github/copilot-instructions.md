# GitHub Copilot instructions for zksato

Read `/AGENTS.md` before editing. Preserve the risk-first architecture and port `9569`.

Never generate code that exposes broker credentials, bypasses server-side risk checks, grants an LLM unrestricted broker mutation, or enables autonomous live-money execution.

For Python changes: keep domain logic typed and deterministic, use explicit error handling, add pytest coverage, and run Ruff. For trading changes: document failure modes, idempotency, audit behavior, and paper/UAT validation. Prefer small vertical slices and update relevant docs/ADR/feature matrix in the same change.
