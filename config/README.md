# Configuration

TOML configuration intended to layer on top of `ZKSATO_*` environment variables
(see `../.env.example` and `../docs/CONFIGURATION.md`).

- `settings.toml` — base settings (`trading_mode = "paper"`); `settings.toml.example` is the template.
- `environments/{dev,test,uat,prod}.toml` — per-environment values
  (`dev`: paper, `uat`: sandbox, `prod`: live).
- `policies/trading.toml` — trading policy limits.

> **Known issue:** `src/zksato/config.py::_apply_toml_overrides` resolves
> `src/config/settings.toml`, which does not exist, so these files are currently
> **not loaded** at runtime. `environments/*.toml` are not referenced by any code.
> Fixing the path must also make env vars take precedence (the current loop would
> let TOML override `ZKSATO_TRADING_MODE`) — treat as a risk-reviewed change.

Secrets never go in these files; they are read from `.env` or `/run/secrets`.
A `live` value in any file never bypasses operator authorization at the
`TradingService` boundary.
