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
         PostgreSQL (zpostgresql)         Redis (zredis / zRedis)
         (Durable State Store)            (Coordination / Cache)
```

---

## 1.1 Local Shared Infrastructure Integration (`zpostgresql` & `zredis`)

Instead of spinning up isolated database and redis containers, `zksato` can connect to the shared local containers:
- **PostgreSQL**: `zpostgresql` (image: `postgres:15-alpine`, network: `zPostgreSQL_network`)
  - Connection string: `postgresql+psycopg://<username>:<password>@zpostgresql:5432/<db_name>`
  - Bridge IP: `172.26.0.5:5432`
- **Redis**: `zredis` / `zRedis` (image: `redis:7.4.12-alpine`, network: `zPostgreSQL_network`)
  - Uses ACL-based security: `redis://<user>:<password>@zredis:6379/0`
  - Bridge IP: `172.26.0.3:6379`
- **Docker Compose Network**: Join `zPostgreSQL_network` as an external network to resolve container names `zpostgresql` and `zredis`.

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
