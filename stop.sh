#!/bin/bash

# Advanced AI Trading Journal - Application Shutdown Script

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "============================================================"
echo " Stopping Advanced AI Trading Journal"
echo "============================================================"

# Stop Backend
if [ -f "$PROJECT_ROOT/.backend.pid" ]; then
    BACKEND_PID=$(cat "$PROJECT_ROOT/.backend.pid")
    echo "Stopping Backend process (PID: $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
    rm -f "$PROJECT_ROOT/.backend.pid"
fi

# Stop Frontend
if [ -f "$PROJECT_ROOT/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PROJECT_ROOT/.frontend.pid")
    echo "Stopping Frontend process (PID: $FRONTEND_PID)..."
    kill "$FRONTEND_PID" 2>/dev/null || true
    rm -f "$PROJECT_ROOT/.frontend.pid"
fi

# Fallback cleanup for processes bound to ports 8000 and 3000
echo "Ensuring ports 8000 and 3000 are freed..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :3000 | xargs kill -9 2>/dev/null || true

echo "============================================================"
echo " Application stopped successfully."
echo "============================================================"
