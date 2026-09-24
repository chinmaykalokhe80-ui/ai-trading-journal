#!/bin/bash

# Advanced AI Trading Journal - Application Launcher Script

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "============================================================"
echo " Starting Advanced AI Trading Journal (Indian Equity & F&O)"
echo "============================================================"

# 1. Start Python FastAPI Backend
echo "Starting Backend API on port 8000..."
cd "$PROJECT_ROOT/backend"

PYTHONPATH="$PROJECT_ROOT/backend" /opt/anaconda3/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PROJECT_ROOT/.backend.pid"
echo "Backend started (PID: $BACKEND_PID, logs: backend.log)"

# 2. Start Next.js Frontend
echo "Starting Next.js Frontend on port 3000..."
cd "$PROJECT_ROOT/frontend"
npm run dev -- -p 3000 > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$PROJECT_ROOT/.frontend.pid"
echo "Frontend started (PID: $FRONTEND_PID, logs: frontend.log)"

echo "============================================================"
echo " Application standard startup complete!"
echo " • Web Journal UI:   http://localhost:3000"
echo " • Backend API Docs:  http://localhost:8000/docs"
echo " • To stop app:       ./stop.sh"
echo "============================================================"
