# ================================================================
# PORTABLE AI - CLI-ANYTHING SETUP (Windows)
# ติดตั้ง CLI harnesses: ollama, browser, libreoffice
# ================================================================

$USB = Split-Path -Parent $MyInvocation.MyCommand.Path
$CLI_DIR = "$USB\cli-anything"
$VENV = "$CLI_DIR\venv"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CLI-Anything Setup for Portable AI USB (Windows)       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/4] ตรวจสอบ Python..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Host "      ERROR: ไม่พบ Python 3.10+ กรุณาติดตั้งก่อน" -ForegroundColor Red
    Write-Host "      https://python.org/downloads" -ForegroundColor Gray
    pause; exit 1
}
$pyVer = & $py.Source --version 2>&1
Write-Host "      พบ: $pyVer" -ForegroundColor Green

# Create venv on USB
Write-Host ""
Write-Host "[2/4] สร้าง Python venv บน USB..." -ForegroundColor Yellow
if (Test-Path "$VENV\Scripts\python.exe") {
    Write-Host "      venv มีอยู่แล้ว ข้าม..." -ForegroundColor Green
} else {
    & $py.Source -m venv $VENV
    Write-Host "      สร้าง venv สำเร็จ" -ForegroundColor Green
}

$PIP = "$VENV\Scripts\pip.exe"
$PYTHON = "$VENV\Scripts\python.exe"

# Upgrade pip
& $PIP install --quiet --upgrade pip

# Install harnesses
Write-Host ""
Write-Host "[3/4] ติดตั้ง CLI harnesses..." -ForegroundColor Yellow

Write-Host "      ollama CLI..." -ForegroundColor Magenta
& $PIP install --quiet -e "$CLI_DIR\ollama"
Write-Host "      ollama CLI OK" -ForegroundColor Green

Write-Host "      browser CLI..." -ForegroundColor Magenta
& $PIP install --quiet -e "$CLI_DIR\browser"
Write-Host "      browser CLI OK" -ForegroundColor Green

Write-Host "      libreoffice CLI..." -ForegroundColor Magenta
& $PIP install --quiet -e "$CLI_DIR\libreoffice"
Write-Host "      libreoffice CLI OK" -ForegroundColor Green

# Verify
Write-Host ""
Write-Host "[4/4] ตรวจสอบการติดตั้ง..." -ForegroundColor Yellow
$SCRIPTS = "$VENV\Scripts"
$ok = 0
foreach ($cmd in @("cli-anything-ollama", "cli-anything-browser", "cli-anything-libreoffice")) {
    if (Test-Path "$SCRIPTS\$cmd.exe") {
        Write-Host "      ✓ $cmd" -ForegroundColor Green
        $ok++
    } else {
        Write-Host "      ✗ $cmd ไม่พบ" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
if ($ok -eq 3) {
    Write-Host "   CLI-Anything พร้อมใช้งาน! ($ok/3 CLIs)              " -ForegroundColor Green
    Write-Host "   รัน start-cli.bat เพื่อเปิด REPL                     " -ForegroundColor White
} else {
    Write-Host "   ติดตั้งบางส่วนไม่สำเร็จ ($ok/3) กรุณาตรวจสอบ        " -ForegroundColor Yellow
}
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
pause
