#!/usr/bin/env bash
# Task 2 probe: Matplotlib chart with sockets blocked, rendered twice and hashed.
set -euo pipefail
cd "$(dirname "$0")/.."

export MPLCONFIGDIR="$PWD/.cache/mpl"
export MPLBACKEND=Agg
mkdir -p "$MPLCONFIGDIR" probe/out

run_twice() {
  for attempt in 1 2; do
    bwrap --unshare-net --bind / / --chdir "$PWD" -- .venv/bin/python - "$attempt" <<'PY'
import socket, runpy, sys

def deny(*_args, **_kwargs):
    raise RuntimeError("NETWORK_DENIED")

socket.socket = deny
socket.create_connection = deny
socket.getaddrinfo = deny

sys.argv = ["probe/chart.py"]
runpy.run_path("probe/chart.py", run_name="__main__")
PY
    cp probe/out/chart.svg "probe/out/chart-run${attempt}.svg"
  done
}

echo "python: $(.venv/bin/python -V) at $(.venv/bin/python -c 'import sys; print(sys.executable)')"
echo "matplotlib: $(.venv/bin/python -c 'import matplotlib; print(matplotlib.__version__)')"
echo "numpy: $(.venv/bin/python -c 'import numpy; print(numpy.__version__)')"
run_twice
echo "--- hashes ---"
sha256sum probe/out/chart-run1.svg probe/out/chart-run2.svg
cmp probe/out/chart-run1.svg probe/out/chart-run2.svg
echo "--- labels ---"
grep -oE ">(Alder|Birch|Cedar|Samples recorded|Not recorded|72|64|58|28|36|42)<" probe/out/chart-run1.svg | sort -u
echo "--- assertions ---"
python3 - <<'PY'
import sys

svg = open("probe/out/chart-run1.svg", encoding="utf-8").read()
checks = {
    "direct value labels": all(f">{v}<" in svg for v in ("72", "64", "58", "28", "36", "42")),
    "category labels": all(f">{c}<" in svg for c in ("Alder", "Birch", "Cedar")),
    "series labels": "Samples recorded" in svg and "Not recorded" in svg,
    "no timestamp metadata": "dc:date" not in svg and "2026" not in svg,
    "vector only (no raster)": "<image" not in svg,
    "accent token present": "#2f3e5c" in svg.lower(),
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
sys.exit(1 if failed else 0)
PY

echo "task 2 probe: PASS"
