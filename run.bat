@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "APP_VERSION=1.0.0"
set "ROOT=%~dp0"
set "COMPOSE_CMD="

:menu
cls
echo.
echo  ====================================================
echo          WishShare Launcher v%APP_VERSION%
echo  ====================================================
echo.
echo  [1] Dev Run (Backend + Frontend)
echo  [2] Backend Only
echo  [3] Frontend Only
echo  [4] Build Frontend (Production)
echo  ----------------------------------------------------
echo  [5] Docker Up (Dev)
echo  [6] Docker Up (Production)
echo  [7] Docker Up (Production + Nginx)
echo  [8] Docker Logs
echo  [9] Docker Stop
echo  ----------------------------------------------------
echo  [T] Cloudflare Tunnel
echo  [G] Generate JWT Secret Key
echo  [E] Setup .env File
echo  [C] Clean Cache
echo  [S] Check Ports Status
echo  [R] Run All Tests
echo  [H] Help
echo  ----------------------------------------------------
echo  [Q] Quit
echo  ====================================================
echo.
set /p "choice=Select option: "

if /i "%choice%"=="1" goto devrun
if /i "%choice%"=="2" goto dev_backend
if /i "%choice%"=="3" goto dev_frontend
if /i "%choice%"=="4" goto build_frontend
if /i "%choice%"=="5" goto docker_dev
if /i "%choice%"=="6" goto docker_prod
if /i "%choice%"=="7" goto docker_prod_nginx
if /i "%choice%"=="8" goto docker_logs
if /i "%choice%"=="9" goto docker_stop
if /i "%choice%"=="T" goto tunnel
if /i "%choice%"=="G" goto generate_jwt
if /i "%choice%"=="E" goto setup_env
if /i "%choice%"=="C" goto clean_cache
if /i "%choice%"=="S" goto check_ports
if /i "%choice%"=="R" goto run_tests
if /i "%choice%"=="H" goto show_help
if /i "%choice%"=="Q" goto end
goto menu

:devrun
call :ensure_python
if errorlevel 1 goto menu
call :ensure_node
if errorlevel 1 goto menu
call :setup_venv
if errorlevel 1 goto menu
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo Port 8000 is already in use.
  pause
  goto menu
)
netstat -ano | findstr ":3000 " | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo Port 3000 is already in use.
  pause
  goto menu
)
echo Starting Backend...
start "" cmd /c "cd /d "%ROOT%backend" && "%VENV_PY%" entrypoint.py"
echo Starting Frontend...
start "" cmd /c "cd /d "%ROOT%frontend" && npm run dev"
timeout /t 4 /nobreak >nul
start "" "http://localhost:3000"
echo.
echo WishShare started: http://localhost:3000
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
pause
goto menu

:dev_backend
call :ensure_python
if errorlevel 1 goto menu
call :setup_venv
if errorlevel 1 goto menu
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo Port 8000 is already in use.
  pause
  goto menu
)
echo Starting Backend server...
start "" cmd /c "cd /d "%ROOT%backend" && "%VENV_PY%" entrypoint.py"
timeout /t 2 /nobreak >nul
echo.
echo Backend started: http://localhost:8000
echo API Docs: http://localhost:8000/docs
pause
goto menu

:dev_frontend
call :ensure_node
if errorlevel 1 goto menu
if not exist "%ROOT%frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd "%ROOT%frontend"
  npm install
  popd
)
netstat -ano | findstr ":3000 " | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo Port 3000 is already in use.
  pause
  goto menu
)
echo Starting Frontend server...
start "" cmd /c "cd /d "%ROOT%frontend" && npm run dev"
timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"
echo.
echo Frontend started: http://localhost:3000
pause
goto menu

:build_frontend
call :ensure_node
if errorlevel 1 goto menu
echo Building frontend for production...
pushd "%ROOT%frontend"
if not exist "%ROOT%frontend\node_modules" (
  npm install
)
npm run build
popd
echo.
echo Frontend build completed.
echo Output: %ROOT%frontend\.next
pause
goto menu

:docker_dev
call :ensure_docker
if errorlevel 1 goto menu
echo Starting Docker containers (Dev mode)...
call %COMPOSE_CMD% -f "%ROOT%docker-compose.dev.yml" up -d --build
echo.
echo Docker Dev environment started.
pause
goto menu

:docker_prod
call :ensure_docker
if errorlevel 1 goto menu
echo Starting Docker containers (Production)...
call %COMPOSE_CMD% -f "%ROOT%docker-compose.yml" up -d --build
echo.
echo Docker Production environment started.
pause
goto menu

:docker_prod_nginx
call :ensure_docker
if errorlevel 1 goto menu
echo Starting Docker with Nginx (Production)...
call %COMPOSE_CMD% -f "%ROOT%docker-compose.yml" --profile production up -d --build
echo.
echo Docker Production + Nginx started.
pause
goto menu

:docker_logs
call :ensure_docker
if errorlevel 1 goto menu
echo Showing Docker logs (Ctrl+C to exit)...
call %COMPOSE_CMD% -f "%ROOT%docker-compose.yml" logs -f
pause
goto menu

:docker_stop
call :ensure_docker
if errorlevel 1 goto menu
echo Stopping Docker containers...
call %COMPOSE_CMD% -f "%ROOT%docker-compose.yml" down
echo Docker containers stopped.
pause
goto menu

:tunnel
call :ensure_cloudflared
if errorlevel 1 goto menu
echo Starting Cloudflare Tunnel...
echo This will create a public URL for your local server.
start "" cmd /c "cloudflared tunnel --url http://localhost:3000"
echo.
echo Tunnel started. Check the new window for your public URL.
pause
goto menu

:generate_jwt
call :ensure_python
if errorlevel 1 goto menu
echo.
echo Generating secure JWT Secret Key...
echo.
for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_urlsafe(64))"') do set "JWT_KEY=%%i"
echo Your JWT Secret Key:
echo.
echo %JWT_KEY%
echo.
echo Add this to your .env file:
echo JWT_SECRET_KEY=%JWT_KEY%
echo.
if exist "%ROOT%.env" (
  set /p "update_env=Update .env file automatically? [Y/N]: "
  if /i "!update_env!"=="Y" (
    findstr /C:"JWT_SECRET_KEY" "%ROOT%.env" >nul
    if errorlevel 1 (
      echo JWT_SECRET_KEY=!JWT_KEY!>> "%ROOT%.env"
      echo JWT_SECRET_KEY added to .env
    ) else (
      powershell -Command "(Get-Content '%ROOT%.env') -replace '^JWT_SECRET_KEY=.*', 'JWT_SECRET_KEY=!JWT_KEY!' | Set-Content '%ROOT%.env'"
      echo JWT_SECRET_KEY updated in .env
    )
  )
)
pause
goto menu

:setup_env
echo.
echo Setting up .env file...
if exist "%ROOT%.env" (
  echo .env file already exists.
  set /p "overwrite=Overwrite? [Y/N]: "
  if /i "!overwrite!"=="N" (
    echo Opening .env for editing...
    notepad "%ROOT%.env"
    goto menu
  )
)
if exist "%ROOT%.env.example" (
  copy "%ROOT%.env.example" "%ROOT%.env" >nul
  echo Created .env from .env.example
  echo.
  echo Please edit .env with your settings.
  notepad "%ROOT%.env"
) else (
  echo .env.example not found. Creating minimal .env...
  (
    echo # WishShare Configuration
    echo APP_NAME=WishShare API
    echo BACKEND_URL=http://localhost:8000
    echo FRONTEND_URL=http://localhost:3000
    echo ENVIRONMENT=local
    echo.
    echo # Database
    echo POSTGRES_DSN=sqlite+aiosqlite:///./wishshare.db
    echo.
    echo # Security - Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    echo JWT_SECRET_KEY=CHANGE_ME
    echo.
    echo # OAuth (optional)
    echo GOOGLE_CLIENT_ID=
    echo GOOGLE_CLIENT_SECRET=
    echo GITHUB_CLIENT_ID=
    echo GITHUB_CLIENT_SECRET=
    echo.
    echo # SMTP (optional)
    echo SMTP_HOST=
    echo SMTP_PORT=587
    echo SMTP_USERNAME=
    echo SMTP_PASSWORD=
  ) > "%ROOT%.env"
  echo Created minimal .env file
  notepad "%ROOT%.env"
)
pause
goto menu

:clean_cache
echo.
echo Cleaning cache and temporary files...
echo.
if exist "%ROOT%frontend\.next" (
  rmdir /s /q "%ROOT%frontend\.next"
  echo Removed frontend\.next
)
if exist "%ROOT%frontend\node_modules\.cache" (
  rmdir /s /q "%ROOT%frontend\node_modules\.cache"
  echo Removed frontend\node_modules\.cache
)
if exist "%ROOT%frontend\.tmp" (
  rmdir /s /q "%ROOT%frontend\.tmp"
  echo Removed frontend\.tmp
)
if exist "%ROOT%backend\__pycache__" (
  rmdir /s /q "%ROOT%backend\__pycache__"
  echo Removed backend\__pycache__
)
if exist "%ROOT%backend\.pytest_cache" (
  rmdir /s /q "%ROOT%backend\.pytest_cache"
  echo Removed backend\.pytest_cache
)
for /d /r "%ROOT%backend" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
echo.
echo Cache cleanup completed.
pause
goto menu

:check_ports
echo.
echo Checking ports status...
echo.
netstat -ano | findstr ":3000 " | findstr "LISTENING" >nul
if errorlevel 1 (
  echo   Port 3000 [FREE]
) else (
  echo   Port 3000 [IN USE]
)
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if errorlevel 1 (
  echo   Port 8000 [FREE]
) else (
  echo   Port 8000 [IN USE]
)
netstat -ano | findstr ":5432 " | findstr "LISTENING" >nul
if errorlevel 1 (
  echo   Port 5432 [FREE]
) else (
  echo   Port 5432 [IN USE]
)
netstat -ano | findstr ":6379 " | findstr "LISTENING" >nul
if errorlevel 1 (
  echo   Port 6379 [FREE]
) else (
  echo   Port 6379 [IN USE]
)
echo.
pause
goto menu

:run_tests
call :ensure_python
if errorlevel 1 goto menu
call :ensure_node
if errorlevel 1 goto menu
echo.
echo ===============================================
echo          Running Backend Tests
echo ===============================================
pushd "%ROOT%backend"
if exist "%ROOT%backend\.venv\Scripts\python.exe" (
  "%ROOT%backend\.venv\Scripts\python.exe" -m pytest -v --tb=short -q
) else (
  python -m pytest -v --tb=short -q
)
popd
echo.
echo ===============================================
echo          Running Frontend Tests
echo ===============================================
pushd "%ROOT%frontend"
if not exist "%ROOT%frontend\node_modules" (
  npm install
)
npm run test
popd
echo.
echo All tests completed.
pause
goto menu

:show_help
cls
echo.
echo  ====================================================
echo                 HELP AND DOCUMENTATION
echo  ====================================================
echo.
echo  GETTING STARTED:
echo    1. Press E to create .env file
echo    2. Press G to generate JWT secret key
echo    3. Press 1 to start development servers
echo.
echo  PORTS:
echo    - Frontend: http://localhost:3000
echo    - Backend:  http://localhost:8000
echo    - API Docs: http://localhost:8000/docs
echo.
echo  DOCKER:
echo    - Option 5: Dev mode with hot reload
echo    - Option 6: Production build
echo    - Option 7: Production with Nginx reverse proxy
echo.
echo  TROUBLESHOOTING:
echo    - If ports are in use, press S to check status
echo    - Press C to clean cache if builds fail
echo    - Check logs with option 8
echo.
echo  ====================================================
pause
goto menu

:: === Helper Functions ===

:ensure_python
where python >nul 2>&1
if errorlevel 1 (
  echo Python not found. Install Python 3.11 or newer.
  echo Download: https://www.python.org/downloads/
  exit /b 1
)
exit /b 0

:ensure_node
where node >nul 2>&1
if errorlevel 1 (
  echo Node.js not found. Install Node.js 20 or newer.
  echo Download: https://nodejs.org/
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
  echo Download: https://www.docker.com/products/docker-desktop
  exit /b 1
)
call :resolve_compose
if not defined COMPOSE_CMD (
  echo Docker Compose not found. Update Docker Desktop.
  exit /b 1
)
exit /b 0

:ensure_cloudflared
where cloudflared >nul 2>&1
if errorlevel 1 (
  echo cloudflared not found.
  echo Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
  exit /b 1
)
exit /b 0

:setup_venv
if not exist "%ROOT%backend\.venv" (
  echo Creating Python virtual environment...
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
echo Installing Python dependencies...
"%VENV_PY%" -m pip install -q -r "%ROOT%backend\requirements.txt"
if errorlevel 1 (
  echo Failed to install Python dependencies.
  exit /b 1
)
echo Installing Playwright browser...
"%VENV_PY%" -m playwright install chromium >nul 2>&1
if not exist "%ROOT%frontend\node_modules" (
  echo Installing Node.js dependencies...
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
cls
echo.
echo Thanks for using WishShare!
echo.
exit /b