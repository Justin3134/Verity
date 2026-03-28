#!/bin/bash
# VERITY — Start all services

echo "╔═════════════════════════════════════════╗"
echo "║         VERITY — Starting Up            ║"
echo "╚═════════════════════════════════════════╝"
echo ""

# Kill any existing processes on these ports
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Start backend
echo "▶ Starting FastAPI backend on :8000..."
cd "$(dirname "$0")/backend"
python3 main.py &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 2

# Start frontend
echo "▶ Starting Next.js frontend on :3000..."
cd "$(dirname "$0")/frontend"
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
