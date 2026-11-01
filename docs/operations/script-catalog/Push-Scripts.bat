@echo off
rem Revision 1.0.0 - Push reviewed local catalog edits to GitHub
setlocal
set "ROOT=%~dp0"
set "MIRROR=%ROOT%..\Riverview-Git"
set "DEST=%MIRROR%\docs\operations\script-catalog"
if not exist "%MIRROR%\.git" (echo ERROR: Git mirror missing& exit /b 2)
git -C "%MIRROR%" pull --ff-only
if errorlevel 1 exit /b 1
copy /Y "%ROOT%scripts.json" "%DEST%\scripts.json" >nul
copy /Y "%ROOT%README.md" "%DEST%\README.md" >nul
copy /Y "%ROOT%Run.bat" "%DEST%\Run.bat" >nul
if not exist "%DEST%\help" mkdir "%DEST%\help"
xcopy /Y /I "%ROOT%help\*.md" "%DEST%\help\" >nul
git -C "%MIRROR%" add -- docs/operations/script-catalog
git -C "%MIRROR%" diff --cached --check
if errorlevel 1 exit /b 3
git -C "%MIRROR%" diff --cached --stat
git -C "%MIRROR%" diff --cached --quiet
if not errorlevel 1 (echo Nothing to push& exit /b 0)
git -C "%MIRROR%" commit -m "Sync Riverview script catalog from Windows"
if errorlevel 1 exit /b 4
git -C "%MIRROR%" push
exit /b %ERRORLEVEL%
