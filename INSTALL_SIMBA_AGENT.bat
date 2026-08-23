@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_COMMAND="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_COMMAND=py -3"

if not defined PYTHON_COMMAND (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_COMMAND=python"
)

if not defined PYTHON_COMMAND (
  echo SIMBA could not find Python 3.
  echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

%PYTHON_COMMAND% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
  echo SIMBA requires Python 3.10 or newer.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" %PYTHON_COMMAND% -m venv .venv
if errorlevel 1 goto :failed

echo Installing the lightweight local application...
".venv\Scripts\python.exe" -m pip install -r requirements-ubuntu-agent.txt
if errorlevel 1 goto :failed

".venv\Scripts\python.exe" scripts\adtc_preflight.py --allow-placeholders --development-tree
if errorlevel 1 goto :failed

echo.
echo Setup complete. Double-click RUN_SIMBA_AGENT.bat.
pause
exit /b 0

:failed
echo.
echo Setup did not complete. Check the message above and your internet connection.
pause
exit /b 1
