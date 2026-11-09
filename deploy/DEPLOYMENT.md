# Deployment Runbook: zksato.zeaz.dev

## 1. Architecture Topology (Cloudflare Tunnel — Option A)

```text
        Internet (Clients / TradingView / Agents)
                           │
                           ▼
               Cloudflare Edge (TLS)
                           │
            zwslcore tunnel (45667e7e-...)
                           │
                           ▼
           NGINX :8089  (127.0.0.1 loopback)
              │               │              │
              ▼               ▼              ▼
       /           /v1, /health,         /dash/
  Frontend       /metrics, /readyz     Dashboard
  Next.js 16    FastAPI (api)           Vite
   :3016           :9569                :5174
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
 PostgreSQL (zpostgresql)   Redis (zredis / zRedis)
 (Durable State Store)      (Coordination / Cache)
```

**TLS is handled by Cloudflare** — no certbot/Let's Encrypt needed.
NGINX listens on `127.0.0.1:8089` (loopback only, never exposed to the internet).
The `cloudflared` systemd service routes `zksato.zeaz.dev` traffic through the
existing shared `zwslcore` tunnel into NGINX.

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

## 2. Go-Live: Cloudflare Tunnel + NGINX Setup

### Step 1 — Install & configure NGINX on the host

```bash
# Install nginx if not present
sudo apt-get install -y nginx

# Install the zksato reverse-proxy site config
sudo cp /home/cvsz/zksato/deploy/nginx.zksato.conf /etc/nginx/sites-available/zksato
sudo ln -sf /etc/nginx/sites-available/zksato /etc/nginx/sites-enabled/zksato

# Validate and reload
sudo nginx -t
sudo systemctl reload nginx

# Confirm it's listening on 127.0.0.1:8089
ss -tlpn | grep 8089
```

### Step 2 — Ensure zksato services are running

```bash
cd /home/cvsz/zksato
docker compose up -d --build

# Confirm all services healthy
docker compose ps

# Spot-check endpoints
curl http://127.0.0.1:9569/health           # API
curl -sI http://127.0.0.1:3016/            # Frontend
curl -sI http://127.0.0.1:5174/            # Dashboard
```

### Step 3 — Add zksato.zeaz.dev to Cloudflare Tunnel

**Provision the DNS CNAME via cloudflared:**
```bash
cloudflared tunnel route dns --overwrite-dns \
  45667e7e-7383-4265-b53e-6a9e770a8554 zksato.zeaz.dev
```

Or use the helper script (dry-run by default):
```bash
bash /home/cvsz/zksato/scripts/cloudflare-tunnel-add-zksato.sh

# When ready to apply:
DRY_RUN=false bash /home/cvsz/zksato/scripts/cloudflare-tunnel-add-zksato.sh
```

**Update the tunnel remote ingress config** (via Cloudflare Zero Trust dashboard or API).
Insert **before** the final `service: http_status:404` catch-all:

```yaml
- hostname: zksato.zeaz.dev
  service: http://127.0.0.1:8089
  originRequest:
    connectTimeout: 10s
    tcpKeepAlive: 30s
```

See `deploy/cloudflared/ingress.example.yml` for the full documented rule.

---

## 3. Prerequisites & DNS

- Cloudflare Tunnel `zwslcore` running: `systemctl status cloudflared`
- nginx installed on host: `sudo apt-get install -y nginx`
- zksato stack healthy: `docker compose ps`
- No inbound port 80/443 firewall rule needed — Cloudflare Tunnel is outbound-only.

---

## 4. Production Stack Startup

```bash
cd /home/cvsz/zksato
docker compose up -d --build
```

For production compose with secrets:
```bash
cd /home/cvsz/zksato/deploy
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 5. Verification & Health Monitoring

1. **Verify local services online**:
   ```bash
   docker compose ps
   curl http://127.0.0.1:9569/health
   ```

2. **Verify NGINX routing**:
   ```bash
   curl -sf http://127.0.0.1:8089/health | python3 -m json.tool
   curl -sI http://127.0.0.1:8089/
   curl -sI http://127.0.0.1:8089/dash/
   ```

3. **Verify public endpoints via Cloudflare Tunnel**:
   - Operator UI: `https://zksato.zeaz.dev/`
   - TradingView Market Terminal: `https://zksato.zeaz.dev/v1/market/terminal`
   - Health Check: `https://zksato.zeaz.dev/health`
   - Native Agent OS Skills: `https://zksato.zeaz.dev/v1/agent-os/skills`
   - Prometheus Metrics: `https://zksato.zeaz.dev/metrics`
   - Lite Dashboard: `https://zksato.zeaz.dev/dash/`

4. **Log Inspection**:
   ```bash
   docker compose logs -f api
   journalctl -u cloudflared -f
   sudo tail -f /var/log/nginx/access.log
   ```

---

## 6. Rollback

- Remove the `zksato.zeaz.dev` ingress rule from the tunnel config (Cloudflare dashboard).
- Or disable the NGINX site: `sudo rm /etc/nginx/sites-enabled/zksato && sudo systemctl reload nginx`
- Application rollback must account for schema compatibility. If a broker-mutating release is rolled back, reconcile broker state before resuming automation.
