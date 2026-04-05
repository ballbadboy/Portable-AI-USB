@echo off
title Portable AI - CLI-Anything Mode
color 0B
set "USB=%~dp0"
set "VENV=%USB%cli-anything\venv"
set "SCRIPTS=%VENV%\Scripts"
set "OLLAMA_MODELS=%USB%ollama\data"

if not exist "%SCRIPTS%\cli-anything-ollama.exe" (
    echo. & echo  CLI ยังไม่ได้ติดตั้ง — รัน install-cli.ps1 ก่อน & echo.
    pause & exit /b
)

tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if errorlevel 1 (
    start "" /B "%USB%ollama\ollama.exe" serve
    timeout /t 3 >nul
)

:MENU
cls
echo.
echo  +========================================================+
echo  ^|        Portable AI -- CLI-Anything Edition            ^|
echo  +========================================================^|
echo  ^|  AI & Models                                          ^|
echo  ^|  [1] ollama        -- จัดการ model + chat             ^|
echo  ^|  [2] anygen        -- สร้าง slides, docs ด้วย AI     ^|
echo  +--------------------------------------------------------+
echo  ^|  เอกสาร & ความรู้                                     ^|
echo  ^|  [3] libreoffice   -- Writer, Calc, Impress           ^|
echo  ^|  [4] joplin        -- Note-taking                     ^|
echo  ^|  [5] jupyterlab    -- Notebook + data analysis        ^|
echo  +--------------------------------------------------------+
echo  ^|  Diagram                                              ^|
echo  ^|  [6] plantuml      -- UML diagrams จาก text           ^|
echo  +--------------------------------------------------------+
echo  ^|  Web & Dev                                            ^|
echo  ^|  [7] browser       -- Browser automation              ^|
echo  ^|  [8] gitea         -- Git server management           ^|
echo  +--------------------------------------------------------+
echo  ^|  ประชุม                                               ^|
echo  ^|  [9] meeting       -- บันทึก แปล สรุปประชุม           ^|
echo  +--------------------------------------------------------+
echo  ^|  [U] UI  -- เปิด chat.html   [Q] ออก                 ^|
echo  +========================================================+
echo.
set /p CHOICE="  เลือก: "

call "%SCRIPTS%\activate.bat" >nul 2>&1

if "%CHOICE%"=="1" ( cls & echo  Ollama REPL & cli-anything-ollama & goto AFTER )
if "%CHOICE%"=="2" ( cls & echo  AnyGen & cli-anything-anygen & goto AFTER )
if "%CHOICE%"=="3" ( cls & echo  LibreOffice & cli-anything-libreoffice & goto AFTER )
if "%CHOICE%"=="4" ( cls & echo  Joplin & cli-anything-joplin & goto AFTER )
if "%CHOICE%"=="5" ( cls & echo  JupyterLab & cli-anything-jupyterlab & goto AFTER )
if "%CHOICE%"=="6" ( cls & echo  PlantUML & cli-anything-plantuml & goto AFTER )
if "%CHOICE%"=="7" ( cls & echo  Browser & cli-anything-browser & goto AFTER )
if "%CHOICE%"=="8" ( cls & echo  Gitea & cli-anything-gitea & goto AFTER )
if "%CHOICE%"=="9" ( cls & echo  Meeting & cli-anything-meeting & goto AFTER )
if /i "%CHOICE%"=="U" ( start "" "%USB%chat.html" & goto MENU )
if /i "%CHOICE%"=="Q" goto END
goto MENU

:AFTER
echo. & pause & goto MENU

:END
echo  ออกจาก CLI Mode
