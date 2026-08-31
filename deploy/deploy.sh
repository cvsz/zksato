#!/usr/bin/env bash
set -euo pipefail

# Production deployment script for zksato.zeaz.dev
# Usage: ./deploy.sh [environment]
# Environments: production, staging

ENVIRONMENT="${1:-production}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_DIR="$SCRIPT_DIR"

echo "Deploying zksato to $ENVIRONMENT environment..."

# Validate environment file
if [ ! -f "$DEPLOY_DIR/.env.$ENVIRONMENT" ]; then
  echo "ERROR: Environment file .env.$ENVIRONMENT not found"
  exit 1
fi

# Load environment
set -a
source "$DEPLOY_DIR/.env.$ENVIRONMENT"
set +a

# Validate required variables
REQUIRED_VARS=(
  "POSTGRES_PASSWORD"
  "REDIS_PASSWORD"
  "SESSION_SECRET"
  "API_KEYS"
  "CLOUDFLARE_API_TOKEN"
  "CLOUDFLARE_ACCOUNT_ID"
  "CLOUDFLARE_ZONE_ID"
  "CLOUDFLARE_TUNNEL_ID"
)

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "ERROR: Required environment variable $var is not set"
    exit 1
  fi
done

# Validate secrets exist
SECRETS_DIR="$DEPLOY_DIR/secrets"
if [ ! -d "$SECRETS_DIR" ]; then
  echo "ERROR: Secrets directory not found at $SECRETS_DIR"
  exit 1
fi

for secret in postgres_password.txt redis_password.txt session_secret.txt api_keys.txt; do
  if [ ! -f "$SECRETS_DIR/$secret" ]; then
    echo "ERROR: Secret file $secret not found in $SECRETS_DIR"
    exit 1
  fi
done

# Create data directories
mkdir -p "$DEPLOY_DIR/data/postgres" "$DEPLOY_DIR/data/redis" "$DEPLOY_DIR/backups"
chmod 700 "$DEPLOY_DIR/data/postgres" "$DEPLOY_DIR/data/redis"

# Build and deploy
echo "Building Docker images..."
cd "$DEPLOY_DIR"
docker compose -f docker-compose.prod.yml build --no-cache

echo "Running database migrations..."
docker compose -f docker-compose.prod.yml run --rm api python -m zksato.migrations upgrade

echo "Starting services..."
docker compose -f docker-compose.prod.yml up -d

# Wait for health checks
echo "Waiting for services to be healthy..."
sleep 10

HEALTH_CHECK_RETRIES=30
RETRY_INTERVAL=5

for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
  if curl -sf "https://zksato.zeaz.dev/health" > /dev/null 2>&1; then
    echo "Health check passed"
    break
  fi
  if [ $i -eq $HEALTH_CHECK_RETRIES ]; then
    echo "ERROR: Health check failed after $HEALTH_CHECK_RETRIES retries"
    docker compose -f docker-compose.prod.yml logs --tail=50 api
    exit 1
  fi
  echo "Retry $i/$HEALTH_CHECK_RETRIES..."
  sleep $RETRY_INTERVAL
done

echo "Deployment completed successfully!"
echo "Frontend: https://zksato.zeaz.dev"
echo "API: https://zksato-api.zeaz.dev"
echo "Dashboard: https://zksato-dash.zeaz.dev"
