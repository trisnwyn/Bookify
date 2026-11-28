#!/usr/bin/env sh
# Install the Bookify CLI engine from GitHub Releases (Linux / macOS).
# Downloads only the ~2 MB pre-built wheel (no PyPI account or git clone required).
set -eu

REPO="trisnwyn/Bookify"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

echo "Fetching latest Bookify release from GitHub (${REPO})..."
WHEEL_URL="$(
  curl -fsSL "$API_URL" | python3 -c '
import json, sys
data = json.load(sys.stdin)
for asset in data.get("assets", []):
    name = asset.get("name", "")
    if name.endswith(".whl"):
        print(asset["browser_download_url"])
        sys.exit(0)
sys.exit("Error: no .whl asset found in latest GitHub release")
'
)"

echo "Installing wheel: ${WHEEL_URL}"
if command -v uv >/dev/null 2>&1; then
  uv tool install --force "$WHEEL_URL"
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force "$WHEEL_URL"
else
  python3 -m pip install --user --upgrade "$WHEEL_URL"
fi

echo "Installing pinned Typst binary for this OS/architecture..."
if command -v bookify >/dev/null 2>&1; then
  bookify toolchain install
  bookify --version
  echo ""
  echo "Bookify CLI installed! Next, install the AI-agent skill for your platform:"
  echo "  bookify skill install --platform all"
  echo "  # or: npx skills add ${REPO}"
else
  echo "Bookify installed. Ensure your Python/uv tool bin directory is on PATH, then run:"
  echo "  bookify toolchain install && bookify skill install --platform all"
fi
