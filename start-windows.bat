@echo off
title Portable AI - Gemma 4 Launcher
color 0A

echo ===================================================
echo     Portable AI - Gemma 4 E2B + E4B Edition
echo ===================================================
echo.

:: Read active model from config file
set "CONFIG=%~dp0active-model.txt"
set "ACTIVE_MODEL=gemma4:e4b"
if exist "%CONFIG%" (
    set /p ACTIVE_MODEL=<"%CONFIG%"
)

:: Model selection menu
echo   Current model: %ACTIVE_MODEL%
echo.
echo   [1] gemma4:e2b  - Fast, works on any machine (1.5 GB RAM)
echo   [2] gemma4:e4b  - Better quality, needs 8 GB RAM
echo   [3] Keep current (%ACTIVE_MODEL%)
echo.
set /p CHOICE="  Select model (1/2/3, or Enter to keep current): "

if "%CHOICE%"=="1" (
    set "ACTIVE_MODEL=gemma4:e2b"
    echo gemma4:e2b>"%CONFIG%"
    echo   Switched to gemma4:e2b
)
if "%CHOICE%"=="2" (
    set "ACTIVE_MODEL=gemma4:e4b"
    echo gemma4:e4b>"%CONFIG%"
    echo   Switched to gemma4:e4b
)

echo.
echo   Starting with: %ACTIVE_MODEL%
echo.

:: Set Ollama model data path to the USB drive
set "OLLAMA_MODELS=%~dp0ollama\data"

:: Override APPDATA so AnythingLLM saves ALL data on the USB (not on host PC!)
set "APPDATA=%~dp0anythingllm_data"
set "STORAGE_DIR=%~dp0anythingllm_data"

:: Start Ollama Engine
echo Starting Ollama Engine...
start "" /B "%~dp0ollama\ollama.exe" serve
timeout /t 3 >nul

:: Pre-load selected model into memory
echo Loading %ACTIVE_MODEL% into memory...
start "" /B "%~dp0ollama\ollama.exe" run %ACTIVE_MODEL% ""
timeout /t 3 >nul

:: Find and launch AnythingLLM
echo Starting AnythingLLM Interface...

if exist "%~dp0anythingllm\AnythingLLM.exe" (
    set "APP_PATH=%~dp0anythingllm\AnythingLLM.exe"
    goto LaunchApp
)
if exist "%~dp0anythingllm_app\AnythingLLM.exe" (
    set "APP_PATH=%~dp0anythingllm_app\AnythingLLM.exe"
    goto LaunchApp
)

echo.
echo First time Windows Setup: Extracting AnythingLLM to USB...
echo (This will take 1-3 minutes depending on your USB speed!)
echo Please wait patiently and do not close this window...

taskkill /F /IM "AnythingLLM.exe" /IM "AnythingLLMDesktop.exe" >nul 2>&1

if exist "%~dp0anythingllm\AnythingLLM_Installer.exe" (
    start /wait "" "%~dp0anythingllm\AnythingLLM_Installer.exe" /CURRENTUSER /S /D=%~sdp0anythingllm_app
) else if exist "%~dp0anythingllm\AnythingLLMDesktop.exe" (
    start /wait "" "%~dp0anythingllm\AnythingLLMDesktop.exe" /CURRENTUSER /S /D=%~sdp0anythingllm_app
) else (
    echo.
    echo ERROR: AnythingLLM was not found on this USB drive!
    echo Please run install.bat first to download everything.
    echo.
    pause
    exit /b
)

set WaitCount=0
:WaitLoop
if exist "%~dp0anythingllm_app\AnythingLLM.exe" (
    set "APP_PATH=%~dp0anythingllm_app\AnythingLLM.exe"
    goto LaunchApp
)
if %WaitCount% geq 24 goto LaunchFail
timeout /t 5 >nul
set /a WaitCount+=1
goto WaitLoop

:LaunchFail
echo.
echo ERROR: AnythingLLM failed to extract!
echo Please cancel the script, manually extract AnythingLLMDesktop.exe, and try again!
echo.
pause
exit /b

:LaunchApp
start "" "%APP_PATH%"

:Running
echo.
echo ===================================================
echo   SYSTEM ONLINE: %ACTIVE_MODEL% running from USB!
echo ===================================================
echo.
echo   To switch model: restart and pick a different option
echo   Keep this window open to keep the AI running!
echo.
echo Press any key to SHUT DOWN the AI safely...
echo.
pause

:: Clean shutdown
taskkill /F /IM "ollama.exe" >nul 2>&1
taskkill /F /IM "AnythingLLM.exe" >nul 2>&1
echo.
echo AI Engine shut down. You may safely eject the USB.
timeout /t 3 >nul
