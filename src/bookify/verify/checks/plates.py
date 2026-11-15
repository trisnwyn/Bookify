"""D4: chapter openers and full-measure plates, measured from the PDF.

An opener must print the number at 40 pt, a thin full-measure rule below it and
the title. A chapter that contains a visual must carry one plate at the text
measure (475.28 pt ±1) unless the author records a `no-plate` reason; a missing
plate is a warning for review, never a hard build failure. A missing or
mutilated opener is a defect.
"""

from __future__ import annotations

import re
from pathlib import Path

from bookify.design import tokens
from bookify.manuscript import model
from bookify.publish import normalize, report
from bookify.verify.checks import Check, failed, passed, warned
from bookify.verify.checks import cover as cover_check
from bookify.verify.checks.pages import numbered_labels, page_texts

NUMERAL_SIZE_PT = 40.0
NUMERAL_TOLERANCE_PT = 1.0
RULE_DPI = 300


def _stream(text: str) -> str:
    return re.sub(r"[\s\u00ad]", "", text)


def _rows(lines: list) -> list[tuple[str, float, float]]:
    """Join Poppler fragments that share a baseline into one visual row."""
    rows: list[list] = []
    for line in sorted(lines, key=lambda item: (round(item.y_min, 1), item.x_min)):
        if rows and abs(rows[-1][1] - line.y_min) < 1.0 and abs(rows[-1][2] - line.y_max) < 1.0:
            rows[-1][0].append((line.x_min, line.text))
        else:
            rows.append([[ (line.x_min, line.text) ], line.y_min, line.y_max])
    return [
        (" ".join(text for _x, text in sorted(parts)), y_min, y_max)
        for parts, y_min, y_max in rows
    ]


def _page_of(lines: list, wanted: set[str], exclude: set[int]) -> int | None:
    for page in sorted({line.page for line in lines} - exclude):
        if any(
            text.strip() in wanted
            for text, _y_min, _y_max in _rows([line for line in lines if line.page == page])
        ):
            return page
    return None


def _opener(
    pdf: Path, lines: list, section: dict, printed: str, exclude: set[int]
) -> list[str]:
    """Check one level-1 opener; return problems."""
    problems: list[str] = []
    wanted = {section["title"], f"{printed} {section['title']}"}
    page = _page_of(lines, wanted, exclude)
    if page is None:
        return [f"{section['title']}: chapter opener page not found"]
    page_width, page_height = cover_check._page_size(pdf)
    margin = (page_width - tokens.BODY_MEASURE_PT) / 2
    page_lines = [
        line
        for line in lines
        if line.page == page
        and not (
            line.text.strip().isdigit()
            and line.y_min > page_height - margin - cover_check.FOLIO_BAND_PT
        )
    ]
    rows = _rows(page_lines)
    numeral = next((row for row in rows if row[0].strip() == printed), None)
    if numeral is None:
        problems.append(f"{section['title']}: opener has no printed number {printed}")
    else:
        size = (numeral[2] - numeral[1]) / cover_check.LINE_BOX_EM
        if abs(size - NUMERAL_SIZE_PT) > NUMERAL_TOLERANCE_PT:
            problems.append(f"{section['title']}: opener numeral measures {size:.2f} pt")
    title = next((row for row in rows if row[0].strip() == section["title"]), None)
    if title is None:
        problems.append(f"{section['title']}: opener has no title line")
    if numeral is not None and title is not None:
        band_top = numeral[2]
        band_bottom = title[1]
        image = cover_check.raster(pdf, page, RULE_DPI)
        measure_px = int(tokens.BODY_MEASURE_PT * RULE_DPI / 72)
        grey = image.mean(axis=2)
        dark = (grey < cover_check.RULE_DARK).sum(axis=1)
        found_rule = any(
            dark[row] >= measure_px * cover_check.RULE_MIN_FRACTION
            for row in range(int(band_top * RULE_DPI / 72), int(band_bottom * RULE_DPI / 72))
        )
        if not found_rule:
            problems.append(f"{section['title']}: opener has no full-measure rule")
    return problems


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    from bookify.verify.checks import captions as captions_check

    lines = list(captions_check.read_lines(pdf))
    texts = page_texts(pdf)
    numbered = numbered_labels(texts)
    figure_paths = {
        block["id"]: "unused.svg"
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    }
    document = normalize.build(manuscript, figure_paths, draft=True)
    numbers = normalize.section_numbers(manuscript)

    exclude = {1} | report.contents_pages(texts)
    problems: list[str] = []
    for section, item in zip(document.data["sections"], numbers):
        if item["level"] != 1:
            continue
        problems.extend(_opener(pdf, lines, section, item["printed"], exclude))
    if problems:
        return failed("plates", "VERIFY_FAILED", "; ".join(problems[:4]), problems=problems)

    plates, gaps = report.plate_entries(pdf, document.data, numbered)
    missing = [gap for gap in gaps if not gap.get("reason")]
    warnings = [
        {
            "id": f"plates:noPlate:chapter={gap['chapter']}",
            "metric": "plate",
            "value": None,
            "band": None,
            "pages": [],
            "chapter": gap["chapter"],
            "reason": gap["reason"],
        }
        for gap in missing
    ]
    evidence = {"plates": plates, "gaps": gaps, "warnings": warnings}
    if missing:
        return warned(
            "plates",
            f"{len(missing)} chapter(s) with a visual have no plate; record a noPlate reason",
            **evidence,
        )
    return passed(
        "plates",
        f"{len(plates)} plate(s) at the text measure; every opener complete",
        **evidence,
    )
