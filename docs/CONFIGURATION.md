# Configuration management

Configuration is environment-specific, validated at startup, and never trusted from the browser for security/risk authority.

## Classes
Runtime/service, market-data, strategy defaults, risk policy, broker integration, authentication, database/Redis, observability, notifications.

## Rules
Typed settings with safe defaults; fail startup on invalid production-critical combinations; secrets referenced separately; expose only sanitized non-secret effective configuration; record configuration/policy version in audit and risk decisions.

## Change control
Risk/broker/live/auth configuration changes require paper/UAT validation, audit record, rollout/rollback plan, and post-deploy verification.
