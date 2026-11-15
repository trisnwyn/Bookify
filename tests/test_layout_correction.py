"""Focused rendered tests for the 2026-11-13 typography/pagination correction.

All fixtures are synthetic and public-safe. Measurements come from the actual
PDF through `pdftotext -bbox-layout`; no tolerance is widened to hide a role.
"""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

import pytest
import yaml
from PIL import Image

from helpers import ROOT, compile_typ
from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.publish import report, typst_driver
from bookify.verify.checks import captions, pages, xrefs

LATIN = (
    "Alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
    "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu "
) * 3
VIETNAMESE = (
    "Tiếng Việt có đủ dấu: ế ộ ữ đ ạ ỹ ỡ ư ơ ằ ắ ẳ ẵ ặ. Một mẫu chỉ có nghĩa khi đi kèm bối cảnh: "
    "nhãn, thời điểm và giới hạn của nó cần được ghi lại trước khi diễn giải. "
) * 2
JAPANESE = (
    "日本語の文章は単語の間に空白がないため、行の折り返しが正しく行われるかを確認します。"
    "見本は文脈と限界を記録して初めて意味を持ちます。見えたままの事実と推測を分けて扱うことが大切です。"
) * 2


def _lines(pdf: Path) -> tuple[captions.LineBox, ...]:
    return captions.read_lines(pdf)


def _page_lines(pdf: Path, page: int) -> list[captions.LineBox]:
    return [line for line in _lines(pdf) if line.page == page and not line.text.strip().isdigit()]


def _pitch(lines: list[captions.LineBox]) -> list[float]:
    ordered = sorted(lines, key=lambda line: line.y_min)
    return [round(later.y_min - earlier.y_min, 2) for earlier, later in zip(ordered, ordered[1:])]


def _assert_pitch(lines: list[captions.LineBox], expected: float, *, minimum: int = 1) -> None:
    deltas = [delta for delta in _pitch(lines) if delta > 1.0]
    assert len(deltas) >= minimum, f"not enough repeated lines: {[line.text for line in lines]}"
    for delta in deltas:
        assert abs(delta - expected) <= 0.15, f"expected {expected} pt, measured {deltas}"


def _roles_pdf() -> Path:
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f"#preset-paragraph({_q(LATIN)})\n"
        "#pagebreak()\n"
        f"#preset-lead({_q(LATIN)})\n"
        "#pagebreak()\n"
        f'#preset-figure-caption("CAPTION-MARKER {LATIN}")\n'
        "#pagebreak()\n"
        f'#preset-note("NOTE-MARKER {LATIN}")\n'
        "#pagebreak()\n"
        f'#preset-quote("QUOTE-MARKER {LATIN}")\n'
        "#pagebreak()\n"
        f'#role-label("definition", "SMALL-MARKER {LATIN}")\n'
        "#pagebreak()\n"
        f'#preset-table(([Header-A],), (([ROW-MARKER {LATIN}],),))\n'
        "#pagebreak()\n"
        f"#preset-paragraph({_q(VIETNAMESE)})\n"
        "#pagebreak()\n"
        f"#preset-paragraph({_q(JAPANESE)})\n"
    )
    return compile_typ(source, "layout-correction-roles")


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def test_role_line_pitches_are_measured_from_the_real_pdf() -> None:
    pdf = _roles_pdf()

    _assert_pitch(_page_lines(pdf, 1), 15.30)
    _assert_pitch(_page_lines(pdf, 2), 16.40)
    _assert_pitch(_page_lines(pdf, 3), 11.20)
    _assert_pitch(_page_lines(pdf, 4), 13.60)
    _assert_pitch(_page_lines(pdf, 5), 15.40)
    _assert_pitch(_page_lines(pdf, 6), 12.00)

    table_lines = _page_lines(pdf, 7)
    row_index = next(index for index, line in enumerate(table_lines) if line.text.startswith("ROW-MARKER"))
    _assert_pitch(table_lines[row_index:], 11.60)

    _assert_pitch(_page_lines(pdf, 8), 15.30)  # Vietnamese shares Spectral metrics
    _assert_pitch(_page_lines(pdf, 9), 15.99)  # Noto Serif CJK JP natural height
    latin = _pitch(_page_lines(pdf, 1))[0]
    japanese = _pitch(_page_lines(pdf, 9))[0]
    assert japanese - latin <= 0.75, f"CJK residual grew: {japanese} vs {latin}"


def test_paragraph_gap_is_wider_than_the_line_pitch_by_5_4_pt() -> None:
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f'#preset-paragraph("ALPHA-MARKER {LATIN}")\n'
        f'#preset-paragraph("BRAVO-MARKER {LATIN}")\n'
    )
    pdf = compile_typ(source, "layout-correction-gap")
    lines = sorted(_page_lines(pdf, 1), key=lambda line: line.y_min)
    bravo = next(index for index, line in enumerate(lines) if line.text.startswith("BRAVO-MARKER"))
    gap = round(lines[bravo].y_min - lines[bravo - 1].y_min, 2)
    body_pitch = _pitch(lines[:bravo])[0]

    assert gap > body_pitch
    assert abs(gap - body_pitch - 5.4) <= 0.3, f"gap {gap}, pitch {body_pitch}"


def test_role_label_keeps_the_absolute_before_role_gap() -> None:
    # D1 retires the definition role label. The role-label mechanism still
    # backs example/case/assessment, so its absolute before_role gap is
    # measured through the example preset, unchanged.
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f'#preset-paragraph("BODY-MARKER {LATIN}")\n'
        f'#preset-example(title: "ROLE-MARKER", "EXAMPLE-MARKER {LATIN}")\n'
    )
    pdf = compile_typ(source, "layout-correction-role-gap")
    lines = sorted(_page_lines(pdf, 1), key=lambda line: line.y_min)
    label = next(index for index, line in enumerate(lines) if line.text.startswith("ROLE-MARKER"))
    above = round(lines[label].y_min - lines[label - 1].y_min, 2)
    below = round(lines[label + 1].y_min - lines[label].y_min, 2)

    # body natural height 0.660 em + before_role 18 pt; label height + 5.4 pt.
    assert abs(above - 25.34) <= 0.15, above
    assert abs(below - 10.27) <= 0.15, below


def test_heading_pitches_are_per_level() -> None:
    source = (
        '#import "/typst/theme.typ": book_base\n'
        "#show: book_base\n"
        "#heading(level: 1)[A very long level one heading that must wrap onto a second line "
        "and then continue far enough to make the wrap unmistakable]\n"
        "#pagebreak()\n"
        "#heading(level: 2)[A very long level two heading that must wrap onto a second line "
        "and then continue far enough to make the wrap unmistakable]\n"
        "#pagebreak()\n"
        "#heading(level: 3)[A very long level three heading that must wrap onto a second line "
        "and then continue far enough to make the wrap unmistakable]\n"
    )
    pdf = compile_typ(source, "layout-correction-headings")

    _assert_pitch(_page_lines(pdf, 1), 30.00)
    _assert_pitch(_page_lines(pdf, 2), 16.50)
    _assert_pitch(_page_lines(pdf, 3), 14.00)


def _visual_groups(pdf: Path, page: int) -> list[tuple[float, float]]:
    """Group rendered line fragments by shared top edge; return (yMin, yMax)."""
    groups: dict[float, float] = {}
    for line in _page_lines(pdf, page):
        key = round(line.y_min, 2)
        groups[key] = max(groups.get(key, line.y_min), line.y_max)
    return sorted(groups.items())


def _heading_and_next(pdf: Path, page: int) -> tuple[tuple[float, float], tuple[float, float]]:
    groups = _visual_groups(pdf, page)
    # Skip a small kicker (about 12.8 pt tall). The heading is the first real
    # text line after it, even for a level-3 heading whose line box is shorter
    # than the standfirst's. Bookify v2 D4 prints a 40 pt chapter numeral above
    # the level-1 title (a ~61 pt line box); the title is the line after it.
    index = next(
        (position for position, (top, bottom) in enumerate(groups) if bottom - top >= 14.0),
        None,
    )
    assert index is not None, f"no heading found on page {page}"
    if groups[index][1] - groups[index][0] > 45.0:
        index += 1
        assert index < len(groups), f"chapter numeral on page {page} has no title"
    assert index + 1 < len(groups), f"no standfirst/lead line follows the heading on page {page}"
    return groups[index], groups[index + 1]


@lru_cache(maxsize=None)
def _ink_bands(pdf: Path, page: int, y_from: float, y_to: float) -> tuple[tuple[int, int], ...]:
    """Merge rows with ink into vertical bands inside the given point window."""
    work = ROOT / ".cache" / "layout-correction-ink"
    work.mkdir(parents=True, exist_ok=True)
    stem = work / f"{pdf.stem}-p{page}"
    subprocess.run(
        ["pdftoppm", "-f", str(page), "-l", str(page), "-png", "-r", "300", str(pdf), str(stem)],
        check=True,
        capture_output=True,
    )
    rendered = sorted(stem.parent.glob(f"{stem.name}-*.png"))
    assert len(rendered) == 1, f"expected one render for {pdf.name} page {page}: {rendered}"
    image = Image.open(rendered[0]).convert("L")
    pixels = image.load()
    scale = 300 / 72
    x0, x1 = int(58 * scale), int(538 * scale)
    rows = [
        y
        for y in range(max(0, int(y_from * scale)), min(image.height, int(y_to * scale)))
        if any(pixels[x, y] < 250 for x in range(x0, x1))
    ]
    assert rows, f"no ink found between {y_from} and {y_to} pt on page {page}"
    bands: list[tuple[int, int]] = []
    start = previous = rows[0]
    for row in rows[1:]:
        if row - previous > 1:
            bands.append((start, previous))
            start = row
        previous = row
    bands.append((start, previous))
    return tuple(bands)


def _ink_gap_pt(pdf: Path, page: int, heading: tuple[float, float], following: tuple[float, float]) -> float:
    bands = _ink_bands(pdf, page, heading[0] - 1, following[1] + 1)
    assert len(bands) >= 2, "the heading ink touches the standfirst ink; no white row"
    return (bands[1][0] - bands[0][1] - 1) * 72 / 300


def _deck_opener(prefix: str, standfirst: bool) -> dict:
    section = {
        "id": f"sec-{prefix}",
        "title": "Reading a sample",
        "level": 1,
        "blocks": [
            _paragraph(f"b-{prefix}-body", "A sample can be read at several levels: what is visible, what the setting suggests, and what remains uncertain.")
        ],
    }
    if standfirst:
        section["standfirst"] = (
            "A synthetic chapter that exercises every typographic element the pipeline must carry "
            "and records the limits of the reading before the page is compiled."
        )
    else:
        section["blocks"].insert(
            0,
            {
                "id": f"b-{prefix}-lead",
                "type": "lead",
                "text": "These notes describe one small synthetic case. They are written for a reading exercise, not as a report of an observation.",
            },
        )
    return section


def test_level1_deck_gap_is_clear_and_levels_2_3_keep_their_hierarchy() -> None:
    path = _write_manuscript(
        "openers",
        [
            _deck_opener("deck", standfirst=True),
            {**_deck_opener("lead", standfirst=False), "title": "A lead opener", "breakBefore": "page"},
            {
                "id": "sec-h2",
                "title": "Minor section",
                "level": 2,
                "breakBefore": "page",
                "standfirst": "A minor-section standfirst that is long enough to wrap onto a second line so the pitch can be measured.",
                "blocks": [_paragraph("b-h2")],
            },
            {
                "id": "sec-h3",
                "title": "Subsection",
                "level": 3,
                "breakBefore": "page",
                "standfirst": "A subsection standfirst that is long enough to wrap onto a second line so the pitch can be measured.",
                "blocks": [_paragraph("b-h3")],
            },
        ],
    )
    result = _build(path, "openers")

    standfirst_heading, standfirst_line = _heading_and_next(result.pdf, 3)
    lead_heading, lead_line = _heading_and_next(result.pdf, 4)
    h2_heading, h2_line = _heading_and_next(result.pdf, 5)
    h3_heading, h3_line = _heading_and_next(result.pdf, 6)

    # Level 1 opens a real deck gap: baseline delta clears the 30 pt h1 pitch
    # and the 3 pt full-width white band at 300 dpi.
    for page, heading, following in ((3, standfirst_heading, standfirst_line), (4, lead_heading, lead_line)):
        delta = following[0] - heading[0]
        assert delta >= 31.25, f"page {page} h1→deck delta {delta} is still cramped"
        assert _ink_gap_pt(result.pdf, page, heading, following) >= 3.0
    assert abs((standfirst_line[0] - standfirst_heading[0]) - (lead_line[0] - lead_heading[0])) <= 0.15

    # Level 2/3 standfirsts keep their pre-existing spacing and stay ordered.
    assert abs((h2_line[0] - h2_heading[0]) - 13.61) <= 0.15
    assert abs((h3_line[0] - h3_heading[0]) - 11.18) <= 0.15
    # The type hierarchy is compared by measured heading height (the opener now
    # prints a numeral above the title, so absolute page position is not the
    # hierarchy any more).
    heights = [
        block[1] - block[0]
        for block in (standfirst_heading, h2_heading, h3_heading)
    ]
    assert heights[0] > heights[1] > heights[2], heights
    assert (standfirst_line[0] - standfirst_heading[0]) > (h2_line[0] - h2_heading[0]) > (h3_line[0] - h3_heading[0])

    # The deck gap stays close to the contents page's own h1→entry rhythm.
    contents_heading, contents_entry = _heading_and_next(result.pdf, 2)
    contents_delta = contents_entry[0] - contents_heading[0]
    assert abs(contents_delta - 31.08) <= 0.15
    assert abs((standfirst_line[0] - standfirst_heading[0]) - contents_delta) <= 2.0

    # The lead pitch and lead→body gap are unchanged.
    assert abs((standfirst_line[0] - standfirst_heading[0]) - 32.75) <= 0.2
    body_lines = sorted(_page_lines(result.pdf, 3), key=lambda line: line.y_min)
    body_index = next(
        index for index, line in enumerate(body_lines) if line.text.startswith("A sample can be read")
    )
    assert abs((body_lines[body_index].y_min - body_lines[body_index - 1].y_min) - 19.20) <= 0.15


PUBLISHED_OPENERS = (
    ("specimen", ROOT / "dist" / "specimen.pdf"),
    ("catalogue", ROOT / "dist" / "catalogue.pdf"),
    ("source-faithful", ROOT / "content" / "agent-skill" / "source-faithful" / "evidence" / "source-faithful.pdf"),
    ("teachable", ROOT / "content" / "agent-skill" / "teachable" / "evidence" / "teachable-textbook.pdf"),
)


@pytest.mark.parametrize("name, pdf", PUBLISHED_OPENERS, ids=[name for name, _ in PUBLISHED_OPENERS])
def test_published_level1_openers_show_the_deck_gap(name: str, pdf: Path) -> None:
    if not pdf.is_file():
        pytest.skip(f"{name} published PDF is not present in this checkout")
    heading, following = _heading_and_next(pdf, 3)
    delta = following[0] - heading[0]
    assert delta >= 31.25, f"{name} h1→deck delta {delta} is still cramped"
    assert delta > 30.00, f"{name} deck delta {delta} does not clear the h1 pitch"
    assert _ink_gap_pt(pdf, 3, heading, following) >= 3.0, f"{name} has no clear white band"


def _write_manuscript(name: str, sections: list[dict], *, revision: int = 1) -> Path:
    work = ROOT / ".cache" / f"layout-correction-{name}"
    work.mkdir(parents=True, exist_ok=True)
    data = {
        "schemaVersion": "1.0",
        "revision": revision,
        "id": f"layout-correction-{name}",
        "metadata": {"title": f"Layout correction {name}", "languages": ["en"]},
        "sections": sections,
    }
    path = work / "manuscript.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return path


def _build(path: Path, name: str) -> typst_driver.BuildResult:
    work = path.parent
    return typst_driver.build(path, work / f"{name}.pdf", work / "build", offline=True)


def _paragraph(block_id: str, text: str = LATIN) -> dict:
    return {"id": block_id, "type": "paragraph", "text": text}


def test_nested_levels_flow_and_a_chapter_break_is_explicit() -> None:
    path = _write_manuscript(
        "nested",
        [
            {"id": "sec-a", "title": "Chapter A", "level": 1, "blocks": [_paragraph("b-a")]},
            {"id": "sec-b", "title": "Minor B", "level": 2, "blocks": [_paragraph("b-b")]},
            {"id": "sec-c", "title": "Sub C", "level": 3, "blocks": [_paragraph("b-c")]},
            {"id": "sec-d", "title": "Minor D", "level": 2, "blocks": [_paragraph("b-d")]},
            {"id": "sec-e", "title": "Chapter E", "level": 1, "blocks": [_paragraph("b-e")]},
            {
                "id": "sec-f",
                "title": "Flowing chapter F",
                "level": 1,
                "breakBefore": "auto",
                "blocks": [_paragraph("b-f")],
            },
        ],
    )
    result = _build(path, "nested")
    by_title = {section["title"]: section["page"] for section in result.report["sections"]}

    assert by_title["Chapter A"] == 3
    assert by_title["Minor B"] == by_title["Chapter A"]
    assert by_title["Sub C"] == by_title["Chapter A"]
    assert by_title["Minor D"] >= by_title["Sub C"]
    assert by_title["Chapter E"] > by_title["Minor D"]
    assert by_title["Flowing chapter F"] == by_title["Chapter E"]
    assert pages.blank_pages(result.pdf) == []


def test_first_section_break_before_page_never_creates_a_blank_page() -> None:
    path = _write_manuscript(
        "first-break",
        [
            {
                "id": "sec-a",
                "title": "Opening",
                "level": 1,
                "breakBefore": "page",
                "blocks": [_paragraph("b-a")],
            },
            {"id": "sec-b", "title": "Second", "level": 1, "blocks": [_paragraph("b-b")]},
        ],
    )
    result = _build(path, "first-break")

    assert result.report["sections"][0]["page"] == 3
    # cover + contents + two chapters; the explicit break on the first body
    # section is ignored rather than adding a third blank page.
    assert result.report["pdf"]["pages"] == 4
    assert pages.blank_pages(result.pdf) == []


def test_invalid_hierarchy_is_rejected_with_a_named_section() -> None:
    first_level_two = _write_manuscript(
        "bad-first",
        [{"id": "sec-a", "title": "Orphan", "level": 2, "blocks": [_paragraph("b-a")]}],
    )
    skipped = _write_manuscript(
        "bad-skip",
        [
            {"id": "sec-a", "title": "Chapter", "level": 1, "blocks": [_paragraph("b-a")]},
            {"id": "sec-b", "title": "Sub", "level": 3, "blocks": [_paragraph("b-b")]},
        ],
    )
    duplicate = _write_manuscript(
        "bad-duplicate",
        [
            {"id": "sec-a", "title": "Overview", "level": 1, "blocks": [_paragraph("b-a")]},
            {"id": "sec-b", "title": "Overview", "level": 2, "blocks": [_paragraph("b-b")]},
        ],
    )
    bad_level = _write_manuscript(
        "bad-level",
        [{"id": "sec-a", "title": "Too deep", "level": 4, "blocks": [_paragraph("b-a")]}],
    )
    bad_break = _write_manuscript(
        "bad-break",
        [
            {
                "id": "sec-a",
                "title": "Bad break",
                "level": 1,
                "breakBefore": "sometimes",
                "blocks": [_paragraph("b-a")],
            }
        ],
    )

    with pytest.raises(BookifyError) as error:
        model.load(first_level_two)
    assert error.value.code == "SCHEMA_INVALID"
    assert error.value.locator == "sections[0].level"

    with pytest.raises(BookifyError) as error:
        model.load(skipped)
    assert error.value.code == "SCHEMA_INVALID"
    assert error.value.locator == "sections[1].level"

    with pytest.raises(BookifyError) as error:
        model.load(duplicate)
    assert error.value.code == "SCHEMA_INVALID"
    assert error.value.locator == "sections[1].title"

    for invalid in (bad_level, bad_break):
        with pytest.raises(BookifyError) as error:
            model.load(invalid)
        assert error.value.code == "SCHEMA_INVALID"


def test_kicker_and_heading_stay_together_at_a_page_foot() -> None:
    filler = ("filler words to consume the text frame " * 160).strip()
    path = _write_manuscript(
        "kicker",
        [
            {"id": "sec-a", "title": "Filler", "level": 1, "blocks": [_paragraph("b-a", filler)]},
            {
                "id": "sec-b",
                "title": "Sticky heading",
                "level": 2,
                "kicker": "KICKER-MARKER",
                "blocks": [_paragraph("b-b", "Body after the sticky heading.")],
            },
        ],
    )
    result = _build(path, "kicker")
    lines = [line for line in _lines(result.pdf) if line.page >= 3]
    kicker = next(line for line in lines if line.text.strip() == "KICKER-MARKER")
    heading = next(line for line in lines if "Sticky heading" in line.text)
    assert kicker.page == heading.page
    assert "sticky: true" in (ROOT / "typst" / "templates" / "book.typ").read_text()


def test_a_plate_section_keeps_heading_note_image_caption_and_credit_together() -> None:
    path = _write_manuscript(
        "plate",
        [
            {
                "id": "sec-plate",
                "title": "Plate chapter",
                "level": 1,
                "blocks": [
                    {"id": "b-note", "type": "unresolved", "note": "PLATE-NOTE unresolved."},
                    {"id": "b-photo", "type": "illustration", "illustrationId": "photo-1"},
                ],
            }
        ],
    )
    result = _build(path, "plate")
    document = result.pdf
    lines = _lines(document)
    body_lines = [line for line in lines if line.page >= 3]
    wanted = ("Plate", "chapter", "PLATE-NOTE", "Photograph 1.", "Photo: William Ng")
    pages_seen: set[int] = set()
    for marker in wanted:
        matches = [line for line in body_lines if marker in line.text]
        assert matches, f"missing rendered text: {marker}"
        pages_seen.add(matches[0].page)
    assert len(pages_seen) == 1, f"plate unit split across pages: {pages_seen}"
    assert pages.blank_pages(document) == []


def test_a_wrapped_side_caption_is_not_mistaken_for_a_detached_unit() -> None:
    long_caption = (
        "A deliberately long side caption that must wrap onto at least two lines "
        "inside the narrow image column while the companion prose wraps on the same "
        "baselines in the other column, so the fit guard has to keep columns apart."
    )
    path = _write_manuscript(
        "side-caption",
        [
            {
                "id": "sec-a",
                "title": "Side caption",
                "level": 1,
                "blocks": [
                    {
                        "id": "b-photo",
                        "type": "illustration",
                        "illustrationId": "photo-1",
                        "caption": long_caption,
                        "composition": {"preset": "side-left", "companion": "b-text"},
                    },
                    {
                        "id": "b-text",
                        "type": "paragraph",
                        "text": "SIDE-COMPANION-MARKER " + LATIN,
                    },
                ],
            }
        ],
    )
    result = _build(path, "side-caption")
    assert result.report["placements"][0]["page"] is not None
    assert pages.page_texts(result.pdf)[result.report["placements"][0]["page"] - 1].count("Photograph 1.") == 1


def test_two_illustrations_still_get_one_page_each_after_reflow() -> None:
    path = _write_manuscript(
        "illustrations",
        [
            {
                "id": "sec-a",
                "title": "Two photographs",
                "level": 1,
                "blocks": [
                    {"id": "b-photo-a", "type": "illustration", "illustrationId": "photo-1"},
                    {"id": "b-photo-b", "type": "illustration", "illustrationId": "hist-1"},
                ],
            }
        ],
    )
    result = _build(path, "illustrations")
    placements = result.report["placements"]
    assert len({placement["page"] for placement in placements}) == 2
    for page in {placement["page"] for placement in placements}:
        assert pages.page_texts(result.pdf)[page - 1].count("Photograph ") == 1


def _table_pdf() -> Path:
    rows = "(" + ", ".join(f"([ROW-{index} {LATIN}],)" for index in range(60)) + ",)"
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f'#preset-table(([HEADER-A],), {rows}, caption: "CAPTION-MARKER")\n'
    )
    return compile_typ(source, "layout-correction-table")


def test_long_table_repeats_its_header_and_keeps_one_caption_with_the_last_rows() -> None:
    import subprocess

    pdf = _table_pdf()
    texts = pages.page_texts(pdf)
    assert len(texts) >= 2
    assert sum(text.count("CAPTION-MARKER") for text in texts) == 1
    table_pages = [index for index, text in enumerate(texts, start=1) if "ROW-" in text]
    for index in table_pages:
        assert "HEADER-A" in texts[index - 1], f"page {index} lost the repeated header"
    caption_page = next(index for index, text in enumerate(texts, start=1) if "CAPTION-MARKER" in text)
    last_row_page = next(index for index, text in enumerate(texts, start=1) if "ROW-59" in text)
    assert caption_page == last_row_page


def test_an_oversize_full_unit_fails_closed_with_its_block_id() -> None:
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#preset-illustration(\n"
        "  rect(width: 100%, height: 1300pt, fill: black),\n"
        '  caption: "Photograph 1. An over-tall illustration unit.",\n'
        '  credit: "Photo: Test.",\n'
        ")\n"
    )
    pdf = compile_typ(source, "layout-correction-oversize")
    document = {
        "sections": [
            {
                "blocks": [
                    {
                        "id": "b-photo",
                        "type": "illustration",
                        "label": "Photograph 1",
                        "caption": "Photograph 1. An over-tall illustration unit.",
                        "credit": "Photo: Test.",
                    }
                ]
            }
        ]
    }

    with pytest.raises(BookifyError) as error:
        report.require_unit_fit(pdf, document, {"Photograph 1": 1}, 841.89)
    assert error.value.code == "BUILD_FAILED"
    assert error.value.locator == "b-photo"


def test_contents_paginate_and_xrefs_see_every_section() -> None:
    sections: list[dict] = [{"id": "sec-0", "title": "Chapter 0", "level": 1, "blocks": [_paragraph("b-0")]}]
    for index in range(1, 60):
        level = 2 if index % 3 else 3
        sections.append(
            {
                "id": f"sec-{index}",
                "title": f"Section {index}",
                "level": level,
                "blocks": [_paragraph(f"b-{index}", f"Body {index}.")],
            }
        )
    path = _write_manuscript("contents", sections)
    result = _build(path, "contents")

    assert len(result.report["contentsPages"]) >= 2
    assert all(section["page"] for section in result.report["sections"])
    manuscript = model.load(path)
    check = xrefs.check(result.pdf, manuscript)
    assert check.status == "pass", check.detail
