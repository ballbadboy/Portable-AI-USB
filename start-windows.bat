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

:: Launch chat UI in browser
echo Starting Chat UI...
start "" "%~dp0chat.html"

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
