---
applyTo: "**/*.py"
---
Use Python 3.11+ typing, small cohesive modules, deterministic core logic, and async boundaries only for I/O. Do not catch broad exceptions unless translating at a boundary. Never log secrets. Money-moving functions require explicit inputs, auditable outcomes, idempotency semantics, and failure-path tests. Keep strategy/AI logic outside the trusted execution authority.
