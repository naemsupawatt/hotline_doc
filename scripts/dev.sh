#!/usr/bin/env bash
# เปิด backend + frontend พร้อมกัน  (Ctrl+C ปิดทั้งคู่)
#   ./scripts/dev.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
. "$HOME/.nvm/nvm.sh" && nvm use >/dev/null

trap 'kill 0' EXIT INT TERM

(cd "$ROOT/backend"  && uv run uvicorn app.main:app --reload --port 8000) &
(cd "$ROOT/frontend" && npm run dev) &

cat <<'BANNER'

  Frontend    http://localhost:3000
  API docs    http://localhost:8000/docs   <- เปิดหน้านี้โชว์กรรมการได้เลย
  Health      http://localhost:8000/health

BANNER
wait
