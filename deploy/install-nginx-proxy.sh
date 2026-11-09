#!/usr/bin/env bash
# deploy/install-nginx-proxy.sh
#
# Sets up the NGINX reverse proxy for zksato.zeaz.dev (Option A).
# Run as a user with passwordless sudo, or run each sudo block manually.
#
# Usage:
#   cd /home/cvsz/zksato
#   bash deploy/install-nginx-proxy.sh
#
# After this script completes:
#   1. Verify: curl -s http://127.0.0.1:8089/health
#   2. Update Cloudflare Tunnel (zwslcore) public hostname to http://127.0.0.1:8089
#      via Zero Trust → Networks → Tunnels → zwslcore → Configure → Public Hostnames

set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> [1/5] Install nginx"
sudo apt-get install -y nginx

echo "==> [2/5] Disable default nginx site"
sudo rm -f /etc/nginx/sites-enabled/default

echo "==> [3/5] Install rate-limit zones snippet"
sudo cp "$REPO_DIR/deploy/nginx-rate-limits.conf" /etc/nginx/conf.d/rate-limits.conf

echo "==> [4/5] Install zksato site config"
sudo cp "$REPO_DIR/deploy/nginx.zksato.conf" /etc/nginx/sites-available/zksato
sudo ln -sf /etc/nginx/sites-available/zksato /etc/nginx/sites-enabled/zksato

echo "==> [5/5] Test config and restart nginx"
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

echo ""
echo "✓ NGINX is live on 127.0.0.1:8089"
echo ""
echo "Verifying routes:"
echo -n "  /health → API     : "
curl -sf http://127.0.0.1:8089/health && echo "OK" || echo "FAIL"
echo -n "  /dash/  → Dashboard: "
curl -sf http://127.0.0.1:8089/dash/ | grep -q '<html' && echo "OK" || echo "FAIL"
echo -n "  /       → Frontend : "
curl -sf http://127.0.0.1:8089/ | grep -q '<html\|next' && echo "OK" || echo "FAIL"

echo ""
echo "NEXT: Update Cloudflare Tunnel (zwslcore) in Cloudflare Zero Trust dashboard:"
echo "  Zero Trust → Networks → Tunnels → zwslcore → Configure → Public Hostnames"
echo "  Set zksato.zeaz.dev → HTTP → 127.0.0.1:8089"
