# On-call and escalation

This repository defines the operational process; actual contact rotations must be configured by the operator and must not be fabricated in source.

## Severity
- SEV-1: potential/actual unintended live exposure, execution-boundary bypass, credential compromise, unreconciled production order state.
- SEV-2: production control-plane outage, persistent reconciliation/data-integrity failure without confirmed exposure.
- SEV-3: degraded non-critical function or UAT/paper issue.

## First actions for execution incidents
Stop automation, engage kill switch, verify broker state through the approved interface, isolate affected service, preserve evidence, rotate exposed credentials, and escalate to broker/operator contacts as applicable.

## Handover
Record incident ID, revision, environment, current broker/local state, mitigations, pending actions, owners, and next checkpoint. Use the incident/postmortem templates.
