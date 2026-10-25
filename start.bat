@echo off
setlocal
cd /d "%~dp0"

rem Prefer the Python launcher; fall back to "python" when it is not installed.
where py >nul 2>nul
if errorlevel 1 (
  set "PYTHON=python"
) else (
  set "PYTHON=py"
)

%PYTHON% site\server.py --open
if errorlevel 1 (
  echo.
  echo DSTMeta could not start. Install Python 3.8 or newer and try again.
  pause
)

endlocal
