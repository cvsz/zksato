# Rollback plan: <release/change>

## Trigger conditions
Define health, correctness, security, migration, or broker-state conditions requiring rollback.

## Safe target
- Revision/image:
- Database compatibility:
- Config/secrets compatibility:

## Steps
1. stop new automation/mutation as required;
2. preserve broker/local state evidence;
3. restore compatible application/config;
4. execute database rollback/restore only if explicitly safe;
5. verify health/readiness/reconciliation.

## Data caveats
Additive migrations may remain after application rollback. Never destructively roll back evidence without an approved recovery plan.

## Verification and owner
