"""Deterministic extraction of pages, text and embedded images.

Every Poppler command goes through :mod:`bookify.intake.sandbox`: list argv, a
per-command timeout and the default `bwrap --unshare-net` boundary. The source
is mounted read-only and only the intake output directory is writable.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from bookify.errors import BookifyError
from bookify.intake.caps import CAP_PAGES, CAP_PDF_BYTES
from bookify.intake.sandbox import SandboxPolicy, run as sandbox_run


@dataclass(frozen=True)
class ImageInfo:
    index: int
    width: int
    height: int
    page: int
    kind: str = "image"


def _command_env() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
    }


def policy_for(out: Path, *, offline: bool = True, allow_unsandboxed: bool = False) -> SandboxPolicy:
    """The extraction policy: the output directory is the only writer.

    Paths are resolved once, before bwrap sees them; a relative bind target is
    resolved against bwrap's own cwd and would look read-only.
    """
    target = out.resolve()
    return SandboxPolicy(
        offline=offline,
        timeout=60.0,
        env=_command_env(),
        workdir=target,
        writable_dirs=(target,),
        allow_unsandboxed=allow_unsandboxed,
    )


def _run(args: list[str], policy: SandboxPolicy | None = None) -> str:
    effective = policy or policy_for(Path.cwd())
    result = sandbox_run(args, effective)
    if result.returncode != 0:
        raise BookifyError(
            "SOURCE_UNREADABLE",
            result.stderr.decode("utf-8", "replace").strip()[:400] or "command failed",
            args[0],
        )
    return result.stdout.decode("utf-8", "replace")


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preflight(path: Path, policy: SandboxPolicy) -> int:
    """Enforce the source-size and page-count caps before any page is read.

    Fails with `INPUT_INVALID` and names the measured value and the cap, so an
    oversized source can never start extraction and leave a partial manifest.
    """
    if not path.is_file():
        raise BookifyError("SOURCE_UNREADABLE", f"source not found: {path}", str(path))
    size = path.stat().st_size
    if size > CAP_PDF_BYTES:
        raise BookifyError(
            "INPUT_INVALID",
            f"source is {size} bytes, over the {CAP_PDF_BYTES}-byte cap",
            f"source:{path.name}:bytes",
        )
    return page_count(path, policy)


def page_count(path: Path, policy: SandboxPolicy | None = None) -> int:
    info = _run(["pdfinfo", str(path)], policy)
    match = re.search(r"^Pages:\s+(\d+)$", info, re.M)
    if match is None:
        raise BookifyError("SOURCE_UNREADABLE", "pdfinfo reported no page count", str(path))
    count = int(match.group(1))
    if count > CAP_PAGES:
        raise BookifyError(
            "INPUT_INVALID",
            f"source has {count} pages, over the {CAP_PAGES}-page cap",
            f"source:{path.name}:pages",
        )
    return count


def page_text(path: Path, page: int, policy: SandboxPolicy | None = None) -> str:
    raw = _run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(path), "-"],
        policy,
    )
    return raw.replace("\r\n", "\n").replace("\f", "")


def list_images(path: Path, page: int, policy: SandboxPolicy | None = None) -> list[ImageInfo]:
    """Every row, including soft masks, so extraction output can be paired positionally."""
    listing = _run(["pdfimages", "-list", "-f", str(page), "-l", str(page), str(path)], policy)
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


def extract_images(
    path: Path, page: int, target_dir: Path, policy: SandboxPolicy | None = None
) -> list[Path]:
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    for stale in target_dir.glob("img-*.png"):
        stale.unlink()
    prefix = target_dir / "img"
    _run(
        ["pdfimages", "-png", "-f", str(page), "-l", str(page), str(path), str(prefix)],
        policy,
    )
    return sorted(target_dir.glob("img-*.png"))


__all__ = [
    "ImageInfo",
    "extract_images",
    "list_images",
    "page_count",
    "page_text",
    "policy_for",
    "preflight",
    "source_sha256",
]
