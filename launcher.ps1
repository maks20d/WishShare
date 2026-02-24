param(
  [string]$Command,
  [string]$Arg1,
  [string]$Arg2
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvDir = Join-Path $BackendDir ".venv"
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"
$script:ForceSync = ($Arg1 -ieq "sync" -or $Arg2 -ieq "sync")
$script:AppUpdated = $false

function Write-Info([string]$Message) { Write-Host "[INFO] $Message" }
function Write-Ok([string]$Message) { Write-Host "[OK] $Message" }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" }
function Write-Err([string]$Message) { Write-Host "[ERROR] $Message" }

function Ensure-LogDir {
  $logDir = Join-Path $Root ".logs"
  if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -Path $logDir -ItemType Directory -Force | Out-Null
  }
  return $logDir
}

function Ensure-Python {
  if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python not found in PATH."
  }
}

function Ensure-Node {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js not found in PATH."
  }
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm not found in PATH."
  }
}

function Resolve-Compose {
  if (Get-Command docker -ErrorAction SilentlyContinue) {
    & docker compose version *> $null
    if ($LASTEXITCODE -eq 0) { return "docker-compose-v2" }
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) { return "docker-compose-v1" }
  }
  throw "Docker Compose command not found."
}

function Get-PortPids([int]$Port) {
  $pids = @()
  $pattern = ":{0}\s+.*LISTENING" -f $Port
  $lines = netstat -ano | Select-String -Pattern $pattern
  foreach ($entry in $lines) {
    if ($entry.Line -match "LISTENING\s+(\d+)$") {
      $procId = [int]$Matches[1]
      if ($procId -ne 0) { $pids += $procId }
    }
  }
  return ($pids | Sort-Object -Unique)
}

function Test-PortInUse([int]$Port) {
  return (Get-PortPids -Port $Port).Count -gt 0
}

function Show-PortStatus([int]$Port, [string]$Name) {
  if (Test-PortInUse -Port $Port) {
    Write-Host "[USED] $Port - $Name"
  } else {
    Write-Host "[FREE] $Port - $Name"
  }
}

function Ensure-BackendDeps {
  Ensure-Python

  if (-not (Test-Path -LiteralPath $VenvPy)) {
    Write-Info "Creating backend virtualenv..."
    & python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Failed to create virtualenv." }
  }

  if (-not (Test-Path -LiteralPath $VenvPy)) {
    throw "Virtualenv python not found: $VenvPy"
  }

  $depsMarker = Join-Path $VenvDir ".deps_installed"
  if ($script:ForceSync -and (Test-Path -LiteralPath $depsMarker)) {
    Remove-Item -LiteralPath $depsMarker -Force -ErrorAction SilentlyContinue
  }

  if (-not (Test-Path -LiteralPath $depsMarker)) {
    Write-Info "Installing backend dependencies..."
    & $VenvPy -m pip install --disable-pip-version-check -q --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }

    & $VenvPy -m pip install -q -r (Join-Path $BackendDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Failed to install backend dependencies." }

    Write-Info "Installing Playwright Chromium..."
    & $VenvPy -m playwright install chromium *> $null

    New-Item -Path $depsMarker -ItemType File -Force | Out-Null
  }
}

function Ensure-FrontendDeps {
  Ensure-Node

  $nodeModules = Join-Path $FrontendDir "node_modules"
  if ($script:ForceSync -and (Test-Path -LiteralPath $nodeModules)) {
    Remove-Item -LiteralPath $nodeModules -Recurse -Force -ErrorAction SilentlyContinue
  }

  if (-not (Test-Path -LiteralPath $nodeModules)) {
    Write-Info "Installing frontend dependencies..."
    Push-Location $FrontendDir
    try {
      & npm install
      if ($LASTEXITCODE -ne 0) { throw "Failed to install frontend dependencies." }
    } finally {
      Pop-Location
    }
  }
}

function Reset-FrontendDevCache {
  $dirs = @(
    (Join-Path $FrontendDir ".next"),
    (Join-Path $FrontendDir ".next-dev")
  )

  foreach ($dir in $dirs) {
    if (Test-Path -LiteralPath $dir) {
      Write-Info "Resetting frontend dev cache ($([System.IO.Path]::GetFileName($dir)))..."
      Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
}

function Wait-ForCondition(
  [scriptblock]$Condition,
  [string]$Name,
  [int]$TimeoutSec = 60,
  [int]$IntervalMs = 1000
) {
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    if (& $Condition) { return $true }
    Start-Sleep -Milliseconds $IntervalMs
  }
  Write-Warn "Timeout while waiting for $Name."
  return $false
}

function Test-BackendHealthy {
  try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 3
    return ($health.status -eq "ok")
  } catch {
    return $false
  }
}

function Test-BackendDbHealthy {
  try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/db" -Method Get -TimeoutSec 3
    return ($health.status -eq "ok")
  } catch {
    return $false
  }
}

function Sync-AppCode {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Warn "Git not found. Skipping app auto-update."
    return
  }

  Push-Location $Root
  try {
    $status = (& git status --porcelain).Trim()
    if (-not [string]::IsNullOrWhiteSpace($status)) {
      Write-Warn "Working tree has local changes. Skipping auto-update."
      return
    }

    Write-Info "Checking for updates on origin/main..."
    & git fetch origin main --quiet
    if ($LASTEXITCODE -ne 0) {
      Write-Warn "git fetch failed. Continuing with local code."
      return
    }

    $localHead = (& git rev-parse HEAD).Trim()
    $remoteHead = (& git rev-parse origin/main).Trim()
    if ($localHead -eq $remoteHead) {
      Write-Info "App code is up to date."
      return
    }

    $mergeBase = (& git merge-base HEAD origin/main).Trim()
    if ($localHead -ne $mergeBase) {
      Write-Warn "Local branch is ahead/diverged from origin/main. Skipping auto-update."
      return
    }

    Write-Info "Updating app code (fast-forward)..."
    & git pull --ff-only origin main
    if ($LASTEXITCODE -ne 0) {
      Write-Warn "git pull failed. Continuing with local code."
      return
    }

    $script:AppUpdated = $true
    $script:ForceSync = $true
    Write-Ok "App code updated from origin/main."
  } finally {
    Pop-Location
  }
}

function Ensure-BackendMigrations {
  $alembicIni = Join-Path $BackendDir "alembic.ini"
  if (-not (Test-Path -LiteralPath $alembicIni)) {
    Write-Warn "alembic.ini not found. Skipping migrations."
    return
  }

  Write-Info "Applying backend migrations..."
  Push-Location $BackendDir
  try {
    & $VenvPy -m alembic -c $alembicIni upgrade head
    if ($LASTEXITCODE -ne 0) {
      throw "Backend migrations failed."
    }
  } finally {
    Pop-Location
  }
  Write-Ok "Backend migrations are up to date."
}

function Test-FrontendReady {
  try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -Method Get -TimeoutSec 3 -UseBasicParsing
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
  } catch {
    return $false
  }
}

function Stop-AppPorts {
  Write-Info "Stopping app ports (3000/8000)..."
  foreach ($port in @(3000, 8000)) {
    $found = $false
    foreach ($procId in (Get-PortPids -Port $port)) {
      try {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Ok "Stopped PID $procId on port $port."
        $found = $true
      } catch {}
    }
    if (-not $found) {
      Write-Info "Port $port already free."
    }
  }

  if ((-not (Test-PortInUse 3000)) -and (-not (Test-PortInUse 8000))) {
    Write-Ok "Ports 3000 and 8000 are free."
    return
  }

  throw "Failed to free one or more ports."
}

function Stop-ServiceByPid([int]$ProcessId, [string]$Name) {
  if ($ProcessId -le 0) {
    return
  }

  try {
    Stop-Process -Id $ProcessId -Force -ErrorAction Stop
    Write-Ok ("Stopped {0} process PID {1}." -f $Name, $ProcessId)
  } catch {
    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -ne $proc) {
      Write-Warn ("Failed to stop {0} process PID {1}: {2}" -f $Name, $ProcessId, $_.Exception.Message)
    }
  }
}

function Start-Backend {
  Ensure-BackendDeps
  if (Test-PortInUse 8000) {
    throw "Port 8000 is already in use."
  }

  Write-Info "Starting backend on http://localhost:8000"
  $cmd = "cd /d `"$BackendDir`" && `"$VenvPy`" entrypoint.py"
  Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $cmd | Out-Null
}

function Start-BackendService {
  Ensure-BackendDeps

  if (Test-BackendHealthy) {
    Write-Info "Backend already running."
    if (-not (Wait-ForCondition -Condition { Test-BackendDbHealthy } -Name "backend db health" -TimeoutSec 20)) {
      Write-Warn "Backend is running but /health/db did not become ready."
    }
    return [pscustomobject]@{ StartedNow = $false; PID = $null }
  }

  Ensure-BackendMigrations

  if (Test-PortInUse 8000) {
    Write-Warn "Port 8000 is busy but backend healthcheck failed. Releasing port..."
    foreach ($procId in (Get-PortPids -Port 8000)) {
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
  }

  $logDir = Ensure-LogDir
  $backendOut = Join-Path $logDir "backend.out.log"
  $backendErr = Join-Path $logDir "backend.err.log"

  Write-Info "Starting backend service..."
  $process = Start-Process `
    -FilePath $VenvPy `
    -ArgumentList "entrypoint.py" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -WindowStyle Hidden `
    -PassThru

  if (-not (Wait-ForCondition -Condition { Test-BackendHealthy } -Name "backend" -TimeoutSec 45)) {
    Stop-ServiceByPid -ProcessId $process.Id -Name "backend"
    throw "Backend failed to start. Check logs in .logs/backend.err.log"
  }

  if (-not (Wait-ForCondition -Condition { Test-BackendDbHealthy } -Name "backend db health" -TimeoutSec 30)) {
    Stop-ServiceByPid -ProcessId $process.Id -Name "backend"
    throw "Backend started but database healthcheck failed. Check backend logs."
  }

  Write-Ok "Backend is ready."
  return [pscustomobject]@{ StartedNow = $true; PID = $process.Id }
}

function Start-Frontend {
  Reset-FrontendDevCache
  Ensure-FrontendDeps
  if (Test-PortInUse 3000) {
    throw "Port 3000 is already in use."
  }

  Write-Info "Starting frontend on http://localhost:3000"
  $cmd = "cd /d `"$FrontendDir`" && npm run dev"
  Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $cmd | Out-Null
  Start-Sleep -Milliseconds 700
  Open-FrontendUrl
}

function Ensure-FrontendBuild {
  $buildId = Join-Path $FrontendDir ".next\BUILD_ID"
  if ((-not $script:AppUpdated) -and (Test-Path -LiteralPath $buildId)) {
    return
  }
  if ($script:AppUpdated) {
    Write-Info "App code updated. Rebuilding frontend..."
  } else {
    Write-Info "Frontend production build not found. Building..."
  }
  Build-Frontend
}

function Start-FrontendService {
  Ensure-FrontendDeps
  Ensure-FrontendBuild

  if (Test-FrontendReady) {
    Write-Info "Frontend already running."
    return [pscustomobject]@{ StartedNow = $false; PID = $null }
  }

  if (Test-PortInUse 3000) {
    Write-Warn "Port 3000 is busy but frontend probe failed. Releasing port..."
    foreach ($procId in (Get-PortPids -Port 3000)) {
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
  }

  $logDir = Ensure-LogDir
  $frontendOut = Join-Path $logDir "frontend.out.log"
  $frontendErr = Join-Path $logDir "frontend.err.log"
  $nodeCmd = Get-Command node -ErrorAction Stop
  $nextCli = Join-Path $FrontendDir "node_modules\next\dist\bin\next"
  if (-not (Test-Path -LiteralPath $nextCli)) {
    throw "Next.js CLI not found: $nextCli"
  }

  Write-Info "Starting frontend service..."
  $process = Start-Process `
    -FilePath $nodeCmd.Source `
    -ArgumentList @($nextCli, "start", "--port", "3000") `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr `
    -WindowStyle Hidden `
    -PassThru

  if (-not (Wait-ForCondition -Condition { Test-FrontendReady } -Name "frontend" -TimeoutSec 60)) {
    Stop-ServiceByPid -ProcessId $process.Id -Name "frontend"
    throw "Frontend failed to start. Check logs in .logs/frontend.err.log"
  }

  Write-Ok "Frontend is ready."
  return [pscustomobject]@{ StartedNow = $true; PID = $process.Id }
}

function Start-App {
  Write-Info "Launching WishShare app mode..."
  Sync-AppCode

  $backendState = $null
  $frontendState = $null
  $appWindow = $null

  try {
    $backendState = Start-BackendService
    $frontendState = Start-FrontendService
    $appWindow = Open-AppWindow

    if ($null -ne $appWindow) {
      Write-Ok "WishShare app launched. Close the app window to stop local services."
      Wait-Process -Id $appWindow.Id
    } else {
      Write-Warn "App window process is not trackable. Press Enter to stop services started by app mode."
      [void](Read-Host)
    }
  } finally {
    if ($frontendState -and $frontendState.StartedNow -and $frontendState.PID) {
      Stop-ServiceByPid -ProcessId ([int]$frontendState.PID) -Name "frontend"
    }
    if ($backendState -and $backendState.StartedNow -and $backendState.PID) {
      Stop-ServiceByPid -ProcessId ([int]$backendState.PID) -Name "backend"
    }
  }

  Write-Ok "WishShare app stopped."
}

function Build-Frontend {
  Ensure-FrontendDeps
  Write-Info "Building frontend..."
  Push-Location $FrontendDir
  try {
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
  } finally {
    Pop-Location
  }
  Write-Ok "Frontend build completed."
}

function Run-Tests {
  Ensure-BackendDeps
  Ensure-FrontendDeps

  Write-Info "Running backend tests..."
  Push-Location $Root
  try {
    & $VenvPy -m pytest backend/tests -q
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }
  } finally {
    Pop-Location
  }

  Write-Info "Running frontend tests..."
  Push-Location $FrontendDir
  try {
    & npm run test
    if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed." }
  } finally {
    Pop-Location
  }

  Write-Ok "All tests passed."
}

function Check-Prereq {
  Write-Info "Checking prerequisites..."
  $hasError = $false

  if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyv = (& python --version 2>&1).Trim()
    Write-Ok $pyv
  } else {
    Write-Err "Python not found in PATH."
    $hasError = $true
  }

  if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodev = (& node --version 2>&1).Trim()
    Write-Ok "Node $nodev"
  } else {
    Write-Err "Node.js not found in PATH."
    $hasError = $true
  }

  if (Get-Command npm -ErrorAction SilentlyContinue) {
    $npmv = (& npm --version 2>&1).Trim()
    Write-Ok "npm $npmv"
  } else {
    Write-Err "npm not found in PATH."
    $hasError = $true
  }

  if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Ok "Docker found."
  } else {
    Write-Warn "Docker not found - optional."
  }

  $envPath = Join-Path $Root ".env"
  if (Test-Path -LiteralPath $envPath) {
    Write-Ok ".env exists."
  } else {
    Write-Warn ".env missing. Run: run.bat env"
  }

  if ($hasError) { throw "Prerequisite check failed." }
  Write-Ok "Prerequisite check passed."
}

function Create-EnvFile {
  $envPath = Join-Path $Root ".env"
  if (Test-Path -LiteralPath $envPath) {
    Write-Info ".env already exists: $envPath"
    return
  }
  $example = Join-Path $Root ".env.example"
  if (-not (Test-Path -LiteralPath $example)) {
    throw ".env.example not found."
  }
  Copy-Item -LiteralPath $example -Destination $envPath -Force
  Write-Ok "Created .env from .env.example"
}

function Get-AppModeBrowserPath {
  $candidates = @(
    (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe")
  )

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
      return $candidate
    }
  }

  foreach ($cmdName in @("chrome", "msedge")) {
    $cmd = Get-Command $cmdName -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
      return $cmd.Source
    }
  }

  return $null
}

function Open-AppWindow {
  $url = "http://localhost:3000"
  $browserPath = Get-AppModeBrowserPath

  if ($browserPath) {
    $profileDir = Join-Path $Root ".app-profile"
    if (-not (Test-Path -LiteralPath $profileDir)) {
      New-Item -Path $profileDir -ItemType Directory -Force | Out-Null
    }

    return Start-Process `
      -FilePath $browserPath `
      -ArgumentList @("--app=$url", "--new-window", "--user-data-dir=$profileDir") `
      -PassThru
  }

  Write-Warn "Chrome/Edge not found. Opening default browser without lifecycle tracking."
  Start-Process $url | Out-Null
  return $null
}

function Open-FrontendUrl {
  $window = Open-AppWindow
  if ($null -eq $window) {
    return
  }
}

function Create-DesktopShortcut {
  $desktop = [Environment]::GetFolderPath("Desktop")
  $shortcutPath = Join-Path $desktop "WishShare.lnk"

  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($shortcutPath)
  $shortcut.TargetPath = Join-Path $Root "run.bat"
  $shortcut.Arguments = "app"
  $shortcut.WorkingDirectory = $Root
  $shortcut.Description = "WishShare (auto-start backend/frontend and open app window)"

  $iconPath = Join-Path $FrontendDir "public\favicon.ico"
  if (Test-Path -LiteralPath $iconPath) {
    $iconFile = Get-Item -LiteralPath $iconPath -ErrorAction SilentlyContinue
    if ($iconFile -and $iconFile.Length -gt 0) {
      $shortcut.IconLocation = $iconPath
    } else {
      $shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
    }
  } else {
    $shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
  }

  $shortcut.Save()

  Write-Ok "Desktop shortcut created: $shortcutPath"
  Write-Info "Shortcut now auto-starts backend/frontend and opens WishShare app window."
}

function Generate-Jwt {
  if (Get-Command python -ErrorAction SilentlyContinue) {
    $jwt = (& python -c "import secrets; print(secrets.token_urlsafe(64))").Trim()
  } else {
    $bytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $jwt = [Convert]::ToBase64String($bytes)
  }
  Write-Ok "JWT secret generated:"
  Write-Host $jwt
}

function Clean-Caches {
  Write-Info "Cleaning caches..."
  $paths = @(
    (Join-Path $FrontendDir ".next"),
    (Join-Path $FrontendDir ".next-dev"),
    (Join-Path $FrontendDir "node_modules\.cache"),
    (Join-Path $FrontendDir ".tmp"),
    (Join-Path $BackendDir ".pytest_cache")
  )
  foreach ($path in $paths) {
    if (Test-Path -LiteralPath $path) {
      Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
  Get-ChildItem -Path $BackendDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
  Write-Ok "Cleanup finished."
}

function Docker-UpDev {
  $mode = Resolve-Compose
  if ($mode -eq "docker-compose-v1") {
    & docker-compose -f (Join-Path $Root "docker-compose.dev.yml") up -d --build
  } else {
    & docker compose -f (Join-Path $Root "docker-compose.dev.yml") up -d --build
  }
  if ($LASTEXITCODE -ne 0) { throw "Failed to start docker dev environment." }
  Write-Ok "Docker dev environment started."
}

function Docker-UpProd {
  $mode = Resolve-Compose
  if ($mode -eq "docker-compose-v1") {
    & docker-compose -f (Join-Path $Root "docker-compose.yml") up -d --build
  } else {
    & docker compose -f (Join-Path $Root "docker-compose.yml") up -d --build
  }
  if ($LASTEXITCODE -ne 0) { throw "Failed to start docker production environment." }
  Write-Ok "Docker production environment started."
}

function Docker-Stop {
  $mode = Resolve-Compose
  if ($mode -eq "docker-compose-v1") {
    & docker-compose -f (Join-Path $Root "docker-compose.yml") down
  } else {
    & docker compose -f (Join-Path $Root "docker-compose.yml") down
  }
  if ($LASTEXITCODE -ne 0) { throw "Failed to stop docker containers." }
  Write-Ok "Docker containers stopped."
}

function Docker-Logs {
  $mode = Resolve-Compose
  if ($mode -eq "docker-compose-v1") {
    & docker-compose -f (Join-Path $Root "docker-compose.yml") logs -f
  } else {
    & docker compose -f (Join-Path $Root "docker-compose.yml") logs -f
  }
  if ($LASTEXITCODE -ne 0) { throw "Failed to show docker logs." }
}

function Show-Ports {
  Write-Info "Port status:"
  Show-PortStatus 3000 "Frontend"
  Show-PortStatus 8000 "Backend"
  Show-PortStatus 5432 "PostgreSQL"
  Show-PortStatus 6379 "Redis"
}

function Show-Usage {
  Write-Host "Usage:"
  Write-Host "  run.bat app|dev|backend|frontend|build|test [sync]"
  Write-Host "  app mode: auto-update (clean git), migrate DB, stop started services on window close"
  Write-Host "  run.bat stop|ports|prereq|clean|env|jwt|shortcut"
  Write-Host "  run.bat docker-dev|docker-prod|docker-stop|docker-logs"
  Write-Host "  run.bat help"
}

function Invoke-CommandByName([string]$CmdName) {
  switch ($CmdName.ToLowerInvariant()) {
    "help" { Show-Usage }
    "app" { Start-App }
    "dev" { Start-Backend; Start-Frontend; Write-Ok "Development environment started." }
    "backend" { Start-Backend }
    "frontend" { Start-Frontend }
    "build" { Build-Frontend }
    "test" { Run-Tests }
    "stop" { Stop-AppPorts }
    "ports" { Show-Ports }
    "prereq" { Check-Prereq }
    "docker-dev" { Docker-UpDev }
    "docker-prod" { Docker-UpProd }
    "docker-stop" { Docker-Stop }
    "docker-logs" { Docker-Logs }
    "clean" { Clean-Caches }
    "env" { Create-EnvFile }
    "jwt" { Generate-Jwt }
    "shortcut" { Create-DesktopShortcut }
    "quit" { return }
    default {
      throw "Unknown command: $CmdName"
    }
  }
}

function Show-Menu {
  Clear-Host
  $line = "+-------------------------------------------------------------+"
  $status3000 = if (Test-PortInUse 3000) { "BUSY" } else { "FREE" }
  $status8000 = if (Test-PortInUse 8000) { "BUSY" } else { "FREE" }
  $statusText = "Ports 3000:$status3000  8000:$status8000"

  Write-Host ""
  Write-Host $line -ForegroundColor DarkCyan
  Write-Host "|                     WishShare Launcher                     |" -ForegroundColor Cyan
  Write-Host $line -ForegroundColor DarkCyan
  Write-Host ("| " + $statusText.PadRight(59) + "|") -ForegroundColor DarkGray
  Write-Host $line -ForegroundColor DarkCyan
  Write-Host "| START                                                       |" -ForegroundColor Yellow
  Write-Host "|  1) app        One-click app (auto-update + auto-stop)      |"
  Write-Host "|  2) dev        Start backend + frontend (dev mode)          |"
  Write-Host "|  3) backend    Start backend only                           |"
  Write-Host "|  4) frontend   Start frontend only                          |"
  Write-Host "|  5) stop       Stop app ports (3000/8000)                  |"
  Write-Host "|  6) ports      Show ports status                            |"
  Write-Host "|                                                             |"
  Write-Host "| MAINTENANCE                                                 |" -ForegroundColor Yellow
  Write-Host "|  7) build      Frontend production build                    |"
  Write-Host "|  8) test       Backend + frontend tests                     |"
  Write-Host "|  9) prereq     Prerequisites check                          |"
  Write-Host "| 10) env        Create .env from .env.example               |"
  Write-Host "| 11) jwt        Generate JWT secret key                      |"
  Write-Host "| 12) clean      Clean caches                                 |"
  Write-Host "| 13) shortcut   Create desktop app shortcut                  |"
  Write-Host "|                                                             |"
  Write-Host "| HELP: run.bat help                                          |" -ForegroundColor DarkGray
  Write-Host "| ADVANCED (CLI): docker-dev, docker-prod, docker-stop, logs |" -ForegroundColor DarkGray
  Write-Host "| Q) Quit                                                     |"
  Write-Host $line -ForegroundColor DarkCyan
  Write-Host ""
}

function Pause-Interactive {
  Write-Host ""
  Write-Host "Press any key to continue . . ."
  [void][System.Console]::ReadKey($true)
}

if (-not $Command) {
  while ($true) {
    Show-Menu
    $choice = Read-Host "Select option"
    if ($null -eq $choice) { continue }

    $mapped = switch ($choice.Trim().ToUpperInvariant()) {
      "1" { "app" }
      "2" { "dev" }
      "3" { "backend" }
      "4" { "frontend" }
      "5" { "stop" }
      "6" { "ports" }
      "7" { "build" }
      "8" { "test" }
      "9" { "prereq" }
      "10" { "env" }
      "11" { "jwt" }
      "12" { "clean" }
      "13" { "shortcut" }
      "Q" { "quit" }
      default { "" }
    }

    if ($mapped -eq "quit") {
      Write-Host "Bye."
      exit 0
    }
    if ([string]::IsNullOrWhiteSpace($mapped)) {
      Write-Err "Unknown option: $choice"
      Pause-Interactive
      continue
    }

    try {
      Invoke-CommandByName $mapped
    } catch {
      Write-Host ""
      Write-Err $_.Exception.Message
    }
    Pause-Interactive
  }
}

try {
  Invoke-CommandByName $Command
  exit 0
} catch {
  Write-Err $_.Exception.Message
  Show-Usage
  exit 1
}

