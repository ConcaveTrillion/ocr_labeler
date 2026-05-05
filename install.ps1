# Install pd-ocr-labeler as a standalone tool using uv.
#
# NOTE: This script has not been tested yet. Please report any issues at
#       https://github.com/ConcaveTrillion/pd-ocr-labeler/issues
#
# Usage (run in PowerShell):
#   irm https://raw.githubusercontent.com/ConcaveTrillion/pd-ocr-labeler/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

# Install uv if not already present
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found -- installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
    # Reload PATH so uv is available in this session
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + $env:PATH
}

$ExtraIndex = ""

# Auto-detect NVIDIA CUDA via nvidia-smi
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    try {
        $smiOut = & nvidia-smi 2>$null
        if ($smiOut -match "CUDA Version:\s*(\d+\.\d+)") {
            $CudaVer = $Matches[1]
            $CudaTag = "cu" + ($CudaVer -replace "\.", "")
            $ExtraIndex = "https://download.pytorch.org/whl/$CudaTag"
            Write-Host "Detected CUDA $CudaVer -- will install PyTorch with $CudaTag support."
        } else {
            Write-Host "nvidia-smi found but could not detect CUDA version -- falling back to CPU."
        }
    } catch {
        Write-Host "nvidia-smi found but could not detect CUDA version -- falling back to CPU."
    }
} else {
    Write-Host "No GPU detected -- installing CPU-only PyTorch."
}

# Resolve latest git tag from GitHub
$Repo = "ConcaveTrillion/pd-ocr-labeler"
$InstallRef = "git+https://github.com/$Repo"
try {
    $Tags = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/tags" -TimeoutSec 10
    if ($Tags -and $Tags.Count -gt 0) {
        $LatestTag = $Tags[0].name
        $InstallRef = "git+https://github.com/$Repo@$LatestTag"
        Write-Host "Installing pd-ocr-labeler $LatestTag..."
    } else {
        Write-Host "Installing pd-ocr-labeler (latest commit -- no tags found)..."
    }
} catch {
    Write-Host "Installing pd-ocr-labeler (latest commit -- could not resolve tag)..."
}

if ($ExtraIndex) {
    uv tool install --reinstall $InstallRef --extra-index-url $ExtraIndex
} else {
    uv tool install --reinstall $InstallRef
}

Write-Host ""
Write-Host "Done! Run: pd-ocr-labeler-ui ."
Write-Host "  (also available: pd-ocr-labeler-export)"
Write-Host "If 'pd-ocr-labeler-ui' is not found, ensure uv's tool bin is on your PATH."
Write-Host "  uv tool update-shell"
