# Configuration management

Configuration is environment-specific, validated at startup, and never trusted from the browser for security/risk authority.

## Classes
Runtime/service, market-data, strategy defaults, risk policy, broker integration, authentication, database/Redis, observability, notifications.

## Rules
Typed settings with safe defaults; fail startup on invalid production-critical combinations; secrets referenced separately; expose only sanitized non-secret effective configuration; record configuration/policy version in audit and risk decisions.

## Sources and precedence
`src/zksato/config.py` resolves each setting from, highest first:
1. explicit sources, in `settings_customise_sources` order — init kwargs, dotenv,
   AWS Secrets Manager, `ZKSATO_*` environment variables;
2. `config/settings.toml` (or the file named by `ZKSATO_CONFIG_FILE`);
3. field defaults.

TOML mapping: `[section] key` → `section_key` if that field exists; otherwise `key`
only for the flat sections `application`, `coordination`, `database`, `market_data`,
`prediction`, `risk`, `strategy`, `tfex`. Other unmatched keys are ignored (e.g.
`[research] max_drawdown_pct` never touches the risk limit).

TOML safety rules (fail closed):
- empty strings mean "unset";
- secret fields (`*secret*`, `*token*`, `*password*`, `*passphrase*`, `*api_key*`;
  `*_file` paths allowed) are refused — use env or `/run/secrets`;
- `trading_mode = "live"` and `live_trading_enabled = true` are refused — live mode
  is enabled only through operator-controlled environment;
- two keys mapping to the same field, malformed TOML, or a value failing validation
  abort startup with `ValueError`.

`config/environments/*.toml` are reference profiles and are not loaded automatically.

## Change control
Risk/broker/live/auth configuration changes require paper/UAT validation, audit record, rollout/rollback plan, and post-deploy verification.
