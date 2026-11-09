# Database & Persistence Audit

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Storage Model

The database tier is designed for high reliability, auditability, and idempotency:
- **Relational Tables**:
  - `orders`: Canonical order lifecycle state.
  - `fills`: Executed trade fills and commissions.
  - `order_events`: Append-only transition history.
  - `audit_events`: Hash-chained audit logs with SHA-256 integrity verification (`store.verify_audit_chain()`).
  - `runtime_state`: Key-value storage for coordination and advisory persistence.
  - `live_approvals`: Stored approval requests and 2FA/operator signatures.

## 2. Integrity & Concurrency
- Database migrations are versioned under `migrations/` and managed with Alembic / SQLAlchemy models.
- Redis-backed distributed locks (`CoordinationManager`) prevent race conditions during high-frequency signal processing and order submission.
- Backups and point-in-time recovery are supported via `scripts/backup_postgres.sh` and `scripts/restore_postgres.sh`.
