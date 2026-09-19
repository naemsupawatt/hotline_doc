# เปิด backend + frontend พร้อมกัน คนละหน้าต่าง
# วิธีรัน:  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
$root = Split-Path $PSScriptRoot -Parent

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "chcp 65001 > `$null; `$env:PYTHONIOENCODING='utf-8'; Set-Location '$root\backend'; uv run uvicorn app.main:app --reload --port 8000"
)

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\frontend'; npm run dev"
)

Write-Host ""
Write-Host "  Frontend    http://localhost:3000" -ForegroundColor Green
Write-Host "  API docs    http://localhost:8000/docs   <- เปิดหน้านี้โชว์กรรมการได้เลย" -ForegroundColor Green
Write-Host "  Health      http://localhost:8000/health" -ForegroundColor DarkGray
