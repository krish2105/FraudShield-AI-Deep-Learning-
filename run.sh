#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# FraudShield AI — one-command launcher (Phase 0 hardening)
#
# Starts the FastAPI backend (which also serves the built React app) and the
# Streamlit dashboard, waits until both are healthy, then opens the browser.
# Designed to be bulletproof for a live presentation.
#
#   ./run.sh            # start API (:8000) + Streamlit (:8501)
#   ./run.sh api        # start only the API
#   ./run.sh streamlit  # start only Streamlit
#   ./run.sh stop       # stop anything we started
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

API_PORT=8000
ST_PORT=8501
LOG_DIR="${TMPDIR:-/tmp}/fraudshield"
mkdir -p "$LOG_DIR"
PID_FILE="$LOG_DIR/pids"

open_url() {
  if command -v open >/dev/null 2>&1; then open "$1" >/dev/null 2>&1
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1
  else echo "Open $1 in your browser."; fi
}

wait_for() { # url, name
  local url="$1" name="$2" i=0
  printf "Waiting for %s" "$name"
  until curl -sf "$url" >/dev/null 2>&1; do
    printf "."; sleep 1; i=$((i+1))
    if [ "$i" -ge 40 ]; then echo " timed out (see $LOG_DIR)"; return 1; fi
  done
  echo " ready."
}

stop() {
  if [ -f "$PID_FILE" ]; then
    while read -r pid; do kill "$pid" 2>/dev/null || true; done < "$PID_FILE"
    rm -f "$PID_FILE"
    echo "Stopped FraudShield services."
  else
    echo "Nothing to stop."
  fi
}

start_api() {
  echo "Starting FastAPI on :$API_PORT ..."
  uvicorn api.main:app --port "$API_PORT" > "$LOG_DIR/api.log" 2>&1 &
  echo $! >> "$PID_FILE"
  wait_for "http://localhost:$API_PORT/api/health" "API"
}

start_streamlit() {
  echo "Starting Streamlit on :$ST_PORT ..."
  streamlit run app/streamlit_app.py --server.port "$ST_PORT" \
    --server.headless true > "$LOG_DIR/streamlit.log" 2>&1 &
  echo $! >> "$PID_FILE"
  wait_for "http://localhost:$ST_PORT" "Streamlit"
}

case "${1:-all}" in
  stop) stop ;;
  api) : > "$PID_FILE"; start_api; echo "API:  http://localhost:$API_PORT" ;;
  streamlit) : > "$PID_FILE"; start_streamlit; echo "Streamlit: http://localhost:$ST_PORT" ;;
  all)
    : > "$PID_FILE"
    start_api
    start_streamlit
    echo ""
    echo "  ✅ FraudShield AI is live:"
    echo "     React app   : http://localhost:$API_PORT"
    echo "     API docs    : http://localhost:$API_PORT/docs"
    echo "     Streamlit   : http://localhost:$ST_PORT"
    echo "     Logs        : $LOG_DIR"
    echo "     Stop with   : ./run.sh stop"
    open_url "http://localhost:$API_PORT"
    ;;
  *) echo "Usage: ./run.sh [all|api|streamlit|stop]"; exit 1 ;;
esac
