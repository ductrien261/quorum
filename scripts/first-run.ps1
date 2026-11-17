# Quorum - chay lan dau bang Docker (Windows PowerShell)
#   powershell -ExecutionPolicy Bypass -File scripts\first-run.ps1
# Tuy chon:
#   -BackfillFrom 2026-01-02   ngay bat dau chay mo hinh cho du lieu that
#   -NewsDays 14               so ngay tin CafeF can tai (0 = bo qua tin)
#   -SkipBuild                 khong build lai image
param(
    [string]$BackfillFrom = "2026-01-02",
    [int]$NewsDays = 14,
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Step([string]$Title, [string[]]$CliArgs) {
    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    docker compose exec -T api @CliArgs
    if ($LASTEXITCODE -ne 0) { throw "Loi o buoc: $Title" }
}

if (-not (Test-Path ".env")) { throw "Chua co file .env (copy .env.example thanh .env roi dien GEMINI_API_KEY)" }
if (-not (Test-Path "artifacts\vn\weights\model_seed0.pt")) { throw "Chua co artifacts\vn (xem artifacts\README.md)" }

docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker chua chay. Mo Docker Desktop, doi bieu tuong chuyen sang mau xanh roi chay lai." }

if ($SkipBuild) { docker compose up -d } else { docker compose up -d --build }
if ($LASTEXITCODE -ne 0) { throw "docker compose up that bai" }

Write-Host "Doi API khoi dong..." -NoNewline
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/health -TimeoutSec 3 | Out-Null; $ok = $true; break }
    catch { Start-Sleep -Seconds 3; Write-Host "." -NoNewline }
}
Write-Host ""
if (-not $ok) { throw "API khong phan hoi. Xem log: docker compose logs api" }

Step "Kiem tra mo hinh khop ket qua Kaggle" @("python", "-m", "pytest", "-q", "tests/test_model.py")
Step "Nap 243 phien kiem dinh 2025 (khoang 1-2 phut)" @("python", "-m", "app.cli", "seed-history")
Step "Tai gia 78 ma + VN-Index tu KBS (khoang 2 phut)" @("python", "-m", "app.cli", "prices")
if ($NewsDays -gt 0) {
    $from = (Get-Date).AddDays(-$NewsDays).ToString("yyyy-MM-dd")
    Step "Tai tin CafeF tu $from va nhung PhoBERT (lau nhat, co the 20-60 phut)" @("python", "-m", "app.cli", "news", "--from", $from)
}
Step "Chay mo hinh cho tung phien tu $BackfillFrom" @("python", "-m", "app.cli", "backfill", "--from", $BackfillFrom)

Write-Host ""
Write-Host "Xong. Mo http://localhost:3000" -ForegroundColor Green
Write-Host "Moi ngay 16:30 container tu cap nhat (may va Docker Desktop can dang bat)."
