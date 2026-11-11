#!/usr/bin/env bash
# Task 1 probe: Typst renders Spectral, Vietnamese, Japanese and an equation
# with only local fonts, no system fonts, no embedded fonts and no network.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p probe/out
TYPST=./tools/typst/typst

echo "typst: $("$TYPST" --version)"

# Offline proof: new network namespace, local fonts and packages only.
bwrap --unshare-net --bind / / --chdir "$PWD" -- \
  "$TYPST" compile \
    --ignore-system-fonts --ignore-embedded-fonts \
    --font-path assets/fonts \
    --package-path vendor/typst \
    --package-cache-path .cache/empty-pkg \
    --root . \
    probe/probe.typ probe/out/probe.pdf

echo "--- pdfinfo ---"
pdfinfo probe/out/probe.pdf | grep -E "Pages|Page size|Creator"
echo "--- pdffonts ---"
pdffonts probe/out/probe.pdf
echo "--- text probes ---"
pdftotext -layout probe/out/probe.pdf probe/out/probe.txt
grep -E "Tiếng Việt có đủ dấu|日本語の文章|∑|≤" probe/out/probe.txt
echo "--- render ---"
pdftoppm -png -r 130 probe/out/probe.pdf probe/out/probe

echo "--- assertions ---"
python3 - <<'PY'
import re, subprocess, sys

text = open("probe/out/probe.txt", encoding="utf-8").read()
info = subprocess.run(["pdfinfo", "probe/out/probe.pdf"], capture_output=True, text=True).stdout
fonts = subprocess.run(["pdffonts", "probe/out/probe.pdf"], capture_output=True, text=True).stdout

checks = {
    "A4 page": "595.276 x 841.89 pts (A4)" in info,
    "single page": re.search(r"^Pages:\s+1$", info, re.M) is not None,
    "Vietnamese extracted": "Tiếng Việt có đủ dấu" in text,
    "Vietnamese diacritics intact": "ế ộ ữ đ ạ ỹ" in text,
    "Japanese extracted": "日本語の文章" in text,
    "math symbols extracted": "∑" in text and "≤" in text,
    "Spectral embedded": "Spectral-Regular" in fonts,
    "CJK embedded": "NotoSerifCJK" in fonts,
    "maths face embedded": "STIXTwoMath" in fonts,
    "no unembedded font": not re.search(r"^\S.*\s+no\s+", fonts, re.M),
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
sys.exit(1 if failed else 0)
PY

echo "task 1 probe: PASS"
