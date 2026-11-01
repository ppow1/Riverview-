@echo off
rem Riverview script launcher revision 1.0.0
if /I "%~1"=="list" (echo Deploy-R3& exit /b 0)
if /I "%~1"=="help" (if /I "%~2"=="Deploy-R3" (type "%~dp0help\Deploy-R3.md"& exit /b 0))
if /I not "%~1"=="Deploy-R3" (echo Unknown command& exit /b 2)
if "%~2"=="" (echo Commit required& exit /b 2)
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0Deploy-R3.ps1" -Commit "%~2"
exit /b %ERRORLEVEL%
