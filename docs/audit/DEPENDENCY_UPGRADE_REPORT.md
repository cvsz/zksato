# Dependency Upgrade Report

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Frontend Upgrades

- **Next.js**: Updated from `16.3.3` to `16.3.6` (PR #36 remediation).
  - Addresses security vulnerability GHSA-vcvr-r3jv-pc5j (Remote Code Execution in next/og ImageResponse) and AVIF image optimization bug fixes.
  - Updated `"build": "next build --webpack"` in `package.json` to ensure deterministic builds without turbopack font resolution failure.
  - Successfully verified via `npm run build` and `tsc --noEmit`.

## 2. GitHub Actions Upgrades (PR #45)

- **`docker/login-action`**: Updated from `v4.6.0` (`dbcb813823bdd20940b903addbd779551569679f`) to `v4.8.0` (`8aa5831fb8d48d8f76594c7ddde61ae58019f550`).
- **`github/codeql-action/init` & `analyze`**: Updated from hash `9b3254085494b55a0f7c4c2b3d2d52cc712ce370` to `33d7b85da1a04171e211befe2c739303b9a4c066`.

## 3. Python Toolchain Verification

- Python 3.14.4 virtual environment created at `.venv/`.
- All optional dependency groups `[dev,quality,security]` installed and validated.
- Static typing (`mypy 2.4.1`) verified with 0 issues across 68 files.
- Linter (`ruff 0.16.5`) verified with 0 issues across 353 files.
