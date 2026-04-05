# ================================================================
# PORTABLE AI - AUTOMATED USB SETUP SCRIPT
# Gemma 4 E2B + E4B Dual-Model Edition
# ================================================================

$USB_Drive = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Starting Automated Portable AI USB Setup!              " -ForegroundColor Cyan
Write-Host "   Gemma 4 E2B + E4B Dual-Model Edition                  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------
# STEP 1: Create folder structure
# -----------------------------------------------------------------
Write-Host "[1/4] Creating folders on USB drive..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$USB_Drive\ollama" | Out-Null
New-Item -ItemType Directory -Force -Path "$USB_Drive\ollama\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$USB_Drive\anythingllm" | Out-Null
New-Item -ItemType Directory -Force -Path "$USB_Drive\anythingllm_data\anythingllm-desktop" | Out-Null
Write-Host "      Done." -ForegroundColor Green

# -----------------------------------------------------------------
# STEP 2: Download Ollama (the AI engine)
# -----------------------------------------------------------------
Write-Host ""
Write-Host "[2/4] Downloading Ollama AI Engine..." -ForegroundColor Yellow
$OllamaURL = "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip"
$OllamaDest = "$USB_Drive\ollama\ollama-windows-amd64.zip"
if (Test-Path "$USB_Drive\ollama\ollama.exe") {
    Write-Host "      Ollama already installed! Skipping..." -ForegroundColor Green
} else {
    curl.exe -L --progress-bar $OllamaURL -o $OllamaDest
    Write-Host "      Extracting Ollama..." -ForegroundColor Yellow
    Expand-Archive -Path $OllamaDest -DestinationPath "$USB_Drive\ollama" -Force
    Remove-Item $OllamaDest -Force
    Write-Host "      Ollama Setup Complete!" -ForegroundColor Green
}

# -----------------------------------------------------------------
# STEP 3: Download Gemma 4 E2B + E4B via Ollama
# -----------------------------------------------------------------
Write-Host ""
Write-Host "[3/4] Downloading Gemma 4 Models..." -ForegroundColor Yellow
Write-Host "      E2B (~1.5 GB) - fast, works on any machine" -ForegroundColor Magenta
Write-Host "      E4B (~5 GB)   - better quality, needs 8 GB RAM" -ForegroundColor Magenta
Write-Host ""

$env:OLLAMA_MODELS = "$USB_Drive\ollama\data"
New-Item -ItemType Directory -Force -Path $env:OLLAMA_MODELS | Out-Null

# Start Ollama temporarily to pull models
Write-Host "      Starting Ollama to download models..." -ForegroundColor DarkGray
$ServerProcess = Start-Process -FilePath "$USB_Drive\ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 5

# Pull E2B
$existingModels = & "$USB_Drive\ollama\ollama.exe" list 2>&1
if ($existingModels -match "gemma4:e2b") {
    Write-Host "      gemma4:e2b already downloaded! Skipping..." -ForegroundColor Green
} else {
    Write-Host "      Downloading gemma4:e2b..." -ForegroundColor Yellow
    & "$USB_Drive\ollama\ollama.exe" pull gemma4:e2b
    Write-Host "      gemma4:e2b ready!" -ForegroundColor Green
}

# Pull E4B
$existingModels = & "$USB_Drive\ollama\ollama.exe" list 2>&1
if ($existingModels -match "gemma4:e4b") {
    Write-Host "      gemma4:e4b already downloaded! Skipping..." -ForegroundColor Green
} else {
    Write-Host "      Downloading gemma4:e4b..." -ForegroundColor Yellow
    & "$USB_Drive\ollama\ollama.exe" pull gemma4:e4b
    Write-Host "      gemma4:e4b ready!" -ForegroundColor Green
}

# Stop temporary server
Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
Write-Host "      All models downloaded!" -ForegroundColor Green

# Save default active model
if (-Not (Test-Path "$USB_Drive\active-model.txt")) {
    Set-Content -Path "$USB_Drive\active-model.txt" -Value "gemma4:e4b"
}

# -----------------------------------------------------------------
# STEP 4: Download AnythingLLM (the chat interface)
# -----------------------------------------------------------------
Write-Host ""
Write-Host "[4/4] Downloading AnythingLLM Chat Interface..." -ForegroundColor Yellow
$AnythingLLMURL = "https://cdn.anythingllm.com/latest/AnythingLLMDesktop.exe"
$InstallerDest = "$USB_Drive\anythingllm\AnythingLLMDesktop.exe"

if (Test-Path "$USB_Drive\anythingllm\AnythingLLM.exe") {
    Write-Host "      AnythingLLM already set up! Skipping..." -ForegroundColor Green
} else {
    if (-Not (Test-Path $InstallerDest) -or (Get-Item $InstallerDest).length -lt 10000000) {
        Write-Host "      Downloading installer..." -ForegroundColor Magenta
        curl.exe -L --progress-bar $AnythingLLMURL -o $InstallerDest
    }
    Write-Host "      Extracting AnythingLLM to USB (this takes 1-2 minutes)..." -ForegroundColor Magenta
    $ShortPath = (New-Object -ComObject Scripting.FileSystemObject).GetFolder($USB_Drive).ShortPath
    $ExtractDir = "$ShortPath\anythingllm"
    Start-Process -FilePath $InstallerDest -ArgumentList "/S /D=$ExtractDir" -Wait
    if (Test-Path "$USB_Drive\anythingllm\AnythingLLM.exe") {
        Remove-Item $InstallerDest -Force -ErrorAction SilentlyContinue
        Write-Host "      AnythingLLM extracted and ready!" -ForegroundColor Green
    } else {
        Write-Host "      AnythingLLM installer downloaded. Will extract on first launch." -ForegroundColor Yellow
    }
}

# -----------------------------------------------------------------
# ALL DONE!
# -----------------------------------------------------------------
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   SETUP COMPLETE! YOUR PORTABLE AI IS READY!             " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Models installed: gemma4:e2b + gemma4:e4b" -ForegroundColor White
Write-Host "  Default model: gemma4:e4b (change in active-model.txt)" -ForegroundColor White
Write-Host ""
Write-Host "  To start your AI: Double-click start-windows.bat" -ForegroundColor White
Write-Host "  On a Mac: Double-click start-mac.command" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to close this installer..." -ForegroundColor Yellow
$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null
