# Contracts

Versioned JSON Schemas for data exchanged with external systems. Breaking changes
require a new versioned file (`*.v2.schema.json`), never an in-place edit.

- `ztrader-advisory-intent.v1.schema.json` — advisory order intents from ztrader.
  Advisory only: `src/zksato/ztrader_integration.py` records intents and accepts
  them only at the paper-trading boundary; they never place orders directly.
  See `../docs/integrations/ZTRADER_ADVISORY_INTENT.md`.

The HTTP API contract is generated, not stored here: `make openapi` (or
`python scripts/openapi_contract.py --output openapi.json`).
