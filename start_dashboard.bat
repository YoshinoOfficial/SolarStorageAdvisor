@echo off
setlocal

set "ROOT=%~dp0"
set "URL=http://127.0.0.1:5000/dashboard"

cd /d "%ROOT%"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found.
    echo Please install Python or add it to PATH, then run this script again.
    echo.
    pause
    exit /b 1
)

call :check_server
if not errorlevel 1 goto open_dashboard

echo Starting Flask server...
start "SolarStorageAdvisor Flask" cmd /k "cd /d ""%ROOT%"" && python web\app.py"

echo Waiting for dashboard service at %URL% ...
for /l %%i in (1,1,20) do (
    timeout /t 1 /nobreak >nul
    call :check_server
    if not errorlevel 1 goto open_dashboard
)

echo.
echo [ERROR] Dashboard service did not become available within 20 seconds.
echo Check the Flask server window for errors, then try again.
echo.
pause
exit /b 1

:open_dashboard
echo Opening %URL% ...
start "" "%URL%"
exit /b 0

:check_server
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri '%URL%' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
exit /b %ERRORLEVEL%
