#!/usr/bin/env bash
set -euo pipefail

DOMAIN="zksato.zeaz.dev"
EMAIL="${SSL_EMAIL:-admin@zeaz.dev}"

echo "==> Configuring SSL Certificate for ${DOMAIN}..."

# Ensure certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "Certbot not found. Please install certbot: sudo apt-get update && sudo apt-get install -y certbot"
fi

# Dry run / certificate issuance command
echo "Execute the following on the host gateway with DNS pointing to this machine:"
echo "sudo certbot certonly --standalone -d ${DOMAIN} --non-interactive --agree-tos -m ${EMAIL}"
echo ""
echo "Or using webroot with running docker-compose.prod.yml:"
echo "sudo certbot certonly --webroot -w /var/www/certbot -d ${DOMAIN} --non-interactive --agree-tos -m ${EMAIL}"
