# Privacy and sensitive-data handling

zksato may process account identifiers, portfolio/order data, operator identity, IP/request metadata, and broker/session configuration. Treat these as sensitive operational data even when not legally classified as personal data in every jurisdiction.

## Principles
- collect only data required for trading correctness, audit, security, or operations;
- never expose PINs, API secrets, session tokens, approval secrets, or webhook credentials;
- minimize account identifiers in logs/UI/support artifacts;
- use role-based access and least privilege;
- define retention/deletion under `DATA-RETENTION.md`;
- sanitize evidence before sharing outside the authorized team.

## External obligations
The repository does not determine an operator's legal privacy obligations. Production operators must document applicable jurisdiction, data-controller/processor roles, notices, retention, and incident-reporting duties.
