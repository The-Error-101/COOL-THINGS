@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PYCMD=py
) else (
    set PYCMD=python
)

echo Installing Python packaging tools...
%PYCMD% -m pip install --upgrade pip pyinstaller

set ICON_FLAG=
if exist "%~dp0cp.ico" (
    set ICON_FLAG=--icon "%~dp0cp.ico"
)

echo Building executable...
%PYCMD% -m PyInstaller --clean --onefile --name CP %ICON_FLAG% "CP.py"

if exist "dist\CP.exe" (
    echo.
    echo SUCCESS: CP.exe was created in the dist folder.
    echo Creating desktop and Start menu shortcuts...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_shortcut.ps1"
    echo.
    echo Done.
) else (
    echo.
    echo BUILD FAILED: check Python and PyInstaller output above.
)

pause
