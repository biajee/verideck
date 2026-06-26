@echo off
REM Double-clickable launcher for the Verideck Windows installer.
REM Runs the PowerShell script next to this file, bypassing execution policy.
echo Starting the Verideck installer...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows.ps1"
echo.
pause
