# Document catalog

`INDEX.md` is the navigation page. This catalog defines document classes and maintenance expectations.

| Class | Examples | Update when |
|---|---|---|
| Governance | AGENTS, SECURITY, GOVERNANCE, CONTRIBUTING | authority/process changes |
| Requirements | business/product/functional/NFR/user stories/acceptance | capability goals change |
| Architecture | architecture/system/domain/event/ADR/RFC | design/trust boundaries change |
| Contracts | API/database/auth/data | external or durable contracts change |
| Trading | market/strategy/risk/order/portfolio/TFEX/Settrade | domain behavior changes |
| Operations | deployment/SLO/DR/incident/on-call/maintenance | operating procedure changes |
| Security | threat/SDLC/vulnerability/supply-chain/privacy/access | security/data handling changes |
| Delivery | GitHub/actions/release/versioning/change management | repository/release process changes |
| Evidence templates | docs/templates | evidence requirements change |

Avoid duplicated truth. Link to authoritative implementation/OpenAPI/config when exact runtime behavior is code-defined.
