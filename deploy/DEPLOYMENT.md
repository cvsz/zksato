# Deployment Runbook: zksato.zeaz.dev

## 1. Architecture Topology

```text
               Internet (Clients / TradingView / Agents)
                                  │
                                  ▼
                         [ Port 80 / 443 ]
                       NGINX Reverse Proxy
                    (SSL / TLS via Let's Encrypt)
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
   / (Root)                 /v1, /health,               /dash
Frontend (Next.js 16)      /metrics, /readyz          Dashboard (Vite)
   Port 3000                 FastAPI (api)                 Port 80
                               Port 9569
                                  │
                   ┌──────────────┴──────────────┐
                   │                             │
                   ▼                             ▼
            PostgreSQL 16                      Redis 7
         (Durable State Store)         (Coordination / Cache)
```

---

## 2. Prerequisites & DNS Configuration

1. Ensure the domain `zksato.zeaz.dev` points to this server's public IPv4 address (`A` record).
2. Ensure inbound firewall ports `80` (HTTP) and `443` (HTTPS) are open.

---

## 3. SSL / TLS Certificate Provisioning

Run the automated SSL setup script to obtain Let's Encrypt certificates:

```bash
cd /home/cvsz/zworkforce/packages/zksato/deploy
./setup_ssl.sh
```

Or execute Certbot directly:
```bash
sudo certbot certonly --standalone -d zksato.zeaz.dev --non-interactive --agree-tos -m admin@zeaz.dev
```

---

## 4. Production Stack Startup

From the `deploy/` directory:

```bash
cd /home/cvsz/zworkforce/packages/zksato/deploy
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 5. Verification & Health Monitoring

1. **Verify Services Online**:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

2. **Check Core Endpoints**:
   - Operator UI: `https://zksato.zeaz.dev/`
   - TradingView Market Terminal: `https://zksato.zeaz.dev/v1/market/terminal`
   - Health Check: `https://zksato.zeaz.dev/health`
   - Native Agent OS Skills: `https://zksato.zeaz.dev/v1/agent-os/skills`
   - Prometheus Metrics: `https://zksato.zeaz.dev/metrics`
   - Lite Dashboard: `https://zksato.zeaz.dev/dash`

3. **Log Inspection**:
   ```bash
   docker compose -f docker-compose.prod.yml logs -f api
   ```
