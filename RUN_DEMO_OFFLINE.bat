@echo off
setlocal
cd /d "%~dp0"
title Meridian Insights - Sprint 1 Demo
set "PY=runtime\python.exe"
%PY% -c "import pandas, pytest" >nul 2>&1 && goto run
set "PY=python"
%PY% -c "import pandas, pytest" >nul 2>&1 && goto run
set "PY=py"
%PY% -c "import pandas, pytest" >nul 2>&1 && goto run
echo.
echo  Could not start Python with pandas + pytest.
echo  The bundled runtime folder may be missing, or this PC blocks it.
echo  Fix: install Python 3.10+ and run:  pip install pandas pytest yfinance
echo.
pause
exit /b 1
:run
%PY% -B demo.py --offline %*
echo.
pause
