@echo off
title Portable AI - CLI Mode
color 0B

set "USB=%~dp0"
set "VENV=%USB%cli-anything\venv"
set "SCRIPTS=%VENV%\Scripts"
set "OLLAMA_MODELS=%USB%ollama\data"

:: Check if CLI is installed
if not exist "%SCRIPTS%\cli-anything-ollama.exe" (
    echo.
    echo  CLI-Anything ยังไม่ได้ติดตั้ง
    echo  กรุณารัน install-cli.ps1 ก่อน
    echo.
    pause
    exit /b
)

:: Start Ollama in background (if not running)
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if errorlevel 1 (
    echo  กำลังเริ่ม Ollama engine...
    start "" /B "%USB%ollama\ollama.exe" serve
    timeout /t 3 >nul
)

cls
echo.
echo  ██████╗ ██████╗ ██████╗ ████████╗ █████╗ ██████╗ ██╗     ███████╗
echo  ██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗██║     ██╔════╝
echo  ██████╔╝██║   ██║██████╔╝   ██║   ███████║██████╔╝██║     █████╗
echo  ██╔═══╝ ██║   ██║██╔══██╗   ██║   ██╔══██║██╔══██╗██║     ██╔══╝
echo  ██║     ╚██████╔╝██║  ██║   ██║   ██║  ██║██████╔╝███████╗███████╗
echo  ╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝
echo.
echo  Portable AI - CLI-Anything Mode
echo  ═══════════════════════════════════════════
echo.
echo  [1] ollama      — จัดการ model และ chat
echo  [2] browser     — ควบคุม browser อัตโนมัติ
echo  [3] libreoffice — สร้างและแก้ไขเอกสาร
echo  [4] UI (chat)   — เปิด chat.html ใน browser
echo  [Q] ออก
echo.
set /p CHOICE="  เลือก (1/2/3/4/Q): "

if /i "%CHOICE%"=="1" goto OLLAMA
if /i "%CHOICE%"=="2" goto BROWSER
if /i "%CHOICE%"=="3" goto LIBREOFFICE
if /i "%CHOICE%"=="4" goto UI
if /i "%CHOICE%"=="Q" goto END
goto END

:OLLAMA
cls
echo  ── Ollama REPL ─────────────────────────────────────────────
echo  พิมพ์ help เพื่อดูคำสั่ง, Ctrl+C เพื่อออก
echo  ────────────────────────────────────────────────────────────
echo.
call "%SCRIPTS%\activate.bat"
cli-anything-ollama
goto MENU_AGAIN

:BROWSER
cls
echo  ── Browser Automation REPL ─────────────────────────────────
echo  ต้องการ DOMShell: npx @apireno/domshell
echo  ────────────────────────────────────────────────────────────
echo.
call "%SCRIPTS%\activate.bat"
cli-anything-browser
goto MENU_AGAIN

:LIBREOFFICE
cls
echo  ── LibreOffice REPL ─────────────────────────────────────────
echo  ต้องการ LibreOffice ติดตั้งในเครื่อง
echo  ────────────────────────────────────────────────────────────
echo.
call "%SCRIPTS%\activate.bat"
cli-anything-libreoffice
goto MENU_AGAIN

:UI
start "" "%USB%chat.html"
goto MENU_AGAIN

:MENU_AGAIN
echo.
echo  กด Enter เพื่อกลับเมนู...
pause >nul
goto START_MENU

:START_MENU
call start-cli.bat

:END
echo  ออกจาก CLI Mode
