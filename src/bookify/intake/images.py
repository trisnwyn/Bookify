"""Image naming and content deduplication."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredImage:
    page: int
    index: int
    file: str
    width: int
    height: int
    sha256: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def store(
    source_file: Path,
    page: int,
    index: int,
    width: int,
    height: int,
    image_dir: Path,
    seen: dict[str, str],
) -> StoredImage:
    digest = sha256(source_file)
    relative = f"images/page-{page:03d}-img-{index:02d}.png"
    if digest in seen:
        source_file.unlink(missing_ok=True)
        return StoredImage(page, index, seen[digest], width, height, digest)
    image_dir.mkdir(parents=True, exist_ok=True)
    target = image_dir.parent / relative
    shutil.move(str(source_file), target)
    seen[digest] = relative
    return StoredImage(page, index, relative, width, height, digest)
