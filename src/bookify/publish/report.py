"""Build report: pages, numbering, placements, hashes and warnings."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bookify.design import tokens
from bookify.errors import BookifyError

LABEL = re.compile(r"^(Figure|Table|Photograph) (\d+)\.")
HTML_NS = "http://www.w3.org/1999/xhtml"
SIDE_PRESETS = ("side-left", "side-right")
UNIT_TYPES = ("chart", "diagram", "illustration")
PAGE_NUMBER = re.compile(r"^\d+$")
CONTENTS_ENTRY = re.compile(r"(?:\.\s*){2,}\d+\s*$", re.MULTILINE)
# Poppler's line bbox includes glyph side bearings. A justified line set to the
# 475.28 pt measure measures ~2.0 pt wider at the final glyph. This allowance is
# for the build-time fit guard only; the caption and figure-geometry gates keep
# their independent 2.0 pt tolerance.
FIT_GLYPH_OVERHANG_PT = 3.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def composition_entries(document: dict[str, Any], numbered: dict[str, int]) -> list[dict[str, Any]]:
    """Evidence for every visual: its composition, companions, page and deferral.

    A chart or diagram carries no authored composition; it is recorded as the
    full-measure plate the template places it at, so the report covers every
    visual type rather than only illustrations.
    """
    entries: list[dict[str, Any]] = []
    for section in document["sections"]:
        for block in section["blocks"]:
            kind = block.get("type")
            if kind not in UNIT_TYPES:
                continue
            preset = block.get("composition", "full")
            if "companions" in block:
                companion_ids = [companion["id"] for companion in block["companions"]]
            elif "companion" in block:
                companion_ids = [block["companion"]["id"]]
            else:
                companion_ids = []
            entries.append(
                {
                    "blockId": block["id"],
                    "type": kind,
                    "preset": preset,
                    "companionId": companion_ids[0] if companion_ids else None,
                    "companionIds": companion_ids,
                    "page": numbered.get(block.get("label", "")),
                    "deferred": bool(block.get("pagebreak")),
                }
            )
    return entries


def _text_pages(pdf: Path, count: int) -> list[str]:
    pages: list[str] = []
    for index in range(1, count + 1):
        result = subprocess.run(
            ["pdftotext", "-layout", "-f", str(index), "-l", str(index), str(pdf), "-"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise BookifyError("BUILD_FAILED", f"pdftotext failed on page {index}", str(pdf))
        pages.append(result.stdout)
    return pages


def _bbox_lines(pdf: Path, page: int) -> tuple[float, float, list[tuple[str, float, float, float, float]]]:
    """Rendered line boxes on one page: text, xMin, xMax, yMin, yMax."""
    result = subprocess.run(
        ["pdftotext", "-bbox-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise BookifyError("BUILD_FAILED", f"pdftotext -bbox-layout failed on page {page}", str(pdf))
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as error:
        raise BookifyError("BUILD_FAILED", f"cannot parse PDF line boxes: {error}", str(pdf)) from error
    lines: list[tuple[str, float, float, float, float]] = []
    for page_node in root.iter(f"{{{HTML_NS}}}page"):
        width = float(page_node.attrib.get("width", "0"))
        height = float(page_node.attrib.get("height", "0"))
        for line in page_node.iter(f"{{{HTML_NS}}}line"):
            words = [word.text or "" for word in line.iter(f"{{{HTML_NS}}}word")]
            text = " ".join(" ".join(words).split())
            if not text:
                continue
            lines.append(
                (
                    text,
                    float(line.attrib["xMin"]),
                    float(line.attrib["xMax"]),
                    float(line.attrib["yMin"]),
                    float(line.attrib["yMax"]),
                )
            )
        return width, height, lines
    return 0.0, 0.0, lines


def contents_pages(texts: list[str]) -> set[int]:
    """Every contents page, from the `Contents` title to the last dotted entry."""
    start = next(
        (index for index, text in enumerate(texts, start=1) if "Contents" in text and "..." in text.replace(" ", "")),
        None,
    )
    if start is None:
        return set()
    pages = {start}
    for index in range(start + 1, len(texts) + 1):
        text = texts[index - 1].replace("\u2060", "").replace("\u00a0", " ")
        if not CONTENTS_ENTRY.search(text):
            break
        pages.add(index)
    return pages


def _stream(text: str) -> str:
    return re.sub(r"[\s\u00ad]", "", text)


# The pinned faces' line box through `pdftotext -bbox`: 1.059 em above the
# baseline, 0.463 em below it. Glyph ink reaches 0.750 em above and 0.240 em
# below. The difference is the empty part of the box; two lines clash only when
# their *ink* rectangles overlap.
LINE_BOX_EM = 1.5217
INK_TOP_EM = 1.059 - 0.750
INK_BOTTOM_EM = 0.463 - 0.240


def _ink_box(line: tuple[str, float, float, float, float]) -> tuple[float, float, float, float]:
    """The glyph-ink rectangle of one rendered line.

    A rotated line (cover-6) reports its type thickness as the x extent, so the
    box is inset on x instead of y and the text run keeps its full y extent.
    """
    _text, x_min, x_max, y_min, y_max = line
    width, height = x_max - x_min, y_max - y_min
    rotated = height > width * 1.5
    thickness = (width if rotated else height) / LINE_BOX_EM
    if rotated:
        return (x_min + INK_TOP_EM * thickness, x_max - INK_BOTTOM_EM * thickness, y_min + 1.0, y_max - 1.0)
    return (x_min, x_max, y_min + INK_TOP_EM * thickness, y_max - INK_BOTTOM_EM * thickness)


def cover_overlaps(
    lines: list[tuple[str, float, float, float, float]],
) -> list[tuple[str, str]]:
    """Pairs of cover lines whose glyph ink overlaps by more than 0.5 pt."""
    boxes = [(line, _ink_box(line)) for line in lines]
    overlaps: list[tuple[str, str]] = []
    for index, (first, (ax0, ax1, ay0, ay1)) in enumerate(boxes):
        for second, (bx0, bx1, by0, by1) in boxes[index + 1 :]:
            if (
                ax0 < bx1 - 0.5
                and bx0 < ax1 - 0.5
                and ay0 < by1 - 0.5
                and by0 < ay1 - 0.5
            ):
                overlaps.append((first[0], second[0]))
    return overlaps


def section_forms(section: dict[str, Any]) -> set[str]:
    """Every rendered heading line a section can produce.

    A chapter prints `Chapter 1: Title`; a body heading prints `1.1 Title`; the
    contents prints `1 Title`. The report, readability, cross-reference and
    opener checks all read this one list so they agree with the page.
    """
    forms = {section["title"]}
    if section.get("heading"):
        forms.add(section["heading"])
    if section.get("printed"):
        forms.add(f"{section['printed']} {section['title']}")
    return forms


def section_prefix(section: dict[str, Any]) -> str:
    """The printed number that opens a section's heading line.

    A wrapped chapter heading only shows this prefix on its first row, so page
    lookups match the prefix rather than a whole line that may be split.
    """
    printed = section.get("printed")
    if not printed:
        return ""
    if section.get("level", 1) == 1:
        if section.get("role") == "appendix":
            return f"{printed}:"
        return f"Chapter {printed}:"
    return f"{printed} "


def line_is_section(line: str, section: dict[str, Any]) -> bool:
    """Whether one rendered line opens this section's heading."""
    stripped = line.strip()
    if stripped in section_forms(section):
        return True
    prefix = section_prefix(section)
    return bool(prefix) and stripped.startswith(prefix)


def _image_column(composition: str | None, page_width: float) -> tuple[float, float] | None:
    """The declared image column for a side preset, in page points."""
    if composition not in SIDE_PRESETS:
        return None
    margin = (page_width - tokens.BODY_MEASURE_PT) / 2
    width = tokens.BODY_MEASURE_PT * tokens.SIDE_FRACTION
    if composition == "side-left":
        return margin, margin + width
    return margin + tokens.BODY_MEASURE_PT - width, margin + tokens.BODY_MEASURE_PT


def require_unit_fit(
    pdf: Path,
    document: dict[str, Any],
    numbered: dict[str, int],
    page_height: float,
) -> None:
    """A chart/diagram/illustration unit must not paint into the bottom margin.

    Only the unit's own caption and credit are measured: unrelated body prose on
    the same page is allowed to reach the normal bottom margin. A caption that
    cannot be followed completely on one page is detached and fails too.
    """
    margin = tokens.PAGE_MARGIN_PT
    limit = page_height - margin + 2.0
    cache: dict[int, tuple[float, list[tuple[str, float, float, float, float]]]] = {}
    from bookify.manuscript import model as manuscript_model

    columns_by_section = manuscript_model.effective_columns(document["sections"])
    for section_index, section in enumerate(document["sections"]):
        for block in section["blocks"]:
            if block.get("type") not in UNIT_TYPES:
                continue
            label = block.get("label", "")
            page = numbered.get(label)
            if page is None:
                continue
            if page not in cache:
                width, _height, raw = _bbox_lines(pdf, page)
                # Reading order for a caption fragment: top-to-bottom, then
                # left-to-right for same-baseline fragments.
                cache[page] = (width, sorted(raw, key=lambda line: (line[3], line[1])))
            page_width, all_lines = cache[page]
            column = _image_column(block.get("composition"), page_width)
            if column is None and columns_by_section[section_index] == 2:
                # A visual inside a two-column chapter is captioned in its own
                # 229.64 pt column; the adjacent column's prose is interleaved.
                start_line = next(
                    (line for line in all_lines if line[0].startswith(f"{label}.")),
                    None,
                )
                if start_line is not None:
                    margin = (page_width - tokens.BODY_MEASURE_PT) / 2
                    if start_line[1] >= margin + tokens.BODY_MEASURE_PT / 2:
                        left = margin + tokens.COLUMN_WIDTH_PT + tokens.SIDE_GUTTER_PT
                    else:
                        left = margin
                    column = (left, left + tokens.COLUMN_WIDTH_PT)
            if column is None:
                lines = all_lines
            else:
                # A caption shares baselines with prose in the other column; keep
                # only its own column.
                lines = [
                    line for line in all_lines
                    if line[1] >= column[0] - 2.0 and line[2] <= column[1] + 2.0
                ]
            start = next(
                (index for index, line in enumerate(lines) if line[0].startswith(f"{label}.")),
                None,
            )
            if start is None:
                continue
            expected = _stream(block.get("caption", ""))
            consumed = 0
            for index in range(start, len(lines)):
                text, _x_min, _x_max, _y_min, y_max = lines[index]
                stream = _stream(text)
                if not stream:
                    continue
                if not expected[consumed:].startswith(stream):
                    break
                consumed += len(stream)
                if y_max > limit:
                    raise BookifyError(
                        "BUILD_FAILED",
                        f"unit does not fit the text block: {block['id']}",
                        block["id"],
                    )
                if consumed >= len(expected):
                    break
            if consumed < len(expected):
                raise BookifyError(
                    "BUILD_FAILED",
                    f"unit caption is detached or incomplete: {block['id']}",
                    block["id"],
                )
            credit = block.get("credit")
            if credit:
                credit_stream = _stream(credit)
                for text, _x_min, _x_max, _y_min, y_max in lines:
                    stream = _stream(text)
                    if stream and credit_stream.startswith(stream):
                        if y_max > limit:
                            raise BookifyError(
                                "BUILD_FAILED",
                                f"unit credit does not fit the text block: {block['id']}",
                                block["id"],
                            )
                        break


def require_cover_fit(
    pdf: Path,
    document: dict[str, Any],
    page_width: float,
    page_height: float,
) -> int:
    """Fit guard for every cover composition: text stays in the text block.

    The accepted compositions place their blocks differently, so this guard does
    not assume a footer rule or a chapter index. It checks the one invariant they
    share — the title renders completely within the line budget, and no text
    leaves the 60 pt text block. Never clips, shrinks or drops a metadata line; a
    miss is `BUILD_FAILED` with the metadata locator so the author fixes the data
    rather than the template.
    """
    margin = tokens.PAGE_MARGIN_PT
    _width, _height, lines = _bbox_lines(pdf, 1)
    metadata = document["metadata"]
    # A large first line's Poppler box rises above its glyph ink by up to 4.65 pt
    # (measured on the accepted composition 5/7); the raster check in
    # `verify/checks/cover.py` is the ink-accurate gate.
    top_allowance = tokens.COVER_LINE_BOX_TOP_ALLOWANCE_PT

    expected = _stream(metadata["title"])
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if _stream(line[0]) and expected.startswith(_stream(line[0]))
        ),
        None,
    )
    if start is None:
        raise BookifyError("BUILD_FAILED", "cover title was not rendered", "metadata.title")
    consumed = 0
    count = 0
    for index in range(start, len(lines)):
        stream = _stream(lines[index][0])
        if not stream:
            continue
        if not expected[consumed:].startswith(stream):
            break
        consumed += len(stream)
        count += 1
        if consumed >= len(expected):
            break
    if consumed < len(expected):
        raise BookifyError("BUILD_FAILED", "cover title was not rendered completely", "metadata.title")
    if count > tokens.COVER_TITLE_MAX_LINES:
        raise BookifyError(
            "BUILD_FAILED",
            f"cover title needs {count} lines; the maximum is {tokens.COVER_TITLE_MAX_LINES}",
            "metadata.title",
        )

    measure_right = margin + tokens.BODY_MEASURE_PT
    for text, x_min, x_max, y_min, y_max in lines:
        if y_max > page_height - margin + 2.0 or y_min < margin - top_allowance:
            raise BookifyError(
                "BUILD_FAILED",
                "cover text leaves the text block vertically",
                f"metadata:{text[:40]}",
            )
        if x_max > measure_right + FIT_GLYPH_OVERHANG_PT or x_min < margin - FIT_GLYPH_OVERHANG_PT:
            raise BookifyError(
                "BUILD_FAILED",
                "cover text leaves the text measure",
                f"metadata:{text[:40]}",
            )
    overlapping = cover_overlaps(lines)
    if overlapping:
        first, second = overlapping[0]
        raise BookifyError(
            "BUILD_FAILED",
            f"cover text overlaps: {first[:30]!r} / {second[:30]!r}",
            "metadata.cover.composition",
        )
    return count


def text_measure_width(
    pdf: Path,
    page: int,
    x_left: float,
    expected: float,
) -> float | None:
    """The rendered measure of a text column, from its justified body lines.

    A chart or diagram is native vector content: Poppler reports no image XObject
    for it, so its placed box cannot be read from the document structure. The
    visual is placed at 100 % of its container, so the container's own measure —
    measured from the justified body lines that share it — is the width the
    visual really occupies. Returns ``None`` when no body line fills the
    container (for example a page that carries only the figure).
    """
    if expected <= 1.0:
        return None
    _width, _height, lines = _bbox_lines(pdf, page)
    body = [
        line for line in lines
        if abs((line[4] - line[3]) / LINE_BOX_EM - tokens.BODY_SIZE_PT) <= 0.3
        and line[1] >= x_left - 1.0
        and line[2] <= x_left + expected + 4.0
    ]
    # A justified line ends at the container's right edge (or ~2 pt past it with
    # hanging punctuation). Only such a line measures the container; a short last
    # line or a ragged note never does.
    hits = sorted(
        line[2] for line in body
        if abs(line[2] - (x_left + expected)) <= 3.0
    )
    if not hits:
        return None
    return hits[len(hits) // 2] - x_left


def figure_boxes(pdf: Path) -> dict[int, list[tuple[float, float, float, float]]]:
    """Every placed image/figure box per page: (left, top, width, height) in points.

    Poppler's XML export reports the placed box of each XObject, including
    vector charts and diagrams it rasterises for the export. This is the
    measured width of a plate, not the width the template asked for.
    """
    result = subprocess.run(
        ["pdftohtml", "-xml", "-hidden", "-stdout", str(pdf)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise BookifyError("BUILD_FAILED", "pdftohtml failed to list figure boxes", str(pdf))
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as error:
        raise BookifyError("BUILD_FAILED", f"cannot parse figure boxes: {error}", str(pdf)) from error
    boxes: dict[int, list[tuple[float, float, float, float]]] = {}
    for page_node in root.iter("page"):
        number = int(page_node.attrib.get("number", "0"))
        width = float(page_node.attrib.get("width", "0")) or 1.0
        # The XML is emitted at a rounded pixel width; the page's real width is
        # the A4 measure plus margins, so derive the scale from the page box.
        scale = (tokens.BODY_MEASURE_PT + 2 * tokens.PAGE_MARGIN_PT) / width
        for image in page_node.iter("image"):
            left = float(image.attrib.get("left", "0")) * scale
            top = float(image.attrib.get("top", "0")) * scale
            box_width = float(image.attrib.get("width", "0")) * scale
            height = float(image.attrib.get("height", "0")) * scale
            boxes.setdefault(number, []).append((left, top, box_width, height))
    return boxes


def plate_entries(
    pdf: Path,
    document: dict[str, Any],
    numbered: dict[str, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """D4: one substantive plate per chapter where the material supports it.

    Visuals in level-2/3/4 sections belong to their nearest level-1 chapter. Only
    a visual placed at the full text measure is a plate: a centred visual keeps
    its figure width and a side visual its declared column, and both are recorded
    as `visuals` with the width they really occupy. A raster illustration's width
    is measured from its placed box; a vector chart or diagram carries no image
    object, so its width is the declared `measure.plate` the template places it
    at. A chapter with a visual and no plate records the authored `noPlate`
    reason (never a bare placeholder); without a reason it is a gap the review
    must answer.
    """
    boxes = figure_boxes(pdf)
    tolerance = tokens.PLATE_TOLERANCE_PT
    plates: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    visuals: list[dict[str, Any]] = []

    chapters: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    current: tuple[dict[str, Any], list[dict[str, Any]]] | None = None
    for section in document["sections"]:
        blocks = [
            block
            for block in section["blocks"]
            if block.get("type") in {"chart", "diagram", "illustration"} and "label" in block
        ]
        if section.get("level", 1) == 1:
            current = (section, list(blocks))
            chapters.append(current)
        elif current is not None:
            current[1].extend(blocks)

    for chapter, blocks in chapters:
        if not blocks:
            continue
        two_column = (chapter.get("layout") or {}).get("columns") == 2
        found: list[dict[str, Any]] = []
        for block in blocks:
            page = numbered.get(block["label"])
            if page is None:
                continue
            preset = block.get("composition", "full") if block["type"] == "illustration" else "full"
            common = {
                "chapter": chapter.get("printed"),
                "blockId": block["id"],
                "label": block["label"],
                "page": page,
            }
            if two_column:
                # A visual inside an authored two-column chapter takes one
                # 229.64 pt column; it is never a full-measure plate.
                expected = tokens.COLUMN_WIDTH_PT
                measured = next(
                    (box for box in boxes.get(page, []) if abs(box[2] - expected) <= tolerance),
                    None,
                )
                width = measured[2] if measured is not None else None
                left = measured[0] if measured is not None else None
                if width is None and block["type"] in {"chart", "diagram"}:
                    margin = tokens.PAGE_MARGIN_PT
                    mid = margin + tokens.BODY_MEASURE_PT / 2
                    caption = next(
                        (line for line in _bbox_lines(pdf, page)[2]
                         if line[0].startswith(f"{block['label']}.")),
                        None,
                    )
                    right = caption is not None and caption[1] >= mid
                    left = mid + tokens.SIDE_GUTTER_PT / 2 if right else margin
                    width = text_measure_width(pdf, page, left, tokens.COLUMN_WIDTH_PT)
                visuals.append(
                    {
                        **common,
                        "preset": preset,
                        "widthPt": round(width if width is not None else expected, 2),
                        "leftPt": None if left is None else round(left, 2),
                        "basis": "measured" if width is not None else "declared",
                        "column": True,
                    }
                )
                continue
            if preset == "full":
                expected = tokens.PLATE_PT
                measured = next(
                    (box for box in boxes.get(page, []) if abs(box[2] - expected) <= tolerance),
                    None,
                )
                width = measured[2] if measured is not None else None
                left = measured[0] if measured is not None else None
                if width is None and block["type"] in {"chart", "diagram"}:
                    width = text_measure_width(pdf, page, tokens.PAGE_MARGIN_PT, tokens.PLATE_PT)
                if width is not None:
                    found.append(
                        {**common, "widthPt": round(width, 2),
                         "leftPt": None if left is None else round(left, 2), "basis": "measured"}
                    )
                else:
                    # A diagram is a native vector drawing with no image object;
                    # the template places it at the measure and the design test
                    # pins that token.
                    found.append({**common, "widthPt": tokens.PLATE_PT, "basis": "declared"})
                continue
            width = tokens.FIGURE_WIDTH_PT if preset == "centred" else tokens.BODY_MEASURE_PT * tokens.SIDE_FRACTION
            measured = next(
                (box for box in boxes.get(page, []) if abs(box[2] - width) <= tolerance),
                None,
            )
            visuals.append(
                {
                    **common,
                    "preset": preset,
                    "widthPt": round(measured[2], 2) if measured is not None else round(width, 2),
                    "leftPt": round(measured[0], 2) if measured is not None else None,
                    "basis": "measured" if measured is not None else "declared",
                    "column": False,
                }
            )
        if found:
            plates.extend(found)
        else:
            reason = chapter.get("noPlate")
            gaps.append(
                {
                    "chapter": chapter.get("printed"),
                    "title": chapter["title"],
                    "blockIds": [block["id"] for block in blocks],
                    "reason": reason,
                    "basis": "declared" if reason else "missing",
                }
            )
    return plates, gaps, visuals


def grouped_page_lines(pdf: Path, page: int) -> list[str]:
    """Rendered lines with same-baseline fragments joined.

    `pdftotext -layout` can split one heading into two lines when Typst emits a
    block boundary mid-line (seen with per-level heading spacing). Grouping the
    bbox fragments that share a vertical box keeps the printed heading intact.
    """
    _width, _height, lines = _bbox_lines(pdf, page)
    grouped: list[list[float | list[tuple[float, str]]]] = []
    for text, x_min, _x_max, y_min, y_max in sorted(lines, key=lambda line: (round(line[3], 1), line[1])):
        if grouped and abs(float(grouped[-1][0]) - y_min) < 1.0 and abs(float(grouped[-1][1]) - y_max) < 1.0:
            grouped[-1][2].append((x_min, text))  # type: ignore[union-attr]
        else:
            grouped.append([y_min, y_max, [(x_min, text)]])
    return [
        " ".join(text for _x, text in sorted(parts))  # type: ignore[union-attr]
        for _y_min, _y_max, parts in grouped
    ]


def require_composition_fit(
    pdf: Path,
    document: dict[str, Any],
    numbered: dict[str, int],
    page_height: float,
) -> None:
    """A side composition must fit the text block; never clip or drop it silently."""
    margin = tokens.PAGE_MARGIN_PT
    measure_right = margin + tokens.BODY_MEASURE_PT
    cache: dict[int, list[tuple[str, float, float, float, float]]] = {}
    for section in document["sections"]:
        for block in section["blocks"]:
            if block.get("type") != "illustration" or block.get("composition") not in SIDE_PRESETS:
                continue
            page = numbered.get(block.get("label", ""))
            if page is None:
                continue
            if page not in cache:
                cache[page] = _bbox_lines(pdf, page)[2]
            for text, x_min, x_max, y_min, y_max in cache[page]:
                if PAGE_NUMBER.fullmatch(text):
                    continue
                if y_max > page_height - margin + 2.0:
                    raise BookifyError(
                        "BUILD_FAILED",
                        f"composition does not fit the text block: {block['id']}",
                        block["id"],
                    )
                if x_max > measure_right + FIT_GLYPH_OVERHANG_PT or x_min < margin - FIT_GLYPH_OVERHANG_PT:
                    raise BookifyError(
                        "BUILD_FAILED",
                        f"composition text leaves its column: {block['id']}",
                        block["id"],
                    )


def analyse(
    pdf: Path,
    document: dict[str, Any],
    figure_assets: list[dict[str, str]],
    offline: bool,
    draft: bool,
    manuscript_path: Path,
    network_attempts: int = 0,
) -> dict[str, Any]:
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    pages = int(next(line.split()[1] for line in info.splitlines() if line.startswith("Pages:")))
    size = next(line.split(":", 1)[1].strip() for line in info.splitlines() if line.startswith("Page size:"))
    texts = _text_pages(pdf, pages)
    height_match = re.search(r"x\s*([0-9.]+)\s*pts", size)
    width_match = re.search(r"([0-9.]+)\s*x", size)
    if not height_match or not width_match:
        raise BookifyError("BUILD_FAILED", f"cannot read page size: {size}", str(pdf))
    page_height = float(height_match.group(1))
    page_width = float(width_match.group(1))

    contents = contents_pages(texts)
    grouped_cache: dict[int, list[str]] = {}

    def page_grouped(index: int) -> list[str]:
        if index not in grouped_cache:
            grouped_cache[index] = grouped_page_lines(pdf, index)
        return grouped_cache[index]

    sections: list[dict[str, Any]] = []
    for section in document["sections"]:
        printed = section.get("printed")
        wanted = section_forms(section)
        page = next(
            (
                index
                for index in range(1, pages + 1)
                if index != 1 and index not in contents
                and any(line_is_section(line, section) for line in page_grouped(index))
            ),
            None,
        )
        sections.append(
            {
                "number": section["number"],
                "printed": printed,
                "title": section["title"],
                "level": section.get("level", 1),
                "page": page,
            }
        )

    placements: list[dict[str, Any]] = []
    numbered: dict[str, int] = {}
    # Read labels from the per-line text boxes, not `pdftotext -layout`: on a
    # two-column page the layout line merges the neighbouring column's prose with
    # the caption, so a right-column `Figure N.` would never start a line. A
    # bbox line is one rendered run and keeps the label at its start.
    for index in range(1, pages + 1):
        for text, _x_min, _x_max, _y_min, _y_max in _bbox_lines(pdf, index)[2]:
            match = LABEL.match(text.strip())
            if match:
                numbered.setdefault(f"{match.group(1)} {match.group(2)}", index)
    for illustration in document["illustrations"]:
        label = illustration.get("label")
        page = numbered.get(label) if label else None
        placements.append({"illustrationId": illustration["id"], "page": page, "caption": illustration["caption"]})

    compositions = composition_entries(document, numbered)
    plates, plate_gaps, visual_entries = plate_entries(pdf, document, numbered)
    definitions = sum(
        1
        for section in document["sections"]
        for block in section["blocks"]
        if block.get("type") == "definition"
    )
    # A collated glossary is an ordinary authored table whose caption starts
    # "Glossary"; there is no transform and no glossary field.
    glossary_tables = sum(
        1
        for section in document["sections"]
        for block in section["blocks"]
        if block.get("type") == "table"
        and re.match(r"^Table \d+\.\s*Glossary\b", block.get("caption", ""), re.IGNORECASE)
    )
    figure_captions = sum(
        1
        for section in document["sections"]
        for block in section["blocks"]
        if block.get("type") in {"chart", "diagram", "illustration"}
    )
    cover_entries = require_cover_fit(pdf, document, page_width, page_height)
    require_composition_fit(pdf, document, numbered, page_height)
    require_unit_fit(pdf, document, numbered, page_height)

    from bookify.publish import readability

    readability_metrics = readability.measure(pdf, document)

    warnings: list[str] = []
    for section in document["sections"]:
        for block in section["blocks"]:
            # Synthetic and inferred provenance are different claims. The
            # caption says it exactly; the machine-readable report must too.
            if block.get("synthetic"):
                detail = (
                    "synthetic data, not measurements"
                    if block["type"] == "chart"
                    else "illustrative diagram, not a reconstruction"
                )
            elif block.get("approximate"):
                detail = (
                    "values are approximate"
                    if block["type"] == "chart"
                    else "diagram inferred, not traced from a source"
                )
            else:
                continue
            warnings.append(f"{block['label']}: {detail} ({block['id']})")

    machine_read = [
        {
            "blockId": block["id"],
            "page": numbered.get(block.get("label", "")),
            "region": block["machineRead"]["region"],
            "method": block["machineRead"]["method"],
            "confidence": block["machineRead"]["confidence"],
        }
        for section in document["sections"]
        for block in section["blocks"]
        if isinstance(block.get("machineRead"), dict)
    ]

    return {
        "schemaVersion": "1.0",
        "manuscript": {
            "path": str(manuscript_path),
            "revision": document["revision"],
            "sha256": _sha256(manuscript_path),
        },
        "pdf": {"path": str(pdf), "sha256": _sha256(pdf), "pages": pages, "pageSize": size},
        "offline": offline,
        "networkAttempts": network_attempts,
        "draft": draft,
        "figures": figure_assets,
        "sections": sections,
        "contentsPages": sorted(contents),
        "numbered": numbered,
        "placements": placements,
        "compositions": compositions,
        "plates": plates,
        "plateGaps": plate_gaps,
        "visuals": visual_entries,
        "definitions": {"count": definitions, "glossaryTables": glossary_tables},
        "captions": {"unified": figure_captions, "separateNotes": 0},
        "readability": readability_metrics,
        "numbering": document.get("numbering"),
        "cover": {
            "composition": (document.get("cover") or {}).get("composition"),
            "selection": (document.get("cover") or {}).get("selection"),
            "artwork": (document.get("cover") or {}).get("artwork"),
            "chapterIndex": "omitted",
            "titleLines": cover_entries,
            "folio": False,
        },
        "machineRead": machine_read,
        "warnings": warnings,
    }


def write(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
