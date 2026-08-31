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

# Ensure secrets directory exists
SECRETS_DIR="$DEPLOY_DIR/secrets"
mkdir -p "$SECRETS_DIR"

# Sync secrets from parent .env if not present in deploy/secrets
sync_secret() {
  local secret_name="$1"
  local env_var_name="$2"
  local secret_file="$SECRETS_DIR/$secret_name.txt"
  
  if [ ! -f "$secret_file" ] && [ -n "${!env_var_name:-}" ]; then
    echo "$secret_name: syncing from .env to deploy/secrets/"
    printf '%s' "${!env_var_name}" > "$secret_file"
    chmod 600 "$secret_file"
  fi
}

sync_secret "postgres_password" "POSTGRES_PASSWORD"
sync_secret "session_secret" "ZKSATO_SESSION_SECRET"
sync_secret "api_keys" "ZKSATO_API_KEYS"

# Handle Redis password - generate if not present
if [ ! -f "$SECRETS_DIR/redis_password.txt" ]; then
  if [ -n "${REDIS_PASSWORD:-}" ]; then
    echo "redis_password: syncing from .env to deploy/secrets/"
    printf '%s' "$REDIS_PASSWORD" > "$SECRETS_DIR/redis_password.txt"
  else
    echo "redis_password: generating random password"
    openssl rand -hex 32 > "$SECRETS_DIR/redis_password.txt"
  fi
  chmod 600 "$SECRETS_DIR/redis_password.txt"
fi

# Validate required secrets exist
REQUIRED_SECRETS=("postgres_password" "redis_password" "session_secret" "api_keys")
for secret in "${REQUIRED_SECRETS[@]}"; do
  if [ ! -f "$SECRETS_DIR/$secret.txt" ]; then
    echo "ERROR: Secret file $secret.txt not found in $SECRETS_DIR"
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
