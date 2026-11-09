# Risk Management Review

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Risk Evaluation Architecture

Every order intent passes through `RiskEngine.evaluate(intent, context)` prior to submission.
The risk context is assembled on the server boundary (`service.risk_context_for(intent)`) and cannot be tampered with by clients or caller payloads.

## 2. Risk Controls Implemented & Verified

1. **Global Kill Switch**:
   When `settings.kill_switch = True`, all order submissions are rejected immediately.
2. **Maximum Position Size Limits**:
   Single position concentration limits prevent oversized exposure relative to portfolio equity.
3. **Maximum Order Notional**:
   Prevents accidental "fat-finger" submissions exceeding permissible capital allocations.
4. **Stale Market Price Fail-Closed**:
   If the market quote age exceeds `settings.max_quote_age_seconds`, order validation fails closed.
5. **Two-Person Rule / Live Approvals**:
   Live orders require explicit operator authorization and distinct approvers when `require_distinct_approver = True`.

## 3. Failure Path Testing
Independent failure tests verify that:
- Stale feeds reject execution.
- Missing quotes reject execution.
- Disconnected broker / storage failures abort without persisting partial fills.
- Risk rejections generate immutable audit log records.
