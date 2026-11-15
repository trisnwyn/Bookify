"""D2: the designed typographic cover, measured from the rendered first page.

The cover is metadata-driven: title, optional subtitle, institution, a real
chapter index (or the documented ledger motif), and a footer line. No folio, no
colour, no stock image, nothing outside the text measure enforced by the body
measure and page margin.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from bookify.design import tokens
from bookify.manuscript import model
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks import captions as captions_check
from bookify.verify.checks.pages import pdf_info

# The pinned faces report a line box of 1.5217 em through `pdftotext -bbox`
# (34 pt title -> 51.75 pt box). The size is derived, never guessed.
LINE_BOX_EM = 1.5217
TITLE_SIZE_PT = 34.0
TITLE_SIZE_TOLERANCE_PT = 1.0
RULE_DPI = 300
RULE_DARK = 200
RULE_MIN_FRACTION = 0.9
RULE_MAX_ROWS = 5
# A folio would sit in the bottom margin band; an index number sits in the body.
FOLIO_BAND_PT = 10.0


def _stream(text: str) -> str:
    return re.sub(r"[\s\u00ad]", "", text)


def _page_size(pdf: Path) -> tuple[float, float]:
    info = pdf_info(pdf)
    match = re.match(r"([0-9.]+) x ([0-9.]+) pts", info.get("Page size", ""))
    if not match:
        raise RuntimeError(f"cannot read page size: {info.get('Page size')}")
    return float(match.group(1)), float(match.group(2))


def raster(pdf: Path, page: int, dpi: int) -> np.ndarray:
    with tempfile.TemporaryDirectory() as directory:
        prefix = Path(directory) / f"page-{page:04d}"
        result = subprocess.run(
            [
                "pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
                "-singlefile", str(pdf), str(prefix),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pdftoppm failed on page {page}")
        with Image.open(f"{prefix}.png") as source:
            return np.asarray(source.convert("RGB"))


def rules(image: np.ndarray, measure_px: int) -> list[int]:
    """Rows that draw a near-full-measure thin rule; returned as run row counts."""
    dark = (np.asarray(Image.fromarray(image).convert("L")) < RULE_DARK).sum(axis=1)
    rows = np.where(dark >= measure_px * RULE_MIN_FRACTION)[0]
    runs: list[int] = []
    if rows.size == 0:
        return runs
    start = previous = int(rows[0])
    for row in rows[1:]:
        row = int(row)
        if row - previous > 1:
            runs.append(previous - start + 1)
            start = row
        previous = row
    runs.append(previous - start + 1)
    return runs


def _images_on_first_page(pdf: Path) -> int:
    result = subprocess.run(
        ["pdfimages", "-list", "-f", "1", "-l", "1", str(pdf)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return 0
    return sum(1 for line in result.stdout.splitlines() if re.match(r"^\s*\d+\s+\d+\s+\w+", line))


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    metadata = manuscript.data["metadata"]
    page_width, page_height = _page_size(pdf)
    margin = (page_width - tokens.BODY_MEASURE_PT) / 2
    measure_right = margin + tokens.BODY_MEASURE_PT
    lines = [line for line in captions_check.read_lines(pdf) if line.page == 1]

    problems: list[str] = []
    evidence: dict[str, object] = {}

    folio = [
        line.text
        for line in lines
        if re.fullmatch(r"\d+", line.text.strip())
        and line.y_min > page_height - margin - FOLIO_BAND_PT
    ]
    if folio:
        problems.append(f"cover carries a folio: {folio[0]}")

    # Title: consecutive lines that continue the metadata title.
    expected = _stream(metadata["title"])
    start = next(
        (index for index, line in enumerate(lines) if _stream(line.text) and expected.startswith(_stream(line.text))),
        None,
    )
    title_lines: list[captions_check.LineBox] = []
    if start is None:
        problems.append("cover title is not rendered")
    else:
        consumed = 0
        for line in lines[start:]:
            stream = _stream(line.text)
            if not stream or not expected[consumed:].startswith(stream):
                break
            title_lines.append(line)
            consumed += len(stream)
            if consumed >= len(expected):
                break
        if consumed < len(expected):
            problems.append("cover title is not rendered completely")
        elif len(title_lines) > tokens.COVER_TITLE_MAX_LINES:
            problems.append(f"cover title uses {len(title_lines)} lines")
        else:
            height = title_lines[0].y_max - title_lines[0].y_min
            size = height / LINE_BOX_EM
            evidence["titleSizePt"] = round(size, 2)
            evidence["titleLines"] = len(title_lines)
            if abs(size - TITLE_SIZE_PT) > TITLE_SIZE_TOLERANCE_PT:
                problems.append(f"cover title measures {size:.2f} pt, not {TITLE_SIZE_PT}")

    if "subtitle" in metadata:
        if _stream(metadata["subtitle"]) not in _stream("\n".join(line.text for line in lines)):
            problems.append("cover subtitle is not rendered")
    if "institution" in metadata:
        if _stream(metadata["institution"]) not in _stream("\n".join(line.text for line in lines)):
            problems.append("cover institution meta line is not rendered")
    for optional in ("author", "course"):
        if optional in metadata:
            if _stream(metadata[optional]) not in _stream("\n".join(line.text for line in lines)):
                problems.append(f"cover footer is missing {optional}")

    colour = raster(pdf, 1, 150)
    chromatic = int(
        np.count_nonzero((colour[:, :, 0] != colour[:, :, 1]) | (colour[:, :, 1] != colour[:, :, 2]))
    )
    evidence["chromaticPixels"] = chromatic
    if chromatic:
        problems.append(f"cover has {chromatic} chromatic pixels")

    rule_rows = rules(raster(pdf, 1, RULE_DPI), int(tokens.BODY_MEASURE_PT * RULE_DPI / 72))
    evidence["rules"] = rule_rows
    if not rule_rows:
        problems.append("cover has no full-measure rule")
    elif any(rows > RULE_MAX_ROWS for rows in rule_rows):
        problems.append(f"cover rule is heavier than 0.6 pt: {rule_rows}")

    images = _images_on_first_page(pdf)
    evidence["images"] = images
    if images:
        problems.append(f"cover carries {images} image(s)")

    # Margins are measured from rendered ink, not from Poppler's line box: the
    # box is 1.52 em tall and overstates a large first line.
    grey = np.asarray(Image.fromarray(colour).convert("L"))
    ink_rows = np.where((grey < RULE_DARK).any(axis=1))[0]
    ink_columns = np.where((grey < RULE_DARK).any(axis=0))[0]
    scale = 72 / 150
    ink = {
        "leftPt": round(float(ink_columns[0]) * scale, 2),
        "rightPt": round(float(ink_columns[-1] + 1) * scale, 2),
        "topPt": round(float(ink_rows[0]) * scale, 2),
        "bottomPt": round(float(ink_rows[-1] + 1) * scale, 2),
    }
    evidence["inkBounds"] = ink
    if (
        ink["leftPt"] < margin - 2.0
        or ink["rightPt"] > measure_right + 3.0
        or ink["topPt"] < margin - 2.0
        or ink["bottomPt"] > page_height - margin + 2.0
    ):
        problems.append(f"cover ink leaves the text block: {ink}")

    cover = normalize_cover(manuscript)
    evidence["indexMode"] = cover["indexMode"]
    evidence["entries"] = len(cover["index"])
    page_stream = _stream("\n".join(line.text for line in lines))
    if cover["indexMode"] == "list":
        for entry in cover["index"]:
            if _stream(f"{entry['number']}{entry['title']}") not in page_stream:
                problems.append(f"cover index is missing its entry: {entry['number']} {entry['title']}")
    else:
        evidence["ledger"] = True
        if any(_stream(entry["title"]) in page_stream for entry in cover["index"]):
            problems.append("ledger cover prints a chapter list")

    if problems:
        return failed("cover", "VERIFY_FAILED", "; ".join(problems[:4]), problems=problems, **evidence)
    return passed(
        "cover",
        f"cover rendered: {len(title_lines)} title line(s), {len(rule_rows)} rule(s), {cover['indexMode']} index",
        **evidence,
    )


def normalize_cover(manuscript: model.Manuscript) -> dict[str, object]:
    """The cover decision the renderer made, recomputed from the manuscript."""
    from bookify.publish import normalize

    numbers = normalize.section_numbers(manuscript)
    index = [
        {"number": item["printed"], "title": section["title"], "role": item["role"]}
        for section, item in zip(manuscript.sections, numbers)
        if item["level"] == 1
    ]
    return {
        "index": index,
        "indexMode": "list" if len(index) <= tokens.COVER_INDEX_LIMIT else "ledger",
    }
