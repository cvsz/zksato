# Financial Data Integrity Audit

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Scope & Verification Goals
- Decimal precision & floating-point safety
- Cash conservation during execution simulation
- Realized & unrealized P&L calculations
- Multi-asset portfolio aggregation
- Elimination of invalid / negative financial values

## 2. Invariants Audited

### A. Non-Positive Price and Quantity Rejection
All order intents and fill records reject `quantity <= 0`, `price <= 0`, and negative fees:
```python
class OrderIntent(BaseModel):
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
```
Verified in: `tests/test_financial_invariants.py::test_order_intent_strictly_rejects_non_positive_prices_and_quantities`.

### B. Cash Conservation
In the paper trading matching engine (`PaperBroker`), execution of buy orders deducts exact notional cash plus commissions:
$$\text{Equity} = \text{Cash} + \sum \text{Market Value} \le \text{Initial Cash}$$
Verified in: `tests/test_financial_invariants.py::test_cash_conservation_in_paper_matching`.

### C. P&L Accounting
- **Long Positions**:
  $$\text{Unrealized P&L} = (\text{Market Price} - \text{Average Price}) \times \text{Quantity}$$
- **Short Positions (TFEX)**:
  $$\text{Unrealized P&L} = (\text{Average Price} - \text{Market Price}) \times |\text{Quantity}|$$
Verified in: `tests/test_financial_invariants.py::test_position_pnl_long_and_short_invariants`.

### D. Portfolio Aggregation
Portfolio snapshots aggregate position market values and unrealized P&L without accumulator drift:
$$\text{Total Equity} = \text{Cash} + \text{Total Market Value}$$
Verified in: `tests/test_financial_invariants.py::test_portfolio_snapshot_aggregation_invariants`.
