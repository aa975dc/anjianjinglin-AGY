@echo off
rem Build KeyPresser.exe -- single portable file, no console window.
rem Requires: python -m pip install pyinstaller
setlocal
cd /d "%~dp0"

rem version.py + version_info.txt, version = build time in yyMMddHHmm
python make_version.py || goto :err
python make_icon.py || goto :err

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name KeyPresser --icon icon.ico --version-file version_info.txt ^
  main.py || goto :err

copy /y "run_admin_exe.bat" "dist\run_admin.bat" >nul
if not exist "dist\profiles" mkdir "dist\profiles"
copy /y "profiles\example.json" "dist\profiles\example.json" >nul

echo.
echo Done: dist\KeyPresser.exe
echo Tip: --onefile unpacks on every start (~1 s). For instant startup replace
echo      --onefile with --onedir above and ship the whole dist\KeyPresser folder.
goto :eof

:err
echo BUILD FAILED
exit /b 1
