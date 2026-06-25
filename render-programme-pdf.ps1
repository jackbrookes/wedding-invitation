param(
    [string]$OutputPath = "programme-a5.pdf"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pagePath = Join-Path $root "programme\index.html"

if (-not (Test-Path -LiteralPath $pagePath)) {
    throw "Programme page not found: $pagePath"
}

$browserCandidates = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

$browserPath = $browserCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $browserPath) {
    $commands = @("msedge", "chrome", "chromium")
    foreach ($command in $commands) {
        $found = Get-Command $command -ErrorAction SilentlyContinue
        if ($found) {
            $browserPath = $found.Source
            break
        }
    }
}

if (-not $browserPath) {
    throw "Could not find Microsoft Edge or Google Chrome. Install one of them, then rerun this script."
}

$resolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
} else {
    Join-Path $root $OutputPath
}

$outputDir = Split-Path -Parent $resolvedOutput
if ($outputDir -and -not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$pageUri = [System.Uri]::new((Resolve-Path -LiteralPath $pagePath).Path).AbsoluteUri
$profileDir = Join-Path ([System.IO.Path]::GetTempPath()) ("programme-pdf-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $profileDir | Out-Null

$arguments = @(
    "--headless=new",
    "--disable-gpu",
    "--run-all-compositor-stages-before-draw",
    "--virtual-time-budget=3000",
    "--no-pdf-header-footer",
    "--user-data-dir=$profileDir",
    "--print-to-pdf=$resolvedOutput",
    $pageUri
)

try {
    $process = Start-Process -FilePath $browserPath -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "Browser PDF render failed with exit code $($process.ExitCode)."
    }

    if (-not (Test-Path -LiteralPath $resolvedOutput)) {
        throw "Browser completed but did not create the PDF: $resolvedOutput"
    }

    Write-Host "Rendered programme PDF:"
    Write-Host $resolvedOutput
} finally {
    if (Test-Path -LiteralPath $profileDir) {
        Remove-Item -LiteralPath $profileDir -Recurse -Force
    }
}
