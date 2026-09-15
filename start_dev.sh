#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load local config (JWT_SECRET_KEY etc.); the backend refuses to start without it.
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$SCRIPT_DIR/.env"
    set +a
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
echo "Starting Flask backend on http://localhost:5000..."
cd "$SCRIPT_DIR"
python app.py &

# Start Next.js frontend
echo "Starting Next.js frontend on http://localhost:3000..."
cd "$SCRIPT_DIR/accessibility-front"
npm run dev &

wait
