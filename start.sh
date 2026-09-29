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

if [ -n "${JOURNAL_PYTHON:-}" ]; then
    PYTHON_BIN="$JOURNAL_PYTHON"
elif [ -x "$PROJECT_ROOT/backend/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/backend/.venv/bin/python"
else
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3 is required to start the backend."
        exit 1
    fi
    echo "Creating backend virtual environment..."
    python3 -m venv "$PROJECT_ROOT/backend/.venv" || exit 1
    PYTHON_BIN="$PROJECT_ROOT/backend/.venv/bin/python"
fi

if [ ! -x "$PYTHON_BIN" ]; then
    echo "Python executable not found: $PYTHON_BIN"
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import uvicorn, fastapi, sqlalchemy, pandas, firebase_admin, pydantic_settings' >/dev/null 2>&1; then
    echo "Installing backend dependencies..."
    if command -v uv >/dev/null 2>&1; then
        UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJECT_ROOT/backend/.venv/.uv-cache}" uv pip install --python "$PYTHON_BIN" -r requirements.txt || exit 1
    else
        "$PYTHON_BIN" -m pip --version >/dev/null 2>&1 || "$PYTHON_BIN" -m ensurepip --upgrade || exit 1
        "$PYTHON_BIN" -m pip install -r requirements.txt || exit 1
    fi
fi

if ! "$PYTHON_BIN" -c 'import uvicorn, fastapi, sqlalchemy, pandas, firebase_admin, pydantic_settings' >/dev/null 2>&1; then
    echo "Backend dependencies are still unavailable."
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required to start the frontend."
    exit 1
fi
if ! command -v node >/dev/null 2>&1; then
    echo "Node.js is required to start the frontend."
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/frontend/node_modules/next" ]; then
    echo "Installing frontend dependencies..."
    (cd "$PROJECT_ROOT/frontend" && npm ci) || exit 1
fi

PYTHONPATH="$PROJECT_ROOT/backend" "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$PROJECT_ROOT/backend.log" 2>&1 < /dev/null &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PROJECT_ROOT/.backend.pid"

for attempt in {1..30}; do
    if curl --silent --fail http://127.0.0.1:8000/docs >/dev/null; then
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Backend failed to start. See backend.log:"
        tail -30 "$PROJECT_ROOT/backend.log"
        rm -f "$PROJECT_ROOT/.backend.pid"
        exit 1
    fi
    sleep 1
done
if ! curl --silent --fail http://127.0.0.1:8000/docs >/dev/null; then
    echo "Backend did not become ready. See backend.log:"
    tail -30 "$PROJECT_ROOT/backend.log"
    kill "$BACKEND_PID" 2>/dev/null || true
    rm -f "$PROJECT_ROOT/.backend.pid"
    exit 1
fi
echo "Backend ready (PID: $BACKEND_PID, logs: backend.log)"

# 2. Start Next.js Frontend
echo "Starting Next.js Frontend on port 3000..."
cd "$PROJECT_ROOT/frontend"
NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:8000/api}" node node_modules/next/dist/bin/next dev --webpack -p 3000 -H 127.0.0.1 > "$PROJECT_ROOT/frontend.log" 2>&1 < /dev/null &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$PROJECT_ROOT/.frontend.pid"

for attempt in {1..30}; do
    if curl --silent --fail http://127.0.0.1:3000/ >/dev/null; then
        break
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "Frontend failed to start. See frontend.log:"
        tail -30 "$PROJECT_ROOT/frontend.log"
        "$PROJECT_ROOT/stop.sh"
        exit 1
    fi
    sleep 1
done
if ! curl --silent --fail http://127.0.0.1:3000/ >/dev/null; then
    echo "Frontend did not become ready. See frontend.log:"
    tail -30 "$PROJECT_ROOT/frontend.log"
    "$PROJECT_ROOT/stop.sh"
    exit 1
fi
echo "Frontend ready (PID: $FRONTEND_PID, logs: frontend.log)"

echo "============================================================"
echo " Application startup complete!"
echo " • Web Journal UI:   http://127.0.0.1:3000"
echo " • Backend API Docs:  http://127.0.0.1:8000/docs"
echo " • To stop app:       ./stop.sh"
echo "============================================================"
echo "Keep this terminal open while using the app. Press Ctrl+C to stop it."

trap '"$PROJECT_ROOT/stop.sh" >/dev/null' EXIT
trap 'exit 0' HUP INT TERM
while true; do
    if [ ! -f "$PROJECT_ROOT/.backend.pid" ] && [ ! -f "$PROJECT_ROOT/.frontend.pid" ]; then
        echo "Application stopped."
        exit 0
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Backend stopped unexpectedly. Recent log:"
        tail -30 "$PROJECT_ROOT/backend.log"
        exit 1
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "Frontend stopped unexpectedly. Recent log:"
        tail -30 "$PROJECT_ROOT/frontend.log"
        exit 1
    fi
    sleep 1
done
