#!/usr/bin/env bash
# VERITY — Start all services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

pick_python() {
  if [[ -x "$SCRIPT_DIR/backend/.venv/bin/python" ]]; then
    echo "$SCRIPT_DIR/backend/.venv/bin/python"
    return
  fi
  local v="$REPO_ROOT/.venv/bin/python"
  if [[ -x "$v" ]] && "$v" -c "import fastapi" 2>/dev/null; then
    echo "$v"
    return
  fi
  echo "${PYTHON:-python3}"
}

echo "╔═════════════════════════════════════════╗"
echo "║         VERITY — Starting Up            ║"
echo "╚═════════════════════════════════════════╝"
echo ""

# Kill any existing processes on these ports
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

PYTHON="$(pick_python)"

# Start backend
echo "▶ Starting FastAPI backend on :8001..."
cd "$SCRIPT_DIR/backend"
"$PYTHON" main.py &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 2

# Start frontend
echo "▶ Starting Next.js frontend on :3000..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "╔═════════════════════════════════════════╗"
echo "║  VERITY running at: http://localhost:3000 ║"
echo "║  Backend API:       http://localhost:8001 ║"
echo "╚═════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
