@echo off
rem Revision 1.0.0 - Pull GitHub script catalog to local A: drive
setlocal
set "ROOT=%~dp0"
set "MIRROR=%ROOT%..\Riverview-Git"
set "SOURCE=%MIRROR%\docs\operations\script-catalog"
if not exist "%MIRROR%\.git" (
 echo ERROR: Git mirror missing. Expected "%MIRROR%"
 exit /b 2
)
git -C "%MIRROR%" pull --ff-only
if errorlevel 1 exit /b 1
if not exist "%SOURCE%\scripts.json" (echo ERROR: GitHub registry missing& exit /b 3)
copy /Y "%SOURCE%\scripts.json" "%ROOT%scripts.json" >nul
copy /Y "%SOURCE%\README.md" "%ROOT%README.md" >nul
copy /Y "%SOURCE%\Run.bat" "%ROOT%Run.bat" >nul
if not exist "%ROOT%help" mkdir "%ROOT%help"
xcopy /Y /I "%SOURCE%\help\*.md" "%ROOT%help\" >nul
echo Catalog pull completed. Existing PowerShell scripts were not overwritten.
exit /b 0
