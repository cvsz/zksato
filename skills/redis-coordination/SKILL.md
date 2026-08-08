# Skill: Redis coordination

Use Redis for cache, ephemeral coordination, rate limiting, and distributed locks only when loss of Redis cannot corrupt durable trading truth.

Define lock scope, TTL, renewal, fencing/version semantics, fail behavior, and recovery. PostgreSQL/broker remains authoritative for durable order/position state.
