# Integration Test Report

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Test Execution Summary

The complete integration test suite was run locally using pytest in the verified `.venv` environment:
- **Command**: `.venv/bin/pytest`
- **Total Tests**: 361 collected
- **Passed**: 355
- **Skipped**: 6 (UAT credentials excluded from standard offline CI)
- **Failed**: 0
- **Duration**: 13.56s

## 2. Tested Integration Subsystems
- **API to StateStore**: Verification of order, quote, and fill event persistence.
- **Paper Broker to Quotes**: Resting limit order matching upon quote price crosses.
- **zTrader Integration**: Advisory intake, trace propagation, tenant isolation, and risk rejection.
- **Workflow Security**: Automated verification of GitHub Action workflow trust boundaries.
- **Financial Invariants**: Price/quantity validation, cash conservation, and P&L accounting.
