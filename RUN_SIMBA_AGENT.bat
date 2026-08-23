@echo off
setlocal
cd /d "%~dp0"
set "SIMBA_DEMO_MODE=1"
set "SIMBA_AGENT_PROVIDER=mock"
set "SIMBA_CONTROL_MODE=simulation"
set "SIMBA_CONTROL_ALLOW_LIVE=0"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\run_demo.py
  goto :end
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 scripts\run_demo.py
  goto :end
)

where python >nul 2>nul
if not errorlevel 1 (
  python scripts\run_demo.py
  goto :end
)

echo SIMBA could not find Python 3.
echo Install Python 3.10 or newer, then run INSTALL_SIMBA_AGENT.bat.
pause
exit /b 1

:end
if errorlevel 1 pause
endlocal
