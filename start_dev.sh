#!/bin/bash
# Usage: ./start_dev.sh [--cas]
#
# Without --cas the frontend signs you in as DEV_AUTH_USER (default: your login name)
# through /api/dev/login, so no CAS server is needed. With --cas it goes through the
# real CAS flow at NEXT_PUBLIC_CAS_URL, for testing the integration. The backend uses a
# local sqlite file unless DEV_DATABASE_URL is set.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

USE_CAS=false
for arg in "$@"; do
    case "$arg" in
        --cas) USE_CAS=true ;;
        *) echo "Unknown option: $arg" >&2; echo "Usage: $0 [--cas]" >&2; exit 1 ;;
    esac
done

# Load local config (JWT_SECRET_KEY etc.); the backend refuses to start without it.
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$SCRIPT_DIR/.env"
    set +a
fi
# Same default as docker-compose.yml: the frontend must present this to log users in.
export INTERNAL_AUTH_SECRET="${INTERNAL_AUTH_SECRET:-$JWT_SECRET_KEY}"
# .env holds the Compose database (host a11y-db, mariadb driver); outside Compose use a
# local sqlite file under instance/ (created on start), or whatever DEV_DATABASE_URL says.
export DATABASE_URL="${DEV_DATABASE_URL:-sqlite:///dev.db}"

# Decided before either server starts: the backend reads SITE_ADMINS at startup.
if [ "$USE_CAS" = true ]; then
    unset DEV_AUTH_USER
    echo "Signing in through CAS at ${NEXT_PUBLIC_CAS_URL:-<NEXT_PUBLIC_CAS_URL unset>}"
else
    export DEV_AUTH_USER="${DEV_AUTH_USER:-$(id -un)}"
    # The backend names the account <user>@<domain of NEXT_PUBLIC_CAS_URL> (blueprints/auth.py);
    # list that address as a site admin so the dev account can reach the admin pages.
    cas_host=$(printf '%s' "$NEXT_PUBLIC_CAS_URL" | sed -E 's#^[a-zA-Z]+://##; s#[/:].*##')
    cas_domain=$(printf '%s' "$cas_host" | awk -F. 'NF > 2 { print $(NF-1) "." $NF; next } { print }')
    export SITE_ADMINS="${SITE_ADMINS:+$SITE_ADMINS,}$DEV_AUTH_USER@$cas_domain"
    echo "No CAS: signing in as $DEV_AUTH_USER@$cas_domain as a site admin (set DEV_AUTH_USER to change, or pass --cas)"
fi

cleanup() {
    echo ""
    echo "Shutting down..."
    kill 0 2>/dev/null
    wait 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start Flask backend
echo "Starting Flask backend on http://localhost:5000 (database: $DATABASE_URL)..."
cd "$SCRIPT_DIR"
python app.py &

# Scans run on Celery, same commands as the worker and beat stages in the Dockerfile
# (one worker serves both queues here). Needs the broker from .env, normally a local redis.
echo "Starting Celery worker (queues celery, pages) and beat (broker: ${CELERY_BROKER_URL:-<CELERY_BROKER_URL unset>})..."
celery -A celery_app.celery worker --loglevel=info --concurrency=2 -Q celery,pages &
mkdir -p "$SCRIPT_DIR/instance"
celery -A celery_app.celery beat --loglevel=info --schedule="$SCRIPT_DIR/instance/celerybeat-schedule" &

# Start Next.js frontend
echo "Starting Next.js frontend on http://localhost:3000..."
cd "$SCRIPT_DIR/accessibility-front"
npm run dev &

wait
