# Skill: testing and quality

Run unit + API + state-machine/property + integration + resilience + UAT as appropriate.

Always test unhappy paths for money-moving changes. Freeze time/seed randomness where determinism matters. Avoid tests that merely mirror implementation. CI minimum: `ruff check .` and `pytest`.
