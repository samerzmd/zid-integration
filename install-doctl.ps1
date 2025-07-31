# DigitalOcean CLI (doctl) Installation Script for Windows
# Run this script as Administrator

param(
    [string]$InstallPath = "C:\doctl"
)

Write-Host "🚀 Installing DigitalOcean CLI (doctl)..." -ForegroundColor Green

# Create installation directory
if (!(Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    Write-Host "✅ Created directory: $InstallPath" -ForegroundColor Green
}

# Get latest release info from GitHub API
try {
    $latestRelease = Invoke-RestMethod -Uri "https://api.github.com/repos/digitalocean/doctl/releases/latest"
    $version = $latestRelease.tag_name
    $downloadUrl = ($latestRelease.assets | Where-Object { $_.name -match "windows-amd64\.zip$" }).browser_download_url
    
    if (!$downloadUrl) {
        throw "Could not find Windows download URL"
    }
    
    Write-Host "📦 Latest version: $version" -ForegroundColor Cyan
    Write-Host "🔗 Download URL: $downloadUrl" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Failed to get latest release info: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Download the binary
$zipPath = "$InstallPath\doctl.zip"
try {
    Write-Host "⬇️  Downloading doctl..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
    Write-Host "✅ Downloaded successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Download failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Extract the archive
try {
    Write-Host "📂 Extracting archive..." -ForegroundColor Yellow
    Expand-Archive -Path $zipPath -DestinationPath $InstallPath -Force
    Remove-Item $zipPath
    Write-Host "✅ Extracted successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Extraction failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Add to PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$InstallPath*") {
    try {
        Write-Host "🔧 Adding to system PATH..." -ForegroundColor Yellow
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$InstallPath", "Machine")
        Write-Host "✅ Added to PATH successfully" -ForegroundColor Green
        Write-Host "⚠️  Please restart your terminal to use doctl" -ForegroundColor Yellow
    } catch {
        Write-Host "❌ Failed to add to PATH: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "📝 Please manually add `'$InstallPath`' to your PATH environment variable" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Already in PATH" -ForegroundColor Green
}

# Verify installation
$doctlPath = "$InstallPath\doctl.exe"
if (Test-Path $doctlPath) {
    Write-Host "✅ Installation completed successfully!" -ForegroundColor Green
    Write-Host "📍 Installed at: $InstallPath" -ForegroundColor Cyan
    Write-Host "🔧 Next steps:" -ForegroundColor Yellow
    Write-Host "   1. Restart your terminal" -ForegroundColor White
    Write-Host "   2. Run: doctl auth init" -ForegroundColor White
    Write-Host "   3. Run: doctl account get" -ForegroundColor White
} else {
    Write-Host "❌ Installation failed - binary not found" -ForegroundColor Red
}