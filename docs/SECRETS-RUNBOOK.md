# Secrets and rotation runbook

Production credentials must not live in `.env`, images, Git, browser storage, logs, or API responses. zksato can read supported values from `ZKSATO_SECRET_DIR` (default `/run/secrets`). Use a managed secret system or orchestrator secret mount and restrict filesystem permissions.

Rotation procedure: activate the kill switch; stop new broker mutations; rotate App Secret/PIN/session/API keys at their authority; update the managed secret version; restart one instance; verify authentication and UAT/read-only broker access; reconcile broker state; rotate remaining instances; invalidate old sessions/API keys; review audit logs; then restore approved operation.

Supported secret-file names are documented in `.env.example`. Treat broker PIN and App Secret as high-sensitivity credentials and never copy them into tickets or chat logs.
