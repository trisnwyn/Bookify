"""D6: heading rhythm, measured from the rendered pages.

Body leading 15.30 pt and paragraph gap 20.70 pt stay as measured. A level-2
heading opens at least 36.0 pt of baseline above the preceding body line and a
level-3 heading at least 31.0 pt; both leave a measured full-width white band
(8.0 pt and 5.0 pt). A level-1 title keeps its >= 32.7 pt deck gap. Below every
heading the check now measures the real white row between the heading's
descender ink and the following line's ascenders: the pinned Latin face ends
its layout line at the baseline, so `block(below:)` alone cannot reserve
descender ink (F1 specimen page 4). No heading is immediately followed by
another heading. When a page offers no sample the check records the zero and
does not invent one.
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
BODY_PITCH_PT = 15.30
PARAGRAPH_GAP_PT = 20.70
BODY_SIZE_PT = 10.1
LEAD_SIZE_PT = 10.6
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
# Below a heading the crop starts just above the baseline (inside the heading's
# x-height ink) and reaches into the following line as far as its x-height ink,
# so both bands are present even when neither side has ascenders or descenders.
HEADING_BASELINE_RISE_EM = 0.12
FOLLOWING_LINE_DEPTH_EM = 0.70
# A heading and the following line must keep at least one dark-free raster row
# between their ink bands at 300 dpi (0.24 pt). The theme reserves 0.5 pt, so a
# passing page normally shows two rows.
HEADING_CLEARANCE_PT = 72 / RASTER_DPI
# Only a following line this close is the heading's immediate follower; a
# larger gap means a plate or a block boundary sits between them.
FOLLOWER_LIMIT_PT = 60.0
PREFIX = re.compile(r"^(?:Appendix [A-Z]+|\d+(?:\.\d+)*|[A-Z]+(?:\.\d+)*)\s+")


def _matches(text: str, title: str) -> bool:
    stripped = text.strip()
    if stripped == title:
        return True
    match = PREFIX.match(stripped)
    return bool(match and stripped[match.end():] == title)


def _stream(text: str) -> str:
    return re.sub(r"[\s\u00ad]", "", text)


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


def _ink_band(pdf: Path, page: int, top: float, bottom: float) -> float | None:
    """Widest white band between ink rows inside a crop, in points.

    The crop spans two text lines whose gap is measured (the preceding line and
    the top of a heading, or a heading's baseline and the next line). The
    widest gap between two ink bands is the measured white band; ``None`` means
    fewer than two bands, i.e. the ink touches or there is nothing to measure.
    """
    if bottom - top < 1.0:
        return None
    image = cover_check.raster(pdf, page, RASTER_DPI).mean(axis=2)
    scale = RASTER_DPI / 72
    lo = max(0, int(top * scale))
    hi = min(image.shape[0], int(bottom * scale) + 1)
    rows = [row for row in range(lo, hi) if (image[row] < cover_check.RULE_DARK).any()]
    if not rows:
        return None
    bands: list[list[int]] = []
    start = previous = rows[0]
    for row in rows[1:]:
        if row - previous > 1:
            bands.append([start, previous])
            start = row
        previous = row
    bands.append([start, previous])
    if len(bands) < 2:
        return None
    return max(bands[index + 1][0] - bands[index][1] - 1 for index in range(len(bands) - 1)) / scale


def _baseline(row: dict) -> float:
    """Baseline of a rendered line from its pdftotext box and measured size."""
    return row["y_max"] - DESCENT_EM * row["size"]


def _clearance_below(pdf: Path, page: int, heading: dict, following: dict) -> float | None:
    """White row between a heading's descenders and the next line, in points.

    ``None`` means the two ink bands touch or overlap: there is no white row to
    measure, which is a clearance failure, not an unmeasured sample.
    """
    top = _baseline(heading) - HEADING_BASELINE_RISE_EM * heading["size"]
    bottom = following["y_min"] + FOLLOWING_LINE_DEPTH_EM * following["size"]
    return _ink_band(pdf, page, top, bottom)


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
    # A designed cover carries a small chapter index (8.6 pt) that repeats every
    # title. A real h1/h2/h3 heading is at least 10.3 pt, so only that means page
    # 1 is body content for a standalone fixture.
    has_body_heading = any(
        _matches(row["text"], section["title"]) and row["size"] >= 10.2
        for row in first_rows
        for section in document["sections"]
    )
    exclude = set(contents) | (set() if has_body_heading else {1})
    pages = sorted({line.page for line in lines} - exclude)
    rows_by_page = {page: _rows([line for line in lines if line.page == page]) for page in pages}

    titles: dict[str, tuple[int, int, dict]] = {}
    for section in document["sections"]:
        for page in pages:
            index = next(
                (
                    position
                    for position, row in enumerate(rows_by_page[page])
                    if _matches(row["text"], section["title"])
                ),
                None,
            )
            if index is not None:
                titles[section["title"]] = (page, index, section)
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
        "headingBands": [],
        "headingClearance": [],
    }
    section_titles = [section["title"] for section in document["sections"]]

    for section_id, (page, index, section) in titles.items():
        rows = rows_by_page[page]
        title = rows[index]
        level = section.get("level", 1)

        # A wrapped heading keeps its level pitch.
        pitch = {1: 30.0, 2: 16.5, 3: 14.0}[level]
        expected = _stream(section["title"])
        row_stream = _stream(title["text"])
        prefix_match = PREFIX.match(title["text"].strip())
        if prefix_match:
            row_stream = row_stream[len(_stream(prefix_match.group(0))):]
        consumed = len(row_stream)
        cursor = index
        while consumed != expected and cursor + 1 < len(rows):
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

        # Clearance below the heading: its descender ink must not touch the
        # following line's ascenders, and at least one raster row must stay
        # white between the two ink bands.
        if cursor + 1 < len(rows):
            following = rows[cursor + 1]
            another_heading = any(
                _matches(following["text"], other)
                for other in section_titles
                if other != section["title"]
            )
            if not another_heading and following["y_min"] - rows[cursor]["y_min"] <= FOLLOWER_LIMIT_PT:
                clearance = _clearance_below(pdf, page, rows[cursor], following)
                evidence["clearanceSamples"] = int(evidence["clearanceSamples"]) + 1
                clearance_list = evidence["headingClearance"]
                assert isinstance(clearance_list, list)
                clearance_list.append(
                    {
                        "section": section["title"],
                        "level": level,
                        "page": page,
                        "clearancePt": None if clearance is None else round(clearance, 2),
                    }
                )
                if clearance is None:
                    problems.append(
                        f"{section['title']}: the following line touches the heading; no white row below it"
                    )
                elif clearance < HEADING_CLEARANCE_PT - 0.01:
                    problems.append(
                        f"{section['title']}: heading clearance {clearance:.2f} pt is below {HEADING_CLEARANCE_PT:.2f}"
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
                if previous["size"] < 10.25:
                    delta = title["y_min"] - previous["y_min"]
                    band = _ink_band(pdf, page, previous["y_min"] - 1.0, title["y_min"] + 6.0)
                    bands_list = evidence["headingBands"]
                    assert isinstance(bands_list, list)
                    bands_list.append(
                        {
                            "section": section["title"],
                            "level": level,
                            "page": page,
                            "bandPt": None if band is None else round(band, 2),
                        }
                    )
                    if level == 2:
                        evidence["h2Samples"] = int(evidence["h2Samples"]) + 1
                        if delta < H2_DELTA_PT - 0.05:
                            problems.append(f"{section['title']}: h2 gap {delta:.2f} pt is below {H2_DELTA_PT}")
                        if band is None:
                            problems.append(
                                f"{section['title']}: h2 white band is unmeasurable above the heading"
                            )
                        elif band < H2_BAND_PT:
                            problems.append(f"{section['title']}: h2 white band {band:.2f} pt is below {H2_BAND_PT}")
                    else:
                        evidence["h3Samples"] = int(evidence["h3Samples"]) + 1
                        if delta < H3_DELTA_PT - 0.05:
                            problems.append(f"{section['title']}: h3 gap {delta:.2f} pt is below {H3_DELTA_PT}")
                        if band is None:
                            problems.append(
                                f"{section['title']}: h3 white band is unmeasurable above the heading"
                            )
                        elif band < H3_BAND_PT:
                            problems.append(f"{section['title']}: h3 white band {band:.2f} pt is below {H3_BAND_PT}")

            # No heading immediately followed by another heading.
            if index + 1 < len(rows) and level in (1, 2, 3):
                next_row = rows[index + 1]
                if any(
                    _matches(next_row["text"], other["title"])
                    for other in document["sections"]
                    if other["title"] != section["title"]
                ):
                    problems.append(f"{section['title']}: heading is followed immediately by another heading")

    # Body pitch inside a paragraph and the paragraph gap between two blocks.
    title_rows = {(page, index) for page, index, _section in titles.values()}
    for page, rows in rows_by_page.items():
        for position in range(len(rows) - 1):
            current, following = rows[position], rows[position + 1]
            if (page, position) in title_rows or (page, position + 1) in title_rows:
                continue
            if abs(current["size"] - BODY_SIZE_PT) > 0.25 or abs(following["size"] - BODY_SIZE_PT) > 0.25:
                continue
            delta = following["y_min"] - current["y_min"]
            full = current["x_max"] - margin >= 0.9 * measure
            short = current["x_max"] - margin <= 0.75 * measure
            if full and abs(delta - BODY_PITCH_PT) <= 1.5:
                evidence["bodyPitchSamples"] = int(evidence["bodyPitchSamples"]) + 1
                if abs(delta - BODY_PITCH_PT) > PITCH_TOLERANCE_PT:
                    problems.append(f"page {page}: body pitch {delta:.2f} pt, expected {BODY_PITCH_PT}")
            elif short and abs(delta - PARAGRAPH_GAP_PT) <= 1.5:
                evidence["paragraphGapSamples"] = int(evidence["paragraphGapSamples"]) + 1
                if abs(delta - PARAGRAPH_GAP_PT) > GAP_TOLERANCE_PT:
                    problems.append(f"page {page}: paragraph gap {delta:.2f} pt, expected {PARAGRAPH_GAP_PT}")

    if problems:
        return failed("rhythm", "VERIFY_FAILED", "; ".join(problems[:4]), problems=problems, **evidence)
    unmeasured = [
        level
        for level, key in (("h2", "h2Samples"), ("h3", "h3Samples"))
        if int(evidence[key]) == 0
    ]
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
