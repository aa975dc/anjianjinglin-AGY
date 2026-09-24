@echo off
rem KeyPresser - launch elevated (needed when the game itself runs as admin)
set "APPDIR=%~dp0"
powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath 'pythonw.exe' -ArgumentList '\"%APPDIR%main.py\"'"
