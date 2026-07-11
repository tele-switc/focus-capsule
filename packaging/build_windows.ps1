[CmdletBinding()]
param(
    [string]$Python,
    [switch]$SkipDependencyInstall,
    [switch]$SkipInstaller,
    [switch]$RequireSigning
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "The Windows package must be built on Windows."
}

$Root = Split-Path -Parent $PSScriptRoot
$BuildDir = Join-Path $Root "build"
$DistDir = Join-Path $Root "dist"
$Version = (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "version.txt")).Trim()

function Resolve-BuildPython {
    param([string]$RequestedPython)

    if ($RequestedPython) {
        $command = Get-Command $RequestedPython -ErrorAction Stop
        return $command.Source
    }

    $venvPython = Join-Path $Root ".venv-build\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $launcher = Get-Command py -ErrorAction Stop
        & $launcher.Source -3.14 -m venv (Join-Path $Root ".venv-build")
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to create the Python 3.14 build environment."
        }
    }
    return $venvPython
}

function Find-SignTool {
    $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $kitsRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (Test-Path -LiteralPath $kitsRoot) {
        $candidate = Get-ChildItem -LiteralPath $kitsRoot -Filter signtool.exe -Recurse -File |
            Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }
    return $null
}

function Sign-Artifact {
    param([Parameter(Mandatory)][string]$Path)

    $certificate = $env:WINDOWS_SIGN_PFX
    if (-not $certificate) {
        if ($RequireSigning) {
            throw "WINDOWS_SIGN_PFX is required for this build."
        }
        Write-Warning "Signing skipped for $Path because WINDOWS_SIGN_PFX is not set."
        return
    }
    if (-not (Test-Path -LiteralPath $certificate)) {
        throw "Signing certificate not found: $certificate"
    }

    $signTool = Find-SignTool
    if (-not $signTool) {
        throw "signtool.exe was not found. Install the Windows SDK before signing."
    }

    $timestamp = if ($env:WINDOWS_TIMESTAMP_URL) {
        $env:WINDOWS_TIMESTAMP_URL
    } else {
        "http://timestamp.digicert.com"
    }
    $arguments = @(
        "sign", "/fd", "SHA256", "/td", "SHA256", "/tr", $timestamp,
        "/f", $certificate
    )
    if ($env:WINDOWS_SIGN_PASSWORD) {
        $arguments += @("/p", $env:WINDOWS_SIGN_PASSWORD)
    }
    $arguments += $Path

    & $signTool @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Authenticode signing failed for $Path"
    }
    & $signTool verify /pa /v $Path
    if ($LASTEXITCODE -ne 0) {
        throw "Authenticode verification failed for $Path"
    }
}

function Find-InnoCompiler {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @()
    if (${env:ProgramFiles(x86)}) {
        $candidates += Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
    }
    if ($env:LOCALAPPDATA) {
        $candidates += Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
    }
    return $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

$BuildPython = Resolve-BuildPython -RequestedPython $Python
Write-Host "Building Focus Capsule $Version with $BuildPython"

Push-Location $Root
try {
    $env:PYTHONUTF8 = "1"
    if (-not $SkipDependencyInstall) {
        & $BuildPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
        & $BuildPython -m pip install -r (Join-Path $Root "requirements-build.txt")
        if ($LASTEXITCODE -ne 0) { throw "Build dependency installation failed." }
    }

    & $BuildPython (Join-Path $PSScriptRoot "generate_version_info.py")
    if ($LASTEXITCODE -ne 0) { throw "Version resource generation failed." }
    & $BuildPython (Join-Path $PSScriptRoot "generate_icons.py") --platform windows
    if ($LASTEXITCODE -ne 0) { throw "Windows icon generation failed." }

    $env:PYTHONHASHSEED = "0"
    $pyInstallerArguments = @(
        "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath", $DistDir,
        "--workpath", $BuildDir,
        (Join-Path $PSScriptRoot "Focus Capsule.windows.spec")
    )
    & $BuildPython @pyInstallerArguments
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

    $application = Join-Path $DistDir "Focus Capsule\Focus Capsule.exe"
    if (-not (Test-Path -LiteralPath $application)) {
        throw "Expected application was not produced: $application"
    }
    Sign-Artifact -Path $application

    if ($SkipInstaller) {
        Write-Host "Portable application: $(Split-Path -Parent $application)"
        return
    }

    $iscc = Find-InnoCompiler
    if (-not $iscc) {
        throw "Inno Setup 6 was not found. Install it with: winget install --id JRSoftware.InnoSetup -e"
    }

    & $iscc "/DMyAppVersion=$Version" (Join-Path $PSScriptRoot "focus-capsule.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }

    $installer = Join-Path $DistDir "installer\Focus-Capsule-$Version-Windows-x64-Setup.exe"
    if (-not (Test-Path -LiteralPath $installer)) {
        throw "Expected installer was not produced: $installer"
    }
    Sign-Artifact -Path $installer

    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash.ToLowerInvariant()
    "$hash  $(Split-Path -Leaf $installer)" |
        Set-Content -LiteralPath "$installer.sha256" -Encoding ascii
    Write-Host "Installer: $installer"
    Write-Host "SHA-256: $hash"
}
finally {
    Pop-Location
}
