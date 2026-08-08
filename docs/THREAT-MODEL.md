# Threat model

## Assets
Broker credentials/PIN, live order authority, account/position data, strategy/risk settings, audit evidence, session credentials, market-data integrity.

## Threat actors
Internet attacker, compromised operator browser, malicious/buggy dependency, insider with excessive privilege, compromised CI/deployment token, faulty AI/strategy, network attacker, provider spoofing/misconfiguration.

## Critical threats
Credential exfiltration; unauthorized live order; risk bypass; replay/duplicate order; CSRF/session theft; stale/tampered quote driving execution; log/trace secret leak; compromised build; audit tampering; broker/local reconciliation drift.

## Controls
Server-side secrets; RBAC/step-up approval; deterministic risk; durable idempotency; TLS; secure sessions/CSRF; stale-feed breaker; signed/provenanced builds where available; redaction; append-oriented audit; reconciliation; least-privilege CI; managed secret rotation.

## Residual risk
Broker/provider outages and market gaps cannot be eliminated. System design must bound exposure, detect uncertainty, fail closed where possible, and support independent broker-side intervention.
