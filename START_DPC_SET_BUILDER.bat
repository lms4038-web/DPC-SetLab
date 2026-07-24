@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo =============================================
echo        DPC DJ Set Builder - Windows
echo =============================================
echo.

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py"

if not defined PY_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD goto no_python

echo Python command: %PY_CMD%
%PY_CMD% --version
if errorlevel 1 goto error

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [1/3] Creating the local Python environment...
    %PY_CMD% -m venv .venv
    if errorlevel 1 goto error
) else (
    echo.
    echo [1/3] Existing Python environment found.
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error

echo [2/3] Installing or checking required packages...
python -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto error

if not exist "config.json" (
    copy /Y "config.example.json" "config.json" >nul
)

echo [3/3] Starting DPC DJ Set Builder...
echo Your browser should open automatically.
echo Keep this window open while using the app.
echo.
python -m streamlit run app.py
if errorlevel 1 goto error

goto end

:no_python
echo.
echo ERROR: Python was not found.
echo Install Python 3.10 or newer and enable "Add python.exe to PATH".
echo Then close this window and run this file again.
echo.
pause
exit /b 1

:error
echo.
echo ERROR: Installation or startup failed.
echo Please copy the last error messages and send them for diagnosis.
echo.
pause
exit /b 1

:end
endlocal
