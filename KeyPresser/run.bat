@echo off
rem KeyPresser - launch without console window
set "APPDIR=%~dp0"
where pythonw.exe >nul 2>nul && (
  start "" pythonw.exe "%APPDIR%main.py"
) || (
  start "" py.exe -3 "%APPDIR%main.py"
)
