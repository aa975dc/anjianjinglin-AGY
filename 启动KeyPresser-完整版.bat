@echo off
rem ===================================================================
rem  KeyPresser - FULL interface (advanced features)
rem  Recording, diagnostics, profiles, send modes, per-step editor.
rem  Content kept ASCII-only on purpose (safe under any codepage).
rem  Interpreter lookup order:
rem    1) pyw.exe -3   (official Python windowed launcher, no console)
rem    2) pythonw.exe  (taken from PATH)
rem    3) error + install hint
rem ===================================================================

setlocal
set "APPDIR=%~dp0KeyPresser"

rem --- Preferred: the official Python windowed launcher --------------
where pyw.exe >nul 2>nul
if %errorlevel%==0 (
  start "" pyw.exe -3 "%APPDIR%\main.py" full
  goto :eof
)

rem --- Fallback: pythonw.exe from PATH ------------------------------
for %%I in (pythonw.exe) do set "PYW=%%~$PATH:I"
if defined PYW (
  start "" "%PYW%" "%APPDIR%\main.py" full
  goto :eof
)

echo [ERROR] No Python interpreter found. Install Python 3.11+ and retry.
pause
exit /b 1
