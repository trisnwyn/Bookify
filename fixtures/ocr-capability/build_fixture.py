#!/usr/bin/env python3
"""Build the Bookify v2 OCR capability fixture.

Standard library plus the pinned Typst binary and Poppler's pdftoppm. Every
input is authored in this directory; no third-party content is fetched.

The build is reproducible: SOURCE_DATE_EPOCH is fixed, Typst writes no
wall-clock metadata beyond it, and pdftoppm PNG output is byte-stable.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TYPST = ROOT / "tools/typst/typst"
FONTS = ROOT / "assets/fonts"
PDFTOPPM = Path("/usr/bin/pdftoppm")
SOURCE_DATE_EPOCH = "1767225600"  # 2026-01-01T00:00:00Z


def run(argv: list[str]) -> None:
    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    proc = subprocess.run(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        raise SystemExit(f"failed: {' '.join(argv)}")


def compile_typst(source: Path, output: Path) -> None:
    run(
        [
            str(TYPST),
            "compile",
            "--root",
            str(HERE),
            "--font-path",
            str(FONTS),
            str(source),
            str(output),
        ]
    )


def rasterise(pdf: Path, dpi: int, output: Path) -> None:
    run(
        [
            str(PDFTOPPM),
            "-r",
            str(dpi),
            "-gray",
            "-png",
            "-singlefile",
            str(pdf),
            str(output.with_suffix("")),
        ]
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="build twice and compare")
    args = parser.parse_args()

    build = HERE / "build"
    build.mkdir(exist_ok=True)

    compile_typst(HERE / "source/trial-balance.typ", build / "trial-balance.pdf")
    compile_typst(HERE / "source/cash-receipts.typ", build / "cash-receipts.pdf")
    rasterise(build / "trial-balance.pdf", 300, build / "trial-balance.png")
    rasterise(build / "cash-receipts.pdf", 300, build / "cash-receipts.png")
    rasterise(build / "trial-balance.pdf", 45, build / "trial-balance-45.png")
    compile_typst(HERE / "source/fixture.typ", HERE / "fixture.pdf")

    first = sha256(HERE / "fixture.pdf")
    print(f"fixture.pdf sha256 {first}")
    for name in (
        "trial-balance.png",
        "cash-receipts.png",
        "trial-balance-45.png",
    ):
        print(f"{name} sha256 {sha256(build / name)}")

    if args.check:
        compile_typst(HERE / "source/fixture.typ", build / "fixture-rebuild.pdf")
        second = sha256(build / "fixture-rebuild.pdf")
        print(f"rebuild sha256 {second}")
        if first != second:
            raise SystemExit("fixture build is not reproducible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
