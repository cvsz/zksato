#!/usr/bin/env bash
# cloudflare-tunnel-add-zksato.sh
#
# Adds zksato.zeaz.dev to the shared zwslcore Cloudflare Tunnel
# (tunnel ID: 45667e7e-7383-4265-b53e-6a9e770a8554) and provisions
# the DNS CNAME record via the Cloudflare API.
#
# Safety:
#   - Reads Cloudflare API token from CF_API_TOKEN env var or a file.
#   - Dry-run by default; set DRY_RUN=false to apply.
#   - Idempotent: safe to re-run; `--overwrite-dns` updates existing CNAME.
#
# Usage:
#   export CF_API_TOKEN="$(cat ~/.config/cloudflared/zksato-api-token)"
#   bash scripts/cloudflare-tunnel-add-zksato.sh
#   DRY_RUN=false bash scripts/cloudflare-tunnel-add-zksato.sh
#
# Prerequisites:
#   - cloudflared installed and authenticated (cert.pem in ~/.cloudflared/)
#   - nginx installed and deploy/nginx.zksato.conf applied
#   - zksato docker compose stack running (api :9569, frontend :3016, dashboard :5174)

set -Eeuo pipefail

TUNNEL_ID="45667e7e-7383-4265-b53e-6a9e770a8554"
HOSTNAME="zksato.zeaz.dev"
DRY_RUN="${DRY_RUN:-true}"

# ── preflight ───────────────────────────────────────────────────────────────

echo "=== zksato Cloudflare Tunnel Go-Live ==="
echo "Tunnel:   $TUNNEL_ID (zwslcore)"
echo "Hostname: $HOSTNAME"
echo "DRY_RUN:  $DRY_RUN"
echo ""

# Confirm cloudflared is available
command -v cloudflared >/dev/null 2>&1 || { echo "ERROR: cloudflared not found in PATH" >&2; exit 1; }

# Confirm nginx is running and listening on 127.0.0.1:8089
if ! ss -tlpn 2>/dev/null | grep -q '127\.0\.0\.1:8089'; then
    echo "WARN: nginx not yet listening on 127.0.0.1:8089"
    echo "      Run: sudo nginx -t && sudo systemctl reload nginx"
    echo "      (after installing deploy/nginx.zksato.conf)"
    if [[ "$DRY_RUN" != "false" ]]; then
        echo "      Continuing in dry-run mode..."
    else
        echo "ERROR: nginx must be running on :8089 before routing tunnel traffic." >&2
        exit 1
    fi
fi

# Confirm zksato API is healthy
if curl -sf --max-time 3 http://127.0.0.1:9569/health >/dev/null 2>&1; then
    echo "✓ zksato API healthy on :9569"
else
    echo "WARN: zksato API not responding on :9569 (is docker compose up?)"
fi

# ── DNS route ───────────────────────────────────────────────────────────────

if [[ "$DRY_RUN" == "false" ]]; then
    echo ""
    echo "→ Provisioning DNS CNAME: $HOSTNAME → $TUNNEL_ID.cfargotunnel.com"
    cloudflared tunnel route dns --overwrite-dns "$TUNNEL_ID" "$HOSTNAME"
    echo "✓ DNS CNAME created/updated"
else
    echo ""
    echo "[DRY-RUN] Would run: cloudflared tunnel route dns --overwrite-dns $TUNNEL_ID $HOSTNAME"
fi

# ── tunnel config update reminder ───────────────────────────────────────────

echo ""
echo "NEXT STEP — Update tunnel remote ingress config:"
echo "  Add the zksato.zeaz.dev rule (see deploy/cloudflared/ingress.example.yml)"
echo "  to the tunnel via Cloudflare Zero Trust dashboard or the API."
echo ""
echo "  The rule to add (insert BEFORE the final http_status:404 catch-all):"
echo "    - hostname: zksato.zeaz.dev"
echo "      service: http://127.0.0.1:8089"
echo ""

if [[ "$DRY_RUN" == "false" ]]; then
    echo "✓ Script completed. Verify:"
    echo "  curl -sf https://$HOSTNAME/health | python3 -m json.tool"
else
    echo "[DRY-RUN] No changes applied. Set DRY_RUN=false to apply."
fi
