$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DistRoot = Join-Path $Root "dist"
$WorkRoot = Join-Path $Root "build"

Set-Location $Root

Write-Host "Instalando dependencias de build..."
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias" }

Write-Host "Instalando Chromium de Playwright..."
python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar Chromium" }

if (Test-Path -LiteralPath $DistRoot) {
    Remove-Item -LiteralPath $DistRoot -Recurse -Force
}
if (Test-Path -LiteralPath $WorkRoot) {
    Remove-Item -LiteralPath $WorkRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $DistRoot | Out-Null
New-Item -ItemType Directory -Path $WorkRoot | Out-Null

function Build-Executable {
    param(
        [string]$Name,
        [string]$Script,
        [switch]$Windowed
    )

    $arguments = @(
        "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", $Name,
        "--distpath", $DistRoot,
        "--workpath", (Join-Path $WorkRoot $Name),
        "--specpath", (Join-Path $WorkRoot "spec"),
        "--icon", (Join-Path $Root "assets\asfi.ico"),
        "--add-data", ((Join-Path $Root "reportes_seed.json") + ";."),
        "--add-data", ((Join-Path $Root "assets") + ";assets"),
        "--collect-all", "playwright",
        "--hidden-import", "plyer.facades",
        "--hidden-import", "plyer.platforms.win.notification",
        "--hidden-import", "plyer.platforms.win.libs.balloontip",
        "--hidden-import", "asfi_monitor_app.application.runner",
        "--hidden-import", "asfi_monitor_app.application.instance_lock"
    )
    if ($Windowed) {
        $arguments += "--windowed"
    } else {
        $arguments += "--console"
    }
    $arguments += (Join-Path $Root $Script)

    Write-Host "Construyendo $Name..."
    & python @arguments
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo al construir $Name" }
}

Build-Executable -Name "ASFI_Monitor_GUI" -Script "gestionar_reportes.py" -Windowed
Build-Executable -Name "ASFI_Monitor_Agent" -Script "asfi_monitor_agent.py" -Windowed
Build-Executable -Name "ASFI_Monitor_CLI" -Script "asfi_monitor.py"

$browserSource = Join-Path $env:LOCALAPPDATA "ms-playwright"
if (!(Test-Path -LiteralPath $browserSource)) {
    throw "No se encontró Chromium en $browserSource"
}
Get-ChildItem -LiteralPath $DistRoot -Directory | ForEach-Object {
    Copy-Item -LiteralPath $browserSource -Destination (Join-Path $_.FullName "ms-playwright") -Recurse
}

Write-Host "Build terminado en $DistRoot"
Write-Host "Siguiente paso: compilar asfi_monitor.iss con Inno Setup."
