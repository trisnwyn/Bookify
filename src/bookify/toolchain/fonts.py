"""Optional font pack management (CJK Noto Serif CJK JP variable font)."""

from __future__ import annotations

import shutil
import tempfile
import urllib.request
from pathlib import Path

from bookify import runtime
from bookify.errors import BookifyError
from bookify.toolchain import pins

CJK_FONT_FILENAME = "NotoSerifCJK-VF.ttc"
CJK_FONT_RELATIVE = f"assets/fonts/{CJK_FONT_FILENAME}"
CJK_FONT_SHA256 = "24720ea76c8b13e822059d155cefb0f9f6be1cfdee1e2bb67b61c96067de42c9"
CJK_FONT_URL = (
    "https://github.com/notofonts/noto-cjk/raw/Serif2.003/Serif/Variable/OTC/NotoSerifCJK-VF.ttc"
)


def cjk_status(engine: Path | None = None) -> dict[str, object]:
    root = engine or runtime.engine_root()
    bundled = root / CJK_FONT_RELATIVE
    if bundled.is_file():
        return {
            "pack": "cjk",
            "installed": True,
            "source": "bundled",
            "path": str(bundled),
            "sha256": CJK_FONT_SHA256,
        }
    cached = runtime.fonts_cache_dir() / CJK_FONT_FILENAME
    if cached.is_file():
        digest = pins.file_sha256(cached)
        return {
            "pack": "cjk",
            "installed": digest == CJK_FONT_SHA256,
            "source": "cache",
            "path": str(cached),
            "sha256": digest,
            "sha256Ok": digest == CJK_FONT_SHA256,
        }
    return {
        "pack": "cjk",
        "installed": False,
        "source": None,
        "path": str(cached),
        "installCommand": "bookify fonts install cjk",
    }


def install_cjk(
    *,
    target_dir: Path | None = None,
    from_file: Path | None = None,
    url: str = CJK_FONT_URL,
) -> dict[str, object]:
    """Install the pinned Noto Serif CJK JP variable font into the user font cache."""
    dest_dir = (target_dir or runtime.fonts_cache_dir()).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / CJK_FONT_FILENAME

    if dest.is_file() and pins.file_sha256(dest) == CJK_FONT_SHA256:
        return {"ok": True, "pack": "cjk", "status": "already-installed", "path": str(dest), "sha256": CJK_FONT_SHA256}

    with tempfile.NamedTemporaryFile(dir=dest_dir, prefix=".cjk-", suffix=".tmp", delete=False) as handle:
        tmp_path = Path(handle.name)
    try:
        if from_file is not None:
            source = from_file.expanduser().resolve()
            if not source.is_file():
                raise BookifyError("INPUT_INVALID", f"font file not found: {source}", str(source))
            shutil.copyfile(source, tmp_path)
        else:
            try:
                urllib.request.urlretrieve(url, tmp_path)
            except Exception as error:  # noqa: BLE001
                raise BookifyError(
                    "FONT_MISSING",
                    f"failed to download CJK font pack from {url}: {error}",
                    url,
                ) from error

        digest = pins.file_sha256(tmp_path)
        if digest != CJK_FONT_SHA256:
            raise BookifyError(
                "FONT_MISSING",
                f"CJK font sha256 mismatch: expected {CJK_FONT_SHA256}, got {digest}",
                str(dest),
            )
        tmp_path.replace(dest)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return {"ok": True, "pack": "cjk", "status": "installed", "path": str(dest), "sha256": CJK_FONT_SHA256}
