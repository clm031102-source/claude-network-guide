@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m app.server %*
  goto end
)
where python >nul 2>nul
if not errorlevel 1 (
  python -m app.server %*
  goto end
)
echo Please install Python 3.10 or later from https://www.python.org/downloads/
:end
if errorlevel 1 pause
endlocal
