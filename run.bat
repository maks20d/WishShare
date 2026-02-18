@echo off
setlocal EnableExtensions
chcp 65001 >nul

if not defined RUN_BAT_INVOKED (
  set "RUN_BAT_INVOKED=1"
  %ComSpec% /d /c ""%~f0""
  exit /b
)

set "ROOT=%~dp0"
set "COMPOSE_CMD="

color 0A
:menu
cls
call :resolve_compose
echo.
echo Welcome to WishShare
echo Путь проекта: %ROOT%
echo.
echo =====================================
echo          WishShare Launcher
echo =====================================
echo [1] Dev Run (Backend + Frontend)
echo [2] Dev Backend Only
echo [3] Dev Frontend Only
echo [4] Build Frontend (Production)
echo [5] Docker Up (Dev)
echo [6] Docker Up (Production)
echo [7] Docker Up (Production + Nginx)
echo [8] Docker Logs
echo [9] Docker Stop
echo [T] Cloudflare Tunnel
echo [Q] Quit
echo.
choice /c 123456789TQ /n /m "Select option: "
if errorlevel 11 goto end
if errorlevel 10 goto tunnel
if errorlevel 9 goto docker_stop
if errorlevel 8 goto docker_logs
if errorlevel 7 goto docker_prod_nginx
if errorlevel 6 goto docker_prod
if errorlevel 5 goto docker_dev
if errorlevel 4 goto build_frontend
if errorlevel 3 goto dev_frontend
if errorlevel 2 goto dev_backend
if errorlevel 1 goto devrun

:devrun
call :ensure_python || goto end
call :ensure_node || goto end
call :setup_venv || goto end
start "" cmd /c "cd /d ""%ROOT%backend"" && ""%VENV_PY%"" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
start "" cmd /c "cd /d ""%ROOT%frontend"" && npm run dev"
timeout /t 4 /nobreak >nul
start "" "http://localhost:3000"
echo WishShare started: http://localhost:3000
pause
goto end

:dev_backend
call :ensure_python || goto end
call :setup_venv || goto end
start "" cmd /c "cd /d ""%ROOT%backend"" && ""%VENV_PY%"" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo Backend started: http://localhost:8000
pause
goto end

:dev_frontend
call :ensure_node || goto end
if not exist "%ROOT%frontend\node_modules" (
  pushd "%ROOT%frontend"
  npm install
  popd
)
start "" cmd /c "cd /d ""%ROOT%frontend"" && npm run dev"
timeout /t 2 /nobreak >nul
start "" "http://localhost:3000"
echo Frontend started: http://localhost:3000
pause
goto end

:build_frontend
call :ensure_node || goto end
pushd "%ROOT%frontend"
npm install
npm run build
popd
echo Frontend build completed.
pause
goto end

:docker_dev
call :ensure_docker || goto end
call %COMPOSE_CMD% -f "%ROOT%docker-compose.dev.yml" up -d --build
pause
goto end

:docker_prod
call :ensure_docker || goto end
call %COMPOSE_CMD% -f "%ROOT%docker-compose.yml" up -d --build
pause
goto end

:docker_prod_nginx
call :ensure_docker || goto end
call %COMPOSE_CMD% -f "%ROOT%docker-compose.yml" --profile production up -d --build
pause
goto end

:docker_logs
call :ensure_docker || goto end
call %COMPOSE_CMD% -f "%ROOT%docker-compose.yml" logs -f
pause
goto end

:docker_stop
call :ensure_docker || goto end
call %COMPOSE_CMD% -f "%ROOT%docker-compose.yml" down
pause
goto end

:tunnel
call :ensure_cloudflared || goto end
start "" cmd /c "cloudflared tunnel --url http://localhost:3000"
pause
goto end

:ensure_python
where python >nul 2>&1
if errorlevel 1 (
  echo Python not found. Install Python 3.11 or newer.
  exit /b 1
)
exit /b 0

:ensure_node
where node >nul 2>&1
if errorlevel 1 (
  echo Node.js not found. Install Node.js 20 or newer.
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo npm not found. Install Node.js 20 or newer.
  exit /b 1
)
exit /b 0

:ensure_docker
where docker >nul 2>&1
if errorlevel 1 (
  echo Docker not found. Install Docker Desktop.
  exit /b 1
)
call :resolve_compose
if not defined COMPOSE_CMD (
  echo Docker Compose not found. Install Docker Compose or update Docker Desktop.
  exit /b 1
)
exit /b 0

:ensure_cloudflared
where cloudflared >nul 2>&1
if errorlevel 1 (
  echo cloudflared not found. Install Cloudflare Tunnel client.
  exit /b 1
)
exit /b 0

:setup_venv
if not exist "%ROOT%backend\.venv" (
  python -m venv "%ROOT%backend\.venv"
)
set "VENV_PY=%ROOT%backend\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  set "VENV_PY=%ROOT%backend\.venv\bin\python"
)
if not exist "%VENV_PY%" (
  echo Python in virtual environment not found.
  exit /b 1
)
"%VENV_PY%" -m pip install -r "%ROOT%backend\requirements.txt"
"%VENV_PY%" -m playwright install chromium
if not exist "%ROOT%frontend\node_modules" (
  pushd "%ROOT%frontend"
  npm install
  popd
)
exit /b 0

:resolve_compose
if defined COMPOSE_CMD exit /b 0
docker compose version >nul 2>&1
if not errorlevel 1 (
  set "COMPOSE_CMD=docker compose"
  exit /b 0
)
where docker-compose >nul 2>&1
if not errorlevel 1 (
  set "COMPOSE_CMD=docker-compose"
  exit /b 0
)
set "COMPOSE_CMD="
exit /b 0

:end
exit /b
