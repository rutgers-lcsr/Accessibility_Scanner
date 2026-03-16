#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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
