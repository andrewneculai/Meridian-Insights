@echo off
setlocal
cd /d "%~dp0"
title Meridian Insights - Sprint 2
set "PY=runtime\python.exe"
%PY% -c "import pandas, flask, pytest" >nul 2>&1 && goto run
set "PY=python"
%PY% -c "import pandas, flask, pytest" >nul 2>&1 && goto run
set "PY=py"
%PY% -c "import pandas, flask, pytest" >nul 2>&1 && goto run
echo.
echo  Could not start Python with pandas + Flask + pytest.
echo  The bundled runtime folder may be missing, or this PC blocks it.
echo  Fix: install Python 3.10+ and run:  pip install -r requirements.txt
echo.
pause
exit /b 1
:run
echo Starting the dashboard... a browser tab will open. Close this window to stop it.
%PY% -B app.py %*
pause
