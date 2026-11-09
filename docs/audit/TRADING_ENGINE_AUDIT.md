# Trading Engine & Order Lifecycle Audit

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Lifecycle State Transitions

Orders progress strictly along authorized state transitions:
```
           +-----------+
           | SUBMITTED |
           +-----+-----+
                 |
         +-------v-------+
         |   ACCEPTED    |
         +-------+-------+
                 |
      +----------+----------+
      |                     |
+-----v-----+         +-----v-----+
| PARTIALLY |         |  FILLED   |
|  FILLED   |         +-----------+
+-----+-----+
      |
+-----v-----+
|  FILLED   |
+-----------+
```
Terminal states: `FILLED`, `CANCELLED`, `REJECTED`, `EXPIRED`.
Transitions out of terminal states are strictly forbidden and raise state errors.

## 2. Idempotency & Duplicate Rejection
- All orders enforce unique `client_order_id` values per trading session.
- Submitting a duplicate `client_order_id` raises a `ValueError("duplicate client_order_id")` and prevents double execution.
- Verified in `tests/test_service.py` and `tests/test_paper_matching.py`.

## 3. Paper Trading Isolation
- `PaperBroker` maintains simulated order matching based on bid/offer quote feeds.
- Live broker credentials are never initialized or referenced when running in `paper` mode.
- Market feeds for paper execution are isolated from live order routing paths.
