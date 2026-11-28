# Install the Bookify CLI engine from GitHub Releases (Windows PowerShell).
# Downloads only the ~2 MB pre-built wheel (no PyPI account or git clone required).
$ErrorActionPreference = "Stop"

$Repo = "trisnwyn/Bookify"
$ApiUrl = "https://api.github.com/repos/$Repo/releases/latest"

Write-Host "Fetching latest Bookify release from GitHub ($Repo)..."
$Release = Invoke-RestMethod -Uri $ApiUrl -Headers @{ "User-Agent" = "bookify-installer" }
$WheelAsset = $Release.assets | Where-Object { $_.name -like "*.whl" } | Select-Object -First 1
if (-not $WheelAsset) {
    throw "No .whl asset found in latest GitHub release for $Repo."
}

$WheelUrl = $WheelAsset.browser_download_url
Write-Host "Installing wheel: $WheelUrl"

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv tool install --force $WheelUrl
} elseif (Get-Command pipx -ErrorAction SilentlyContinue) {
    pipx install --force $WheelUrl
} else {
    python -m pip install --user --upgrade $WheelUrl
}

if (Get-Command bookify -ErrorAction SilentlyContinue) {
    Write-Host "Installing pinned Typst binary for Windows..."
    bookify toolchain install
    bookify --version
    Write-Host ""
    Write-Host "Bookify CLI installed! Next, install the AI-agent skill for your platform:"
    Write-Host "  bookify skill install --platform all"
    Write-Host "  # or: npx skills add $Repo"
} else {
    Write-Host "Bookify installed. Restart your shell (or add uv/Python Scripts to PATH), then run:"
    Write-Host "  bookify toolchain install"
    Write-Host "  bookify skill install --platform all"
}
