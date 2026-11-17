# Deployment

Full runbook: [`DEPLOYMENT.md`](DEPLOYMENT.md).

- `docker-compose.prod.yml`, `docker-compose.tls.yml`, `docker-compose.monitoring.yml` — compose overlays
- `nginx*.conf`, `install-nginx-proxy.sh` — loopback NGINX proxy (`127.0.0.1:8089`)
- `cloudflared/` — Cloudflare tunnel ingress example
- `monitoring/` — Prometheus, alert rules, OpenTelemetry collector
- `terraform/` — cloud backup/failover only (localhost Docker Compose is primary)
- `deploy.sh`, `setup_ssl.sh` — deployment helpers
