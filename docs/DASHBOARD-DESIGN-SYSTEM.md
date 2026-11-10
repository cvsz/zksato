# ZKSATO Dashboard Design System & Tokens

## Reference
TailAdmin Next.js (`https://nextjs-demo.tailadmin.com/`) adapted for High-Precision Financial Trading Operations.

## 1. Palette & Surface Tokens
| Token | Dark (Default) | Light | Semantic Purpose |
|---|---|---|---|
| `--bg-base` | `#0B111E` / `#060913` | `#F3F4F6` | Root application background |
| `--bg-surface` | `#111827` / `#0F172A` | `#FFFFFF` | Card, container, and sidebar surface |
| `--bg-subtle` | `#1E293B` | `#F9FAFB` | Input background, table header |
| `--bg-hover` | `rgba(255, 255, 255, 0.05)` | `rgba(0, 0, 0, 0.04)` | Interactive hover state |
| `--border-subtle` | `rgba(255, 255, 255, 0.08)` | `rgba(0, 0, 0, 0.08)` | Standard card/divider borders |
| `--border-medium` | `rgba(255, 255, 255, 0.16)` | `rgba(0, 0, 0, 0.16)` | Active and focused element borders |

## 2. Trading Semantics & Accent Colors
| Accent | Hex / RGBA | Financial Semantics |
|---|---|---|
| `--color-primary` | `#3B82F6` | Interactive focus, links, brand indicators |
| `--color-accent` | `#10B981` | Profit, executed buy fills, nominal preflight pass |
| `--color-danger` | `#EF4444` | Loss, emergency kill switch, sell executions, halted engine |
| `--color-warning` | `#F59E0B` | Degraded network, warning alerts, uncommitted state |
| `--color-secondary` | `#8B5CF6` | AI analysis, indicators, research telemetry |

## 3. Typography & Financial Numerics
- **Primary Interface**: `Outfit, system-ui, sans-serif`
- **Numbers / Prices / Hashes / Quantities**: `JetBrains Mono, monospace` (font-mono with tabular figures)
- Precision rules: 2 decimal places for price/PNL, 4 decimals for crypto/derivatives rates.

## 4. Component Standards
- **Metric Cards (`.tailadmin-metric-card`)**: Fixed 4-column responsive grid with icon badge, large metric value, title, and bottom trend indicator.
- **Table Cards (`.tailadmin-table-card`)**: Card header with title & actions, scrollable horizontal table, zebra hover, and crisp status badges.
- **Action Buttons**: `.btn-base` with `.btn-primary`, `.btn-danger`, `.btn-secondary`, `.btn-sm`.
