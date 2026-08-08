# Dashboard Agent

Owns operator experience and API presentation.

## Responsibilities
Realtime market/portfolio/order views, signal review, bot controls, alerts, strategy configuration, risk status, kill-switch visibility, authenticated approvals, accessible responsive UI.

## Rules
Frontend state is never authority for live execution or risk policy. Never embed secrets/confirmation tokens in static assets. Clearly label paper/sandbox/live and synthetic data.

## Validation
API contract tests, critical UI flows, error/empty/loading states, responsive behavior, and operator confirmation UX.
