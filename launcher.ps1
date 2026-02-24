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
$ForceSync = ($Arg1 -ieq "sync" -or $Arg2 -ieq "sync")

function Write-Info([string]$Message) { Write-Host "[INFO] $Message" }
function Write-Ok([string]$Message) { Write-Host "[OK] $Message" }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" }
function Write-Err([string]$Message) { Write-Host "[ERROR] $Message" }

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
  if ($ForceSync -and (Test-Path -LiteralPath $depsMarker)) {
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
  if ($ForceSync -and (Test-Path -LiteralPath $nodeModules)) {
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

function Start-Backend {
  Ensure-BackendDeps
  if (Test-PortInUse 8000) {
    throw "Port 8000 is already in use."
  }

  Write-Info "Starting backend on http://localhost:8000"
  $cmd = "cd /d `"$BackendDir`" && `"$VenvPy`" entrypoint.py"
  Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $cmd | Out-Null
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

function Open-FrontendUrl {
  $url = "http://localhost:3000"
  $browserPath = Get-AppModeBrowserPath

  if ($browserPath) {
    Start-Process -FilePath $browserPath -ArgumentList @("--app=$url", "--new-window") | Out-Null
    return
  }

  Write-Warn "Chrome/Edge not found. Opening default browser."
  Start-Process $url | Out-Null
}

function Create-DesktopShortcut {
  $browserPath = Get-AppModeBrowserPath
  if (-not $browserPath) {
    throw "Chrome/Edge not found. Install Chrome or Edge to create app-mode shortcut."
  }

  $desktop = [Environment]::GetFolderPath("Desktop")
  $shortcutPath = Join-Path $desktop "WishShare.lnk"

  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($shortcutPath)
  $shortcut.TargetPath = $browserPath
  $shortcut.Arguments = "--app=http://localhost:3000 --new-window"
  $shortcut.WorkingDirectory = $Root
  $shortcut.Description = "WishShare (opens in separate app window)"

  $iconPath = Join-Path $FrontendDir "public\favicon.ico"
  if (Test-Path -LiteralPath $iconPath) {
    $iconFile = Get-Item -LiteralPath $iconPath -ErrorAction SilentlyContinue
    if ($iconFile -and $iconFile.Length -gt 0) {
      $shortcut.IconLocation = $iconPath
    } else {
      $shortcut.IconLocation = $browserPath
    }
  } else {
    $shortcut.IconLocation = $browserPath
  }

  $shortcut.Save()

  Write-Ok "Desktop shortcut created: $shortcutPath"
  Write-Info "Shortcut opens WishShare in a separate browser app window."
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
  Write-Host "  run.bat dev|backend|frontend|build|test [sync]"
  Write-Host "  run.bat stop|ports|prereq|clean|env|jwt|shortcut"
  Write-Host "  run.bat docker-dev|docker-prod|docker-stop|docker-logs"
  Write-Host "  run.bat help"
}

function Invoke-CommandByName([string]$CmdName) {
  switch ($CmdName.ToLowerInvariant()) {
    "help" { Show-Usage }
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
  Write-Host "|  1) dev        Start backend + frontend                     |"
  Write-Host "|  2) backend    Start backend only                           |"
  Write-Host "|  3) frontend   Start frontend only                          |"
  Write-Host "|  4) stop       Stop app ports (3000/8000)                  |"
  Write-Host "|  5) ports      Show ports status                            |"
  Write-Host "|                                                             |"
  Write-Host "| MAINTENANCE                                                 |" -ForegroundColor Yellow
  Write-Host "|  6) build      Frontend production build                    |"
  Write-Host "|  7) test       Backend + frontend tests                     |"
  Write-Host "|  8) prereq     Prerequisites check                          |"
  Write-Host "|  9) env        Create .env from .env.example               |"
  Write-Host "| 10) jwt        Generate JWT secret key                      |"
  Write-Host "| 11) clean      Clean caches                                 |"
  Write-Host "| 12) shortcut   Create desktop app shortcut                  |"
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
      "1" { "dev" }
      "2" { "backend" }
      "3" { "frontend" }
      "4" { "stop" }
      "5" { "ports" }
      "6" { "build" }
      "7" { "test" }
      "8" { "prereq" }
      "9" { "env" }
      "10" { "jwt" }
      "11" { "clean" }
      "12" { "shortcut" }
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
