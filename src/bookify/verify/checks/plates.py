"""D4: chapter headings and full-measure plates, measured from the PDF.

A chapter heading is one h1 line beginning `Chapter 1:` (or `Appendix A:`); the
retired 40 pt numeral and opener rule are not printed. A chapter that contains a
visual must carry one plate at the text measure (475.28 pt ±1) unless the author
records a `no-plate` reason; a centred or side visual is not a plate and is
recorded with the width it really occupies. A missing plate is a warning for
review, never a hard build failure. A missing or malformed heading is a defect.
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


def _page_of(lines: list, section: dict, exclude: set[int]) -> int | None:
    for page in sorted({line.page for line in lines} - exclude):
        if any(
            report.line_is_section(text, section)
            for text, _y_min, _y_max in _rows([line for line in lines if line.page == page])
        ):
            return page
    return None


def _opener(
    pdf: Path, lines: list, section: dict, printed: str, exclude: set[int]
) -> list[str]:
    """Check one chapter heading; the `Chapter n: Title` rule supersedes the opener.

    The retired stack was a 40 pt numeral, a full-measure rule and the title. The
    current rule is one h1 line that begins `Chapter 1:` (or `Appendix A:`) and
    is followed by at least one blank body line, measured by the rhythm check.
    """
    problems: list[str] = []
    page = _page_of(lines, section, exclude)
    if page is None:
        return [f"{section['title']}: chapter heading page not found"]
    page_width, _page_height = cover_check._page_size(pdf)
    page_lines = [line for line in lines if line.page == page]
    rows = _rows(page_lines)
    prefix = f"{printed}:" if section.get("role") == "appendix" else f"Chapter {printed}:"
    heading = next((row for row in rows if row[0].strip().startswith(prefix)), None)
    if heading is None:
        problems.append(f"{section['title']}: heading does not begin {prefix!r}")
    else:
        size = (heading[2] - heading[1]) / cover_check.LINE_BOX_EM
        if abs(size - tokens.H1_SIZE_PT) > 1.0:
            problems.append(f"{section['title']}: chapter heading measures {size:.2f} pt")
    if len(rows) >= 2:
        first = rows[0]
        if first[0].strip() == printed:
            problems.append(f"{section['title']}: the retired 40 pt numeral stack is still printed")
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

    plates, gaps, visuals = report.plate_entries(pdf, document.data, numbered)
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
    evidence = {"plates": plates, "gaps": gaps, "visuals": visuals, "warnings": warnings}
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
