"""Deterministic extraction of pages, text and embedded images."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from bookify.errors import BookifyError


@dataclass(frozen=True)
class ImageInfo:
    index: int
    width: int
    height: int
    page: int
    kind: str = "image"


def _run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise BookifyError("SOURCE_UNREADABLE", result.stderr.strip()[:400] or "command failed", args[0])
    return result.stdout


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def page_count(path: Path) -> int:
    info = _run(["pdfinfo", str(path)])
    match = re.search(r"^Pages:\s+(\d+)$", info, re.M)
    if match is None:
        raise BookifyError("SOURCE_UNREADABLE", "pdfinfo reported no page count", str(path))
    return int(match.group(1))


def page_text(path: Path, page: int) -> str:
    raw = _run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(path), "-"])
    return raw.replace("\r\n", "\n").replace("\f", "")


def list_images(path: Path, page: int) -> list[ImageInfo]:
    """Every row, including soft masks, so extraction output can be paired positionally."""
    listing = _run(["pdfimages", "-list", "-f", str(page), "-l", str(page), str(path)])
    images: list[ImageInfo] = []
    for line in listing.splitlines()[2:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        images.append(
            ImageInfo(
                index=int(parts[1]), width=int(parts[3]), height=int(parts[4]),
                page=page, kind=parts[2],
            )
        )
    return images


def extract_images(path: Path, page: int, target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    for stale in target_dir.glob("img-*.png"):
        stale.unlink()
    prefix = target_dir / "img"
    _run(["pdfimages", "-png", "-f", str(page), "-l", str(page), str(path), str(prefix)])
    return sorted(target_dir.glob("img-*.png"))
