# Architecture Audit Report

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. System Components

The `zksato` platform is structured into clear, decoupled boundaries:

```
[ Frontend: Next.js 16.3.6 App Router (Webpack) ]
                       |
                 (HTTP/JSON API)
                       v
[ Control Plane API: FastAPI 0.162.2 (src/zksato/api.py) ]
      |                 |                   |
      v                 v                   v
[ TradingService ]   [ RiskEngine ]    [ AutomationEngine ]
      |                 |                   |
      +--------+--------+                   |
               v                            v
       [ Broker Adapter ]            [ Market Feed ]
    (PaperBroker / Settrade)    (Demo / CCXT / Settrade)
               |
               v
  [ StateStore / Database / Redis ]
```

## 2. Frontend Architecture
- **Framework**: Next.js 16.3.6 with React 19.2.7 and TypeScript 5.7.3.
- **Routing**: Next.js App Router (`frontend/src/app/[lng]/...`) supporting multi-language (`react-i18next`).
- **Styling**: Tailwind CSS / PostCSS with dark/light theme switching (`next-themes`).
- **Charts**: TradingView lightweight-charts (`lightweight-charts 4.2.3`).
- **Build Mode**: Standalone output via webpack compilation (`next build --webpack`), guaranteeing hermetic container deployment.

## 3. Backend Architecture
- **Framework**: FastAPI with Pydantic v2 schemas and validation models.
- **Storage Layer**: Abstracted `StateStore` supporting in-memory operation as well as PostgreSQL (`SQLAlchemy 2.x` + `psycopg 3.x`) and Redis coordination (`redis-py 8.x`).
- **Authentication**: Role-based access control with Bearer tokens and API keys (`Principal`, `Role`, `AuthManager`), with distinct roles: `read`, `order`, `strategy`, `admin`.

## 4. Architectural Boundaries
- Strict separation between signal generation (`AutomationEngine`), risk evaluation (`RiskEngine`), execution (`TradingService`), and broker reconciliation.
- External advisories (e.g. `zTrader`) ingest data only through schema-validated intake endpoints that cannot trigger trade submission or bypass risk evaluations.
