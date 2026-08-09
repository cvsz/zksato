---
applyTo: "migrations/**/*.sql"
---
Migrations are ordered, durable contracts. Prefer additive changes, preserve order/fill/risk/audit/idempotency integrity, document forward/rollback/restore behavior, and test both empty and representative existing databases. Never rewrite a released migration to hide history.
