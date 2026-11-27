"""D6: heading rhythm, measured from the rendered pages.

Body leading 15.30 pt and paragraph gap 20.70 pt stay as measured. A level-2
heading opens at least 36.0 pt of baseline above the preceding body line and a
level-3 heading at least 31.0 pt; both leave a measured full-width white band
(8.0 pt and 5.0 pt). A level-1 title keeps its >= 32.7 pt deck gap.

The house rule is stronger than "the inks do not collide": every heading is
followed by at least one visibly blank body line (15.30 pt). The check measures
the real white band below the heading's last line, whatever follows it — prose, a
figure, a caption — so a heading cannot sit tight against any content. A crop no
narrower than the heading's own column is used, so a two-column page (A2) is
measured per column and never across the gutter.

When a page offers no sample the check records the zero and does not invent one.
"""

from __future__ import annotations

import re
from pathlib import Path

from bookify.design import tokens
from bookify.manuscript import model
from bookify.publish import normalize, report
from bookify.verify.checks import Check, failed, passed, warned
from bookify.verify.checks import captions as captions_check
from bookify.verify.checks import cover as cover_check

LINE_BOX_EM = 1.5217
BODY_PITCH_PT = tokens.INK_LINE_BOX_EM * tokens.BODY_SIZE_PT + tokens.BODY_LEADING_PT
PARAGRAPH_GAP_PT = 20.70
BODY_SIZE_PT = tokens.BODY_SIZE_PT
LEAD_SIZE_PT = tokens.LEAD_SIZE_PT
BODY_LEADING_PT = tokens.BODY_LEADING_PT
DECK_GAP_PT = 32.7
H2_DELTA_PT = 36.0
H2_BAND_PT = 8.0
H3_DELTA_PT = 31.0
H3_BAND_PT = 5.0
PITCH_TOLERANCE_PT = 0.2
GAP_TOLERANCE_PT = 0.35
RASTER_DPI = 300
# The pdftotext line box runs 0.463 em below the baseline and 1.059 em above it
# for the pinned Spectral faces; `size` is the box height / 1.5217.
DESCENT_EM = 0.463
# A heading and the following line must keep at least one body line pitch of
# white space between their ink bands. The theme reserves
# `descent + overhang + blank_line + clearance`, so a passing page normally shows
# just over 15.30 pt.
HEADING_CLEARANCE_PT = tokens.BLANK_LINE_PT
# How far below a heading's line box the next ink may sit and still belong to
# the heading's clearance measurement.
FOLLOW_WINDOW_PT = 60.0
# Below a heading the crop starts just above the baseline (inside the heading's
# x-height ink) so a previous line's descenders cannot be mistaken for it.
HEADING_BASELINE_RISE_EM = 0.12
# Rows that start this far into the measure open the second column.
PREFIX = re.compile(
    r"^(?:Chapter \d+|Appendix [A-Z]+):\s+"
    r"|^(?:Appendix [A-Z]+|\d+(?:\.\d+)*\.?|[A-Z]+(?:\.\d+)*\.?)\s+"
)


def _matches(text: str, section: dict) -> bool:
    stripped = text.strip()
    if report.line_is_section(stripped, section):
        return True
    match = PREFIX.match(stripped)
    return bool(match and stripped[match.end():] == section["title"])


def _stream(text: str) -> str:
    return re.sub(r"[\s\u00ad]", "", text)


def _column_bounds(index: int, margin: float, measure: float, *, two_column: bool = True) -> tuple[float, float]:
    if not two_column:
        return margin, margin + measure
    width = tokens.COLUMN_WIDTH_PT
    gutter = tokens.SIDE_GUTTER_PT
    if index == 0:
        return margin, margin + width
    return margin + width + gutter, margin + width + gutter + width


def _rows(lines: list) -> list[dict]:
    rows: list[list] = []
    for line in sorted(lines, key=lambda item: (round(item.y_min, 1), item.x_min)):
        if rows and abs(rows[-1]["y_min"] - line.y_min) < 1.0 and abs(rows[-1]["y_max"] - line.y_max) < 1.0:
            rows[-1]["parts"].append((line.x_min, line.x_max, line.text))
        else:
            rows.append(
                {
                    "parts": [(line.x_min, line.x_max, line.text)],
                    "y_min": line.y_min,
                    "y_max": line.y_max,
                }
            )
    for row in rows:
        parts = sorted(row["parts"])
        row["text"] = " ".join(text for _x0, _x1, text in parts)
        row["x_min"] = min(x0 for x0, _x1, _text in parts)
        row["x_max"] = max(x1 for _x0, x1, _text in parts)
        row["size"] = (row["y_max"] - row["y_min"]) / LINE_BOX_EM
    for row in rows:
        row.pop("parts")
    return rows


def _bands(pdf: Path, page: int, top: float, bottom: float, x_from: float, x_to: float) -> list[list[int]]:
    """Inked raster row bands inside a crop, in raster rows."""
    if bottom - top < 1.0:
        return []
    image = cover_check.raster(pdf, page, RASTER_DPI).mean(axis=2)
    scale = RASTER_DPI / 72
    lo = max(0, int(top * scale))
    hi = min(image.shape[0], int(bottom * scale) + 1)
    x_lo = max(0, int(x_from * scale))
    x_hi = min(image.shape[1], int(x_to * scale) + 1)
    rows = [row for row in range(lo, hi) if (image[row, x_lo:x_hi] < cover_check.RULE_DARK).any()]
    if not rows:
        return []
    bands: list[list[int]] = []
    start = previous = rows[0]
    for row in rows[1:]:
        if row - previous > 1:
            bands.append([start, previous])
            start = row
        previous = row
    bands.append([start, previous])
    return bands


def _ink_band(pdf: Path, page: int, top: float, bottom: float, x_from: float, x_to: float) -> float | None:
    """Widest white band between ink rows inside a crop, in points."""
    bands = _bands(pdf, page, top, bottom, x_from, x_to)
    if len(bands) < 2:
        return None
    return max(bands[index + 1][0] - bands[index][1] - 1 for index in range(len(bands) - 1)) * 72 / RASTER_DPI


def _baseline(row: dict) -> float:
    """Baseline of a rendered line from its pdftotext box and measured size."""
    return row["y_max"] - DESCENT_EM * row["size"]


def _clearance_below(
    pdf: Path, page: int, heading: dict, x_from: float, x_to: float
) -> tuple[float | None, bool]:
    """White band below a heading's last line, and whether ink touches it.

    The crop starts at the heading's own line box and reaches one follow window
    below it, so it measures whatever content follows: prose, a figure, a
    caption or a table. Returns ``(None, False)`` when nothing follows on this
    page, and ``(None, True)`` when the next band touches the heading ink.
    """
    scale = RASTER_DPI / 72
    baseline = _baseline(heading)
    # Start inside the heading's own x-height so the previous heading line's
    # descenders (they overlap a large line box) are never the first band.
    top = baseline - HEADING_BASELINE_RISE_EM * heading["size"]
    bottom = baseline + FOLLOW_WINDOW_PT
    bands = _bands(pdf, page, top, bottom, x_from, x_to)
    if not bands:
        return None, False
    if len(bands) < 2:
        # One band: either nothing follows the heading, or the follower's ink
        # merged with the heading's. A merged band reaches past the heading's
        # own descender ink.
        descender = (baseline + DESCENT_EM * heading["size"]) * scale
        if bands[0][1] > descender + 1:
            return None, True
        return None, False
    return (bands[1][0] - bands[0][1] - 1) / scale, False


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    figure_paths = {
        block["id"]: "unused.svg"
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    }
    document = normalize.build(manuscript, figure_paths, draft=True).data
    lines = list(captions_check.read_lines(pdf))
    page_width, _page_height = cover_check._page_size(pdf)
    margin = (page_width - tokens.BODY_MEASURE_PT) / 2
    measure = tokens.BODY_MEASURE_PT
    texts = [
        "\n".join(line.text for line in lines if line.page == page)
        for page in range(1, max(line.page for line in lines) + 1)
    ]
    contents = report.contents_pages(texts)
    # A real book opens with a designed cover, so page 1 is not body content. A
    # standalone fixture may start its first section on page 1; keep it then.
    first_rows = _rows([line for line in lines if line.page == 1])
    # A designed cover carries only cover type (8.4-34 pt) and never a body
    # heading; a real h1/h2/h3 heading is at least 10.3 pt and matches a section.
    has_body_heading = any(
        _matches(row["text"], section)
        for row in first_rows
        for section in document["sections"]
        if row["size"] >= 10.2
    )
    exclude = set(contents) | (set() if has_body_heading else {1})
    pages = sorted({line.page for line in lines} - exclude)

    # Two-column pages are known from the authored chapter layout, never guessed
    # from where lines happen to start: a table or diagram page is single-column.
    start_pages: dict[str, int] = {}
    for section in document["sections"]:
        page = next(
            (
                candidate
                for candidate in pages
                if any(
                    report.line_is_section(line.text, section)
                    for line in lines
                    if line.page == candidate
                )
            ),
            None,
        )
        if page is not None:
            start_pages[section["title"]] = page
    level_one = [section for section in document["sections"] if section.get("level", 1) == 1]
    two_column_pages: set[int] = set()
    for index, section in enumerate(level_one):
        if (section.get("layout") or {}).get("columns") != 2:
            continue
        start = start_pages.get(section["title"])
        if start is None:
            continue
        following = [
            start_pages[other["title"]]
            for other in level_one[index + 1 :]
            if other["title"] in start_pages
        ]
        if following:
            stop = min(following)
            # A following chapter may start on the same page (breakBefore auto).
            # That page still carries the two-column chapter above it, so only
            # the *later* pages become single-column; declaring the whole run a
            # column page would crop the following chapter's full-measure text.
            if stop <= start:
                stop = start + 1
        else:
            stop = (max(pages) + 1) if pages else (start + 1)
        two_column_pages.update(range(start, stop))

    rows_by_column: dict[tuple[int, int], list[dict]] = {}
    columns_by_page: dict[int, list[int]] = {}
    for page in pages:
        page_lines = [line for line in lines if line.page == page]
        if page in two_column_pages:
            split = {
                0: [line for line in page_lines if line.x_min < margin + measure / 2],
                1: [line for line in page_lines if line.x_min >= margin + measure / 2],
            }
        else:
            split = {0: page_lines}
        columns_by_page[page] = sorted(split)
        for column, column_lines in split.items():
            rows_by_column[(page, column)] = _rows(column_lines)

    titles: dict[str, tuple[int, int, int, dict]] = {}
    for section in document["sections"]:
        for page in pages:
            for column in columns_by_page[page]:
                index = next(
                    (
                        position
                        for position, row in enumerate(rows_by_column[(page, column)])
                        if _matches(row["text"], section)
                    ),
                    None,
                )
                if index is not None:
                    titles[section["title"]] = (page, column, index, section)
                    break
            if section["title"] in titles:
                break

    problems: list[str] = []
    evidence: dict[str, object] = {
        "bodyPitchSamples": 0,
        "paragraphGapSamples": 0,
        "h2Samples": 0,
        "h3Samples": 0,
        "deckSamples": 0,
        "wrappedHeadingSamples": 0,
        "clearanceSamples": 0,
        "columnPages": sorted(two_column_pages & set(pages)),
        "headingBands": [],
        "headingClearance": [],
    }
    section_titles = document["sections"]

    for section_id, (page, column, index, section) in titles.items():
        rows = rows_by_column[(page, column)]
        x_from, x_to = _column_bounds(column, margin, measure, two_column=page in two_column_pages)
        title = rows[index]
        level = section.get("level", 1)

        # A wrapped heading keeps its level pitch.
        # Levels 4 and 5 use the h3 type role, so they keep its 14 pt pitch.
        pitch = {1: 30.0, 2: 16.5, 3: 14.0, 4: 14.0, 5: 14.0}[level]
        expected = _stream(section["title"])
        row_stream = _stream(title["text"])
        prefix_match = PREFIX.match(title["text"].strip())
        if prefix_match:
            row_stream = row_stream[len(_stream(prefix_match.group(0))):]
        consumed = len(row_stream)
        cursor = index
        while consumed < len(expected) and cursor + 1 < len(rows):
            following = rows[cursor + 1]
            stream = _stream(following["text"])
            if not expected[consumed:].startswith(stream):
                break
            cursor += 1
            consumed += len(stream)
            measured = following["y_min"] - rows[cursor - 1]["y_min"]
            evidence["wrappedHeadingSamples"] = int(evidence["wrappedHeadingSamples"]) + 1
            if abs(measured - pitch) > PITCH_TOLERANCE_PT:
                problems.append(
                    f"{section['title']}: wrapped heading pitch {measured:.2f} pt, expected {pitch}"
                )

        # Clearance below the heading's last line: at least one visible body
        # blank line before whatever follows it.
        clearance, touching = _clearance_below(pdf, page, rows[cursor], x_from, x_to)
        if touching:
            problems.append(
                f"{section['title']}: the following content touches the heading; no white line below it"
            )
        elif clearance is not None:
            evidence["clearanceSamples"] = int(evidence["clearanceSamples"]) + 1
            clearance_list = evidence["headingClearance"]
            assert isinstance(clearance_list, list)
            clearance_list.append(
                {
                    "section": section["title"],
                    "level": level,
                    "page": page,
                    "column": column,
                    "clearancePt": round(clearance, 2),
                }
            )
            if clearance < HEADING_CLEARANCE_PT - 0.05:
                problems.append(
                    f"{section['title']}: heading clearance {clearance:.2f} pt is below one "
                    f"body blank line ({HEADING_CLEARANCE_PT:.2f} pt)"
                )

        if level == 1:
            if index + 1 < len(rows):
                following = rows[index + 1]
                if abs(following["size"] - LEAD_SIZE_PT) <= 0.3:
                    delta = following["y_min"] - title["y_min"]
                    evidence["deckSamples"] = int(evidence["deckSamples"]) + 1
                    if delta < DECK_GAP_PT - 0.05:
                        problems.append(f"{section['title']}: deck gap {delta:.2f} pt is below {DECK_GAP_PT}")
        else:
            if index > 0:
                previous = rows[index - 1]
                # The 36/31 pt baseline delta is defined against a preceding
                # *body* line. A caption, note or figure label before the heading
                # has a smaller line box, so only the measured white band is
                # authoritative there.
                body_before = 9.9 <= previous["size"] <= 10.25
                delta = (title["y_min"] - previous["y_min"]) if body_before else None
                band = _ink_band(pdf, page, previous["y_min"] - 1.0, title["y_min"] + 6.0, x_from, x_to)
                bands_list = evidence["headingBands"]
                assert isinstance(bands_list, list)
                bands_list.append(
                    {
                        "section": section["title"],
                        "level": level,
                        "page": page,
                        "column": column,
                        "bandPt": None if band is None else round(band, 2),
                    }
                )
                if level == 2:
                    evidence["h2Samples"] = int(evidence["h2Samples"]) + 1
                    if body_before and delta is not None and delta < H2_DELTA_PT - 0.05:
                        problems.append(f"{section['title']}: h2 gap {delta:.2f} pt is below {H2_DELTA_PT}")
                    if band is None:
                        problems.append(
                            f"{section['title']}: h2 white band is unmeasurable above the heading"
                        )
                    elif band < H2_BAND_PT:
                        problems.append(f"{section['title']}: h2 white band {band:.2f} pt is below {H2_BAND_PT}")
                else:
                    evidence["h3Samples"] = int(evidence["h3Samples"]) + 1
                    if body_before and delta is not None and delta < H3_DELTA_PT - 0.05:
                        problems.append(f"{section['title']}: h3 gap {delta:.2f} pt is below {H3_DELTA_PT}")
                    if band is None:
                        problems.append(
                            f"{section['title']}: h3 white band is unmeasurable above the heading"
                        )
                    elif band < H3_BAND_PT:
                        problems.append(f"{section['title']}: h3 white band {band:.2f} pt is below {H3_BAND_PT}")

            # No heading immediately followed by another heading.
            if index + 1 < len(rows):
                next_row = rows[index + 1]
                if any(
                    _matches(next_row["text"], other) and other["title"] != section["title"]
                    for other in section_titles
                ):
                    problems.append(f"{section['title']}: heading is followed immediately by another heading")

    # Body pitch inside a paragraph and the paragraph gap between two blocks.
    title_rows = {(page, column, index) for page, column, index, _section in titles.values()}
    for (page, column), rows in rows_by_column.items():
        for position in range(len(rows) - 1):
            current, following = rows[position], rows[position + 1]
            if (page, column, position) in title_rows or (page, column, position + 1) in title_rows:
                continue
            if abs(current["size"] - BODY_SIZE_PT) > 0.25 or abs(following["size"] - BODY_SIZE_PT) > 0.25:
                continue
            delta = following["y_min"] - current["y_min"]
            full = current["x_max"] - margin >= 0.9 * measure
            short = current["x_max"] - margin <= 0.75 * measure
            if full and abs(delta - BODY_PITCH_PT) <= 1.5:
                evidence["bodyPitchSamples"] = int(evidence["bodyPitchSamples"]) + 1
                if abs(delta - BODY_PITCH_PT) > PITCH_TOLERANCE_PT:
                    problems.append(f"page {page}: body pitch {delta:.2f} pt, expected {BODY_PITCH_PT:.2f}")
            elif short and abs(delta - PARAGRAPH_GAP_PT) <= 1.5:
                evidence["paragraphGapSamples"] = int(evidence["paragraphGapSamples"]) + 1
                if abs(delta - PARAGRAPH_GAP_PT) > GAP_TOLERANCE_PT:
                    problems.append(f"page {page}: paragraph gap {delta:.2f} pt, expected {PARAGRAPH_GAP_PT}")

    if problems:
        return failed("rhythm", "VERIFY_FAILED", "; ".join(problems[:4]), problems=problems, **evidence)
    levels = {section.get("level", 1) for section in document["sections"]}
    unmeasured: list[str] = []
    if not any(level >= 2 for level in levels):
        # A book with no body headings at all has no proven hierarchy rhythm.
        unmeasured = ["h2", "h3"]
    else:
        if 2 in levels and int(evidence["h2Samples"]) == 0:
            unmeasured.append("h2")
        if any(level >= 3 for level in levels) and int(evidence["h3Samples"]) == 0:
            unmeasured.append("h3")
    if unmeasured:
        warnings = [
            {
                "id": f"rhythm:unmeasured:{level}",
                "metric": "headingRhythm",
                "value": 0,
                "band": None,
                "pages": [],
                "detail": (
                    f"no {level} sample was measured; the {level} band is unproven for this book"
                ),
            }
            for level in unmeasured
        ]
        return warned(
            "rhythm",
            f"zero {', '.join(unmeasured)} sample(s); heading rhythm is unmeasured",
            warnings=warnings,
            **evidence,
        )
    return passed(
        "rhythm",
        "heading and body rhythm within the measured bands",
        **evidence,
    )
