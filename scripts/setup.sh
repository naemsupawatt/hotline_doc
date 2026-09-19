#!/usr/bin/env bash
# ติดตั้งครั้งแรกบนเครื่อง — รันครั้งเดียวตอนเริ่มงาน
#   ./scripts/setup.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"

echo "==> Node (ผ่าน nvm ตาม .nvmrc)"
. "$HOME/.nvm/nvm.sh"
nvm install >/dev/null 2>&1 || true
nvm use
echo "    node $(node -v) / npm $(npm -v)"

echo "==> uv + Python 3.13"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.13 >/dev/null
echo "    $(uv --version)"

echo "==> Backend"
cd "$ROOT/backend"
uv sync
[ -f .env ] || { cp .env.example .env; echo "    สร้าง backend/.env แล้ว"; }

echo "==> Frontend"
cd "$ROOT/frontend"
npm install
[ -f .env.local ] || { cp .env.local.example .env.local; echo "    สร้าง frontend/.env.local แล้ว"; }

echo "==> ฐานข้อมูล"
if psql -tAc "select 1 from pg_database where datname='hotline'" postgres 2>/dev/null | grep -q 1; then
  echo "    ฐานข้อมูล hotline มีอยู่แล้ว"
else
  createdb hotline && echo "    สร้างฐานข้อมูล hotline แล้ว"
fi

echo ""
echo "เสร็จแล้ว — เริ่มงานด้วย: ./scripts/dev.sh"
