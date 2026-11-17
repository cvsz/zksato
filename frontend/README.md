# zksato operator UI

Next.js 16 / React 19 operator interface, served on port `3016` and proxied at `/`
by NGINX. It talks only to the FastAPI control plane; broker credentials never
reach the browser.

```bash
npm ci
npm run dev     # http://127.0.0.1:3016
npm run build
```

End-to-end tests use Playwright (`playwright.config.ts`, `tests/`).
Design system: `../docs/ZKSATO-THEME.md`, `../docs/DASHBOARD-DESIGN-SYSTEM.md`.
