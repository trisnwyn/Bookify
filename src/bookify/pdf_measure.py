"""Shared PDF measurement cache: batch Poppler extraction and raster caching.

A single ``PdfMeasure`` per PDF file (invalidated by path, mtime and size)
eliminates redundant per-page ``pdftotext``, ``pdftohtml`` and ``pdftoppm``
subprocesses across ``publish.report``, ``publish.readability`` and all
``verify.checks.*`` modules while preserving clean module boundaries.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from bookify.design import tokens
from bookify.errors import BookifyError

if TYPE_CHECKING:
    import numpy as np

HTML_NS = "http://www.w3.org/1999/xhtml"
LABEL = re.compile(r"^(Figure|Table|Photograph) (\d+)\.")


@dataclass(frozen=True)
class LineBox:
    page: int
    page_width: float
    text: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def centre(self) -> float:
        return (self.x_min + self.x_max) / 2

    @property
    def delta_pt(self) -> float:
        return self.centre - self.page_width / 2

    def delta_to(self, centre: float) -> float:
        return self.centre - centre


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _run_tool(command: list[str], pdf: Path, error_code: str, detail: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
        )
    except OSError as error:
        raise BookifyError(error_code, f"{command[0]} unavailable: {error}", str(pdf)) from error
    if result.returncode != 0:
        stderr = result.stderr.strip()[:300]
        message = f"{detail}: {stderr}" if stderr else detail
        raise BookifyError(error_code, message, str(pdf))
    return result


class PdfMeasure:
    """Lazy, cached batch measurements of one PDF file."""

    def __init__(self, pdf: Path) -> None:
        self.pdf = pdf
        self._info: dict[str, str] | None = None
        self._texts: list[str] | None = None
        self._bbox_pages: dict[int, tuple[float, float, list[tuple[str, float, float, float, float]]]] | None = None
        self._line_boxes: tuple[LineBox, ...] | None = None
        self._grouped: dict[int, list[str]] = {}
        self._figure_boxes: dict[int, list[tuple[float, float, float, float]]] | None = None
        self._rasters_rgb: dict[tuple[int, int], "np.ndarray"] = {}

    def info(self, *, error_code: str = "VERIFY_FAILED") -> dict[str, str]:
        if self._info is None:
            result = _run_tool(["pdfinfo", str(self.pdf)], self.pdf, error_code, "pdfinfo failed")
            parsed: dict[str, str] = {}
            for line in result.stdout.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    parsed[key.strip()] = value.strip()
            self._info = parsed
        return dict(self._info)

    def page_count(self, *, error_code: str = "VERIFY_FAILED") -> int:
        info = self.info(error_code=error_code)
        raw = info.get("Pages")
        if raw is None or not raw.isdigit():
            raise BookifyError(error_code, f"cannot read page count from pdfinfo: {raw!r}", str(self.pdf))
        return int(raw)

    def page_size(self, *, error_code: str = "VERIFY_FAILED") -> tuple[float, float]:
        info = self.info(error_code=error_code)
        size = info.get("Page size", "")
        width_match = re.search(r"([0-9.]+)\s*x", size)
        height_match = re.search(r"x\s*([0-9.]+)\s*pts", size)
        if not width_match or not height_match:
            raise BookifyError(error_code, f"cannot read page size: {size}", str(self.pdf))
        return float(width_match.group(1)), float(height_match.group(1))

    def page_texts(self, *, error_code: str = "VERIFY_FAILED") -> list[str]:
        """Per-page ``pdftotext -layout`` strings from one batch invocation."""
        if self._texts is None:
            count = self.page_count(error_code=error_code)
            result = _run_tool(
                ["pdftotext", "-layout", str(self.pdf), "-"],
                self.pdf,
                error_code,
                "pdftotext -layout failed",
            )
            parts = result.stdout.split("\f")
            # `pdftotext` emits one form-feed after every page; match per-page
            # `pdftotext -layout -f i -l i` output (which ends with `\f`).
            if len(parts) == count + 1 and parts[-1] == "":
                self._texts = [chunk + "\f" for chunk in parts[:count]]
            elif len(parts) == count:
                self._texts = [chunk + "\f" for chunk in parts]
            else:
                # Fallback to per-page extraction if a page body contained a literal form-feed.
                pages: list[str] = []
                for index in range(1, count + 1):
                    page_result = _run_tool(
                        ["pdftotext", "-layout", "-f", str(index), "-l", str(index), str(self.pdf), "-"],
                        self.pdf,
                        error_code,
                        f"pdftotext failed on page {index}",
                    )
                    pages.append(page_result.stdout)
                self._texts = pages
        return list(self._texts)

    def _load_bbox(self, *, error_code: str = "VERIFY_FAILED") -> None:
        if self._bbox_pages is not None:
            return
        result = _run_tool(
            ["pdftotext", "-bbox-layout", str(self.pdf), "-"],
            self.pdf,
            error_code,
            "pdftotext -bbox-layout failed",
        )
        try:
            root = ET.fromstring(result.stdout)
        except ET.ParseError as error:
            raise BookifyError(error_code, f"cannot parse PDF line boxes: {error}", str(self.pdf)) from error

        pages: dict[int, tuple[float, float, list[tuple[str, float, float, float, float]]]] = {}
        boxes: list[LineBox] = []
        for page_index, page_node in enumerate(root.iter(f"{{{HTML_NS}}}page"), start=1):
            width = float(page_node.attrib.get("width", "0"))
            height = float(page_node.attrib.get("height", "0"))
            page_lines: list[tuple[str, float, float, float, float]] = []
            for line in page_node.iter(f"{{{HTML_NS}}}line"):
                words = [word.text or "" for word in line.iter(f"{{{HTML_NS}}}word")]
                text = _normalise(" ".join(words))
                if not text:
                    continue
                x_min = float(line.attrib["xMin"])
                x_max = float(line.attrib["xMax"])
                y_min = float(line.attrib["yMin"])
                y_max = float(line.attrib["yMax"])
                page_lines.append((text, x_min, x_max, y_min, y_max))
                boxes.append(
                    LineBox(
                        page=page_index,
                        page_width=width,
                        text=text,
                        x_min=x_min,
                        x_max=x_max,
                        y_min=y_min,
                        y_max=y_max,
                    )
                )
            pages[page_index] = (width, height, page_lines)
        self._bbox_pages = pages
        self._line_boxes = tuple(boxes)

    def bbox_lines(
        self, page: int, *, error_code: str = "BUILD_FAILED"
    ) -> tuple[float, float, list[tuple[str, float, float, float, float]]]:
        self._load_bbox(error_code=error_code)
        assert self._bbox_pages is not None
        width, height, lines = self._bbox_pages.get(page, (0.0, 0.0, []))
        return width, height, list(lines)

    def line_boxes(self, *, error_code: str = "VERIFY_FAILED") -> tuple[LineBox, ...]:
        self._load_bbox(error_code=error_code)
        assert self._line_boxes is not None
        if not self._line_boxes:
            raise BookifyError(error_code, "no text lines found in the PDF", str(self.pdf))
        return self._line_boxes

    def grouped_page_lines(self, page: int, *, error_code: str = "BUILD_FAILED") -> list[str]:
        if page not in self._grouped:
            _width, _height, lines = self.bbox_lines(page, error_code=error_code)
            grouped: list[list[float | list[tuple[float, str]]]] = []
            for text, x_min, _x_max, y_min, y_max in sorted(lines, key=lambda line: (round(line[3], 1), line[1])):
                if grouped and abs(float(grouped[-1][0]) - y_min) < 1.0 and abs(float(grouped[-1][1]) - y_max) < 1.0:
                    grouped[-1][2].append((x_min, text))  # type: ignore[union-attr]
                else:
                    grouped.append([y_min, y_max, [(x_min, text)]])
            self._grouped[page] = [
                " ".join(text for _x, text in sorted(parts))  # type: ignore[union-attr]
                for _y_min, _y_max, parts in grouped
            ]
        return list(self._grouped[page])

    def numbered_labels(self, *, error_code: str = "BUILD_FAILED") -> dict[str, int]:
        """Page map for ``Figure N`` / ``Table N`` / ``Photograph N`` labels."""
        self._load_bbox(error_code=error_code)
        assert self._bbox_pages is not None
        numbered: dict[str, int] = {}
        for page_index in sorted(self._bbox_pages):
            for text, _x_min, _x_max, _y_min, _y_max in self._bbox_pages[page_index][2]:
                match = LABEL.match(text.strip())
                if match:
                    numbered.setdefault(f"{match.group(1)} {match.group(2)}", page_index)
        return numbered

    def figure_boxes(self, *, error_code: str = "BUILD_FAILED") -> dict[int, list[tuple[float, float, float, float]]]:
        if self._figure_boxes is None:
            result = _run_tool(
                ["pdftohtml", "-xml", "-hidden", "-stdout", str(self.pdf)],
                self.pdf,
                error_code,
                "pdftohtml failed to list figure boxes",
            )
            try:
                root = ET.fromstring(result.stdout)
            except ET.ParseError as error:
                raise BookifyError(error_code, f"cannot parse figure boxes: {error}", str(self.pdf)) from error
            boxes: dict[int, list[tuple[float, float, float, float]]] = {}
            for page_node in root.iter("page"):
                number = int(page_node.attrib.get("number", "0"))
                width = float(page_node.attrib.get("width", "0")) or 1.0
                scale = (tokens.BODY_MEASURE_PT + 2 * tokens.PAGE_MARGIN_PT) / width
                for image in page_node.iter("image"):
                    left = float(image.attrib.get("left", "0")) * scale
                    top = float(image.attrib.get("top", "0")) * scale
                    box_width = float(image.attrib.get("width", "0")) * scale
                    height = float(image.attrib.get("height", "0")) * scale
                    boxes.setdefault(number, []).append((left, top, box_width, height))
            self._figure_boxes = boxes
        return {page: list(items) for page, items in self._figure_boxes.items()}

    def raster_rgb(self, page: int, dpi: int, *, error_code: str = "VERIFY_FAILED") -> "np.ndarray":
        key = (page, dpi)
        cached = self._rasters_rgb.get(key)
        if cached is not None:
            return cached
        import numpy as np
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / f"page-{page:04d}"
            _run_tool(
                [
                    "pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
                    "-singlefile", str(self.pdf), str(prefix),
                ],
                self.pdf,
                error_code,
                f"pdftoppm failed on page {page}",
            )
            image_path = Path(f"{prefix}.png")
            if not image_path.is_file():
                raise BookifyError(error_code, f"no raster for page {page}", str(self.pdf))
            with Image.open(image_path) as source:
                array = np.asarray(source.convert("RGB"))
        self._rasters_rgb[key] = array
        return array

    def raster_gray(self, page: int, dpi: int, *, error_code: str = "VERIFY_FAILED") -> "np.ndarray":
        import numpy as np
        from PIL import Image

        rgb = self.raster_rgb(page, dpi, error_code=error_code)
        return np.asarray(Image.fromarray(rgb).convert("L"))


@lru_cache(maxsize=16)
def _cached(resolved: str, mtime_ns: int, size: int) -> PdfMeasure:
    del mtime_ns, size
    return PdfMeasure(Path(resolved))


def for_pdf(pdf: Path) -> PdfMeasure:
    """Return the cached ``PdfMeasure`` for ``pdf``, invalidated on file change."""
    resolved = pdf.resolve()
    try:
        stat = resolved.stat()
    except OSError as error:
        raise BookifyError("INPUT_INVALID", f"pdf not found: {pdf}", str(pdf)) from error
    return _cached(str(resolved), stat.st_mtime_ns, stat.st_size)


def clear_cache() -> None:
    _cached.cache_clear()
