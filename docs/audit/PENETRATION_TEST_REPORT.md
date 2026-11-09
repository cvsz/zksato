# Penetration & Vulnerability Testing Report

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Test Scope
Non-destructive penetration testing executed locally against the codebase and test harness:
- Advisory injection and replay
- Multi-tenant state cross-contamination
- Unauthenticated access to order endpoints
- Workflow token exfiltration simulation
- Live-trading elevation attempts

## 2. Findings & Verdicts

| Test Case | Method | Result | Severity |
| :--- | :--- | :--- | :--- |
| **Workflow Token Theft** | Inspected PR workflows for exfiltration paths | Remediated (removed insecure workflows) | Resolved (P0) |
| **Cross-Tenant Advisory Overwrite** | Submitted identical signal ID across distinct tenants | Remediated (composite hashing of tenant/account/signal) | Resolved (P1) |
| **Bypass of Paper Mode via Advisory** | Sent `"mode": "live"` in advisory proposed trade | Rejected by Pydantic validator (HTTP 422) | PASS |
| **Live Order Execution Without 2FA** | Attempted direct order execution in live mode | Rejected by `TradingModeError` / Approval gate | PASS |
| **SQL Injection in StateStore** | Parameterized SQL query audit via SQLAlchemy | No raw SQL concatenation detected | PASS |
| **Dependency CVE Scan** | Next.js CVE-2026-96889 / GHSA-vcvr-r3jv-pc5j | Bumped Next.js to 16.3.6 | Resolved |
