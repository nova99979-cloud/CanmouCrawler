#!/bin/zsh
set -e
ROOT="/Users/aiqing/.openclaw/workspace-canmou"
APP="$ROOT/desktop_app/CanmouCrawler/app_server.py"
PY="$ROOT/.venv-crawlers311/bin/python"
PORT="${CANMOU_CRAWLER_PORT:-8765}"
mkdir -p "$ROOT/outputs/app_runs"
# If server already running, just open it.
if curl -fsS "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
  open "http://127.0.0.1:$PORT/"
  exit 0
fi
nohup "$PY" "$APP" > "$ROOT/outputs/app_runs/app_server.log" 2>&1 &
sleep 1
open "http://127.0.0.1:$PORT/"
