"""Pure-Python Pillow contact-sheet generator (replaces external ImageMagick dependency)."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from bookify.errors import BookifyError

PAGE_NUMBER = re.compile(r"(\d+)")


def _page_sort_key(path: Path) -> tuple[int, str]:
    matches = PAGE_NUMBER.findall(path.stem)
    return (int(matches[-1]) if matches else 0, path.name)


def render_pdf_pages(pdf: Path, out_dir: Path, *, dpi: int = 120) -> list[Path]:
    """Render PDF pages to PNGs using pdftoppm (or pypdfium2 if installed)."""
    if not pdf.is_file():
        raise BookifyError("INPUT_INVALID", f"PDF not found: {pdf}", str(pdf))
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("page-*.png"):
        stale.unlink()

    if shutil.which("pdftoppm"):
        prefix = out_dir / "page"
        result = subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(prefix)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise BookifyError("BUILD_FAILED", result.stderr.strip() or "pdftoppm failed", str(pdf))
        return sorted(out_dir.glob("page-*.png"), key=_page_sort_key)

    try:
        import pypdfium2 as pdfium  # type: ignore[import-not-found]
    except ImportError as error:
        raise BookifyError(
            "BUILD_FAILED",
            "cannot render PDF pages: install Poppler (pdftoppm) or pypdfium2",
            str(pdf),
        ) from error

    doc = pdfium.PdfDocument(str(pdf))
    rendered: list[Path] = []
    scale = dpi / 72.0
    digits = max(2, len(str(len(doc))))
    for index in range(len(doc)):
        page = doc[index]
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        target = out_dir / f"page-{index + 1:0{digits}d}.png"
        pil_image.save(target, format="PNG")
        rendered.append(target)
    return rendered


def build_contact_sheet(
    *,
    out_path: Path,
    pdf: Path | None = None,
    pages_dir: Path | None = None,
    cols: int = 4,
    dpi: int = 120,
    tile_width: int = 420,
    gap: int = 24,
) -> dict[str, object]:
    """Compose a clean, bordered contact sheet PNG with pure Pillow (no ImageMagick)."""
    if (pdf is None) == (pages_dir is None):
        raise BookifyError("INPUT_INVALID", "contact-sheet requires exactly one of --pdf or --pages-dir")
    if cols < 1:
        raise BookifyError("INPUT_INVALID", "cols must be >= 1", "cols")

    tmp_ctx = tempfile.TemporaryDirectory(prefix="bookify-pages-") if pdf is not None else None
    try:
        if pdf is not None:
            assert tmp_ctx is not None
            images = render_pdf_pages(pdf, Path(tmp_ctx.name), dpi=dpi)
        else:
            assert pages_dir is not None
            if not pages_dir.is_dir():
                raise BookifyError("INPUT_INVALID", f"pages directory not found: {pages_dir}", str(pages_dir))
            images = sorted(pages_dir.glob("*.png"), key=_page_sort_key)

        if not images:
            raise BookifyError("INPUT_INVALID", "no PNG pages found for contact sheet", str(pdf or pages_dir))

        tiles: list[Image.Image] = []
        for path in images:
            with Image.open(path) as img:
                rgb = img.convert("RGB")
                ratio = tile_width / rgb.width
                tile_height = max(1, int(round(rgb.height * ratio)))
                tiles.append(rgb.resize((tile_width, tile_height), Image.Resampling.LANCZOS))

        actual_cols = min(cols, len(tiles))
        rows = math.ceil(len(tiles) / actual_cols)
        cell_h = max(tile.height for tile in tiles)
        canvas_w = gap + actual_cols * (tile_width + gap)
        canvas_h = gap + rows * (cell_h + gap)
        canvas = Image.new("RGB", (canvas_w, canvas_h), (240, 240, 240))
        draw = ImageDraw.Draw(canvas)

        for idx, tile in enumerate(tiles):
            row, col = divmod(idx, actual_cols)
            x = gap + col * (tile_width + gap)
            y = gap + row * (cell_h + gap)
            canvas.paste(tile, (x, y))
            draw.rectangle([x - 1, y - 1, x + tile.width, y + tile.height], outline=(196, 196, 196), width=1)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, format="PNG")
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()

    return {
        "ok": True,
        "contactSheet": str(out_path),
        "pages": len(tiles),
        "columns": actual_cols,
        "rows": rows,
        "size": [canvas_w, canvas_h],
    }
