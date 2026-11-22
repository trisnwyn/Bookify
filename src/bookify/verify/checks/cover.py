"""D2: the selected cover composition, measured from the rendered first page.

The cover is metadata plus one authored composition out of seven. This check
measures the page the renderer actually produced: the title's real size on the
axis it was set on, every metadata line, no folio, no colour, and no raster image
unless a rights-checked artwork record was selected. A composition is not
required to print a chapter index or a full-measure rule; the accepted covers do
neither, so requiring them would reject the design. What every cover must do is
keep its ink inside the text block.
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
from bookify.publish import normalize, report
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
# A folio would sit in the bottom margin band; no cover prints one.
FOLIO_BAND_PT = 10.0
# The vertical composition sets its title 90° clockwise, so Poppler reports the
# title line's x extent as the type's line box.
ROTATED_COMPOSITIONS = frozenset({"cover-6"})


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


def cover_state(manuscript: model.Manuscript) -> dict[str, object]:
    """The cover decision the renderer made, recomputed from the manuscript."""
    figure_paths = {
        block["id"]: "unused.svg"
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    }
    return normalize.build(manuscript, figure_paths, draft=True).data["cover"]


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    metadata = manuscript.data["metadata"]
    cover = cover_state(manuscript)
    composition = str(cover["composition"])
    rotated = composition in ROTATED_COMPOSITIONS
    page_width, page_height = _page_size(pdf)
    margin = (page_width - tokens.BODY_MEASURE_PT) / 2
    measure_right = margin + tokens.BODY_MEASURE_PT
    lines = [line for line in captions_check.read_lines(pdf) if line.page == 1]

    problems: list[str] = []
    evidence: dict[str, object] = {
        "composition": composition,
        "selection": cover["selection"],
        "artwork": cover["artwork"],
        "rotatedTitle": rotated,
    }

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
            first = title_lines[0]
            if rotated:
                # A 90° line runs down the page, so its type size is its x extent.
                size = (first.x_max - first.x_min) / LINE_BOX_EM
            else:
                size = (first.y_max - first.y_min) / LINE_BOX_EM
            evidence["titleSizePt"] = round(size, 2)
            evidence["titleLines"] = len(title_lines)
            if abs(size - TITLE_SIZE_PT) > TITLE_SIZE_TOLERANCE_PT:
                problems.append(f"cover title measures {size:.2f} pt, not {TITLE_SIZE_PT}")

    page_stream = _stream("\n".join(line.text for line in lines))
    for field in ("subtitle", "institution", "author", "course"):
        if field in metadata and _stream(metadata[field]) not in page_stream:
            problems.append(f"cover is missing its {field} line")

    colour = raster(pdf, 1, 150)
    chromatic = int(
        np.count_nonzero((colour[:, :, 0] != colour[:, :, 1]) | (colour[:, :, 1] != colour[:, :, 2]))
    )
    evidence["chromaticPixels"] = chromatic
    if chromatic:
        problems.append(f"cover has {chromatic} chromatic pixels")

    if cover["artwork"] == "present":
        # The artwork is a photographic/illustrative field, not ornament; a dark
        # band inside it is not a cover rule. Rule weight is only meaningful on a
        # composition whose surface is typographic.
        evidence["rules"] = []
    else:
        rule_rows = rules(raster(pdf, 1, RULE_DPI), int(tokens.BODY_MEASURE_PT * RULE_DPI / 72))
        evidence["rules"] = rule_rows
        if any(rows > RULE_MAX_ROWS for rows in rule_rows):
            problems.append(f"cover rule is heavier than 0.6 pt: {rule_rows}")

    images = _images_on_first_page(pdf)
    evidence["images"] = images
    if images and cover["artwork"] != "present":
        problems.append(f"cover carries {images} image(s) without an artwork record")

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

    # No accepted composition prints a chapter index. The retired ledger cover
    # printed each entry as the title alone or as `<number> <title>`; only an
    # exact rendered line is that entry. A chapter title that is merely a word in
    # the title, subtitle, institution, course or author is not an index, and a
    # line that is one of those metadata fields is excluded outright.
    numbers = normalize.section_numbers(manuscript)
    index_forms: set[str] = set()
    for section, number in zip(manuscript.sections, numbers):
        if number["level"] != 1:
            continue
        title = _stream(section["title"])
        if not title:
            continue
        index_forms.add(title)
        index_forms.add(_stream(str(number["printed"])) + title)
        index_forms.add(_stream(str(number["printed"])) + " " + title)
    metadata_streams = {
        _stream(value) for value in metadata.values() if isinstance(value, str) and value.strip()
    }
    line_streams = [_stream(line.text) for line in lines if line.text.strip()]
    carried = [
        stream for stream in line_streams
        if stream and stream in index_forms and stream not in metadata_streams
    ]
    evidence["chapterIndex"] = "none"
    if carried:
        problems.append(f"cover prints chapter titles: {len(carried)}")

    # Two cover lines whose glyph ink overlaps make the page unreadable even when
    # every line is inside the text block; the build guard checks this too, so a
    # PDF built elsewhere is measured the same way.
    overlapping = report.cover_overlaps(
        [(line.text, line.x_min, line.x_max, line.y_min, line.y_max) for line in lines]
    )
    evidence["overlaps"] = [list(pair) for pair in overlapping]
    if overlapping:
        first, second = overlapping[0]
        problems.append(f"cover text overlaps: {first[:30]!r} / {second[:30]!r}")

    if problems:
        return failed("cover", "VERIFY_FAILED", "; ".join(problems[:4]), problems=problems, **evidence)
    return passed(
        "cover",
        f"{composition} rendered: {len(title_lines)} title line(s), artwork {cover['artwork']}",
        **evidence,
    )


def normalize_cover(manuscript: model.Manuscript) -> dict[str, object]:
    """Backwards-compatible name for the cover state recomputation."""
    return cover_state(manuscript)
