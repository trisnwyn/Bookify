#!/usr/bin/env bash
# Task 2 probe (CeTZ): vendored package, network namespace closed, two builds.
set -euo pipefail
cd "$(dirname "$0")/.."

TYPST=./tools/typst/typst
STAMP=1750000000

compile() {
  local out="$1"
  bwrap --unshare-net --bind / / --chdir "$PWD" -- \
    "$TYPST" compile \
      --ignore-system-fonts --ignore-embedded-fonts \
      --font-path assets/fonts \
      --package-path vendor/typst \
      --package-cache-path .cache/empty-pkg \
      --creation-timestamp "$STAMP" \
      --root . \
      probe/diagram.typ "$out"
}

echo "typst: $("$TYPST" --version)"
echo "packages:"
for pkg in vendor/typst/preview/*/*/typst.toml; do
  echo "  $(dirname "$pkg") -> $(grep -E '^(name|version)' "$pkg" | tr '\n' ' ')"
done

compile probe/out/diagram.pdf
compile probe/out/diagram-rebuild.pdf
echo "--- hashes ---"
sha256sum probe/out/diagram.pdf probe/out/diagram-rebuild.pdf
cmp probe/out/diagram.pdf probe/out/diagram-rebuild.pdf

pdffonts probe/out/diagram.pdf
pdftoppm -png -r 150 probe/out/diagram.pdf probe/out/diagram

python3 - <<'PY'
import re, subprocess, sys
from pathlib import Path

fonts = subprocess.run(["pdffonts", "probe/out/diagram.pdf"], capture_output=True, text=True).stdout
checks = {
    "vendored cetz present": Path("vendor/typst/preview/cetz/0.5.3/typst.toml").is_file(),
    "no package fetched into the empty cache": not Path(".cache/empty-pkg/preview").exists(),
    "Spectral embedded": "Spectral" in fonts,
    "no unembedded font": not re.search(r"^\S.*\s+no\s+", fonts, re.M),
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
sys.exit(1 if failed else 0)
PY

echo "task 2 CeTZ probe: PASS"
