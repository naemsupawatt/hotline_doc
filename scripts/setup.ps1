# ติดตั้งครั้งแรกบนเครื่อง — รันครั้งเดียวตอนเริ่มงาน
# วิธีรัน:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

# คอนโซล Windows ค่าเริ่มต้นเป็น cp874/cp1252 ทำให้ print ภาษาไทยพัง
$env:PYTHONIOENCODING = "utf-8"
chcp 65001 > $null

Write-Host "==> ตรวจเครื่องมือที่ต้องมี" -ForegroundColor Cyan
foreach ($tool in @("node", "git", "uv", "psql")) {
    if (Get-Command $tool -ErrorAction SilentlyContinue) {
        Write-Host "    [ok]     $tool"
    } else {
        Write-Host "    [ขาด]    $tool" -ForegroundColor Yellow
    }
}
Write-Host ""
Write-Host "    ถ้ายังขาด ให้ติดตั้งด้วย:" -ForegroundColor DarkGray
Write-Host "      winget install astral-sh.uv" -ForegroundColor DarkGray
Write-Host "      winget install PostgreSQL.PostgreSQL.16" -ForegroundColor DarkGray
Write-Host ""

Write-Host "==> Backend: สร้าง venv (Python 3.13) และติดตั้ง dependencies" -ForegroundColor Cyan
Push-Location "$root\backend"
uv python install 3.13
uv venv --python 3.13
uv sync
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "    สร้าง backend\.env แล้ว" }
Pop-Location

Write-Host "==> Frontend: ติดตั้ง dependencies" -ForegroundColor Cyan
Push-Location "$root\frontend"
npm install
if (-not (Test-Path ".env.local")) { Copy-Item ".env.local.example" ".env.local"; Write-Host "    สร้าง frontend\.env.local แล้ว" }
Pop-Location

Write-Host "==> สร้างฐานข้อมูล hotline (ถ้ายังไม่มี)" -ForegroundColor Cyan
Write-Host "    รันคำสั่งนี้เองถ้ายังไม่ได้สร้าง:" -ForegroundColor DarkGray
Write-Host '      psql -U postgres -c "CREATE DATABASE hotline;"' -ForegroundColor DarkGray

Write-Host ""
Write-Host "เสร็จแล้ว — เริ่มงานด้วย: .\scripts\dev.ps1" -ForegroundColor Green
