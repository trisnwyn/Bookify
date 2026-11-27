"""PDF page helpers shared by verification checks."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from bookify import pdf_measure
from bookify.errors import BookifyError
from bookify.verify.checks import Check, failed, passed

LABEL = re.compile(r"^(Figure|Table|Photograph) (\d+)\.")
PHOTOGRAPH_CAPTION = re.compile(r"(?:^[ \t]*|[.!?][ \t]+|[ \t]{2,})Photograph (\d+)\.", re.MULTILINE)


def pdf_info(pdf: Path) -> dict[str, str]:
    return pdf_measure.for_pdf(pdf).info(error_code="VERIFY_FAILED")


def page_texts(pdf: Path) -> list[str]:
    return pdf_measure.for_pdf(pdf).page_texts(error_code="VERIFY_FAILED")


def numbered_labels(texts: list[str]) -> dict[str, int]:
    labels: dict[str, int] = {}
    for page, text in enumerate(texts, start=1):
        for line in text.splitlines():
            match = LABEL.match(line.strip())
            if match:
                labels.setdefault(f"{match.group(1)} {match.group(2)}", page)
    return labels


def illustration_pages(texts: list[str]) -> dict[int, list[str]]:
    pages: dict[int, list[str]] = {}
    for page, text in enumerate(texts, start=1):
        found = PHOTOGRAPH_CAPTION.findall(text)
        if found:
            pages[page] = sorted({f"Photograph {number}" for number in found})
    return pages


def blank_pages(pdf: Path, threshold: int = 200) -> list[int]:
    """A page is blank when it has no text and almost no ink."""
    texts = page_texts(pdf)
    candidates = [index for index, text in enumerate(texts, start=1) if not text.strip()]
    blanks: list[int] = []
    with tempfile.TemporaryDirectory() as directory:
        for index in candidates:
            prefix = Path(directory) / f"page-{index:04d}"
            result = subprocess.run(
                ["pdftoppm", "-png", "-r", "50", "-f", str(index), "-l", str(index), str(pdf), str(prefix)],
                capture_output=True, text=True, check=False,
            )
            if result.returncode != 0:
                raise BookifyError("VERIFY_FAILED", f"pdftoppm failed on page {index}", str(pdf))
            rendered = sorted(Path(directory).glob(f"page-{index:04d}-*.png"))
            if len(rendered) != 1:
                raise BookifyError(
                    "VERIFY_FAILED",
                    f"expected one rendered image for page {index}, found {len(rendered)}",
                    f"{pdf}#page={index}",
                )
            try:
                with Image.open(rendered[0]) as source:
                    image = source.convert("L")
            except OSError as error:
                raise BookifyError(
                    "VERIFY_FAILED",
                    f"cannot read rendered page {index}: {error}",
                    f"{pdf}#page={index}",
                ) from error
            pixels = image.load()
            width, height = image.size
            ink = sum(1 for y in range(height) for x in range(width) if pixels[x, y] < 200)
            if ink < threshold:
                blanks.append(index)
    return blanks


def check_geometry(pdf: Path) -> Check:
    info = pdf_info(pdf)
    size = info.get("Page size", "")
    pages = int(info["Pages"])
    if "595.276 x 841.89 pts (A4)" not in size:
        return failed("pages", "BUILD_FAILED", f"not A4: {size}", pageSize=size)
    blanks = blank_pages(pdf)
    if blanks:
        return failed("pages", "BUILD_FAILED", f"blank page(s): {blanks}", pages=pages, blanks=blanks)
    return passed("pages", f"{pages} A4 pages, none blank", pages=pages)
