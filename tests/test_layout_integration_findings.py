"""Independent verification findings for the production layout integration.

These are Prove-It tests: every one of them fails against the current
implementation and must pass after the debugger's fix. They are keyed to the
contract in `.opencode/layout-integration-task.md` and the accepted proofs under
`docs/design/proofs/`; they deliberately do not encode a new design.

Builds use the real production entry (`typst_driver.build`) and the same public
fixtures as the rest of the suite. Nothing here touches product code or the
installed payload.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from helpers import ROOT
from bookify.manuscript import model
from bookify.publish import normalize, typst_driver
from bookify.verify.checks import captions, cover, rhythm, xrefs

WORK = ROOT / ".cache" / "test-writer-layout-findings"

LONG = (
    "A measured paragraph of public-safe prose that fills a column and carries the "
    "reader to the next line. "
)


def _write(name: str, sections: list[dict], metadata: dict) -> Path:
    directory = WORK / name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "book.yaml"
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": name,
        "metadata": metadata,
        "sections": sections,
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return path


def _build(name: str, sections: list[dict], metadata: dict):
    path = _write(name, sections, metadata)
    return path, typst_driver.build(
        path, WORK / name / "book.pdf", WORK / name / "build", offline=True
    )


def _metadata(title: str, **extra) -> dict:
    return {
        "title": title,
        "languages": ["en"],
        "institution": "Example Institute",
        "course": "Layout Verification",
        "author": "Bookify verification",
        **extra,
    }


def _paragraph(block_id: str, text: str) -> dict:
    return {"id": block_id, "type": "paragraph", "text": text}


def _chapter(blocks: list[dict], *, level: int = 1, title: str = "A Chapter", **extra) -> dict:
    return {"id": f"sec-{title.lower().replace(' ', '-')}", "title": title, "level": level, "blocks": blocks, **extra}


def _assert_rectangles_do_not_overlap(first: captions.LineBox, second: captions.LineBox) -> None:
    overlaps_x = first.x_min < second.x_max and second.x_min < first.x_max
    overlaps_y = first.y_min < second.y_max and second.y_min < first.y_max
    assert not (overlaps_x and overlaps_y), (
        f"{first.text!r} overlaps {second.text!r}: "
        f"({first.x_min:.2f},{first.y_min:.2f})-({first.x_max:.2f},{first.y_max:.2f}) vs "
        f"({second.x_min:.2f},{second.y_min:.2f})-({second.x_max:.2f},{second.y_max:.2f})"
    )


def _stream(text: str) -> str:
    return re.sub(r"[\s\u00ad]", "", text)


def test_numbering_is_the_hierarchical_path() -> None:
    """`Chapter 1: Title` -> `1.1` -> `1.1.1` -> `1.1.1 a)` -> `1.1.1.1`.

    Decision (2026-11-21): the earlier path put the first body heading at `1.`
    and gave the second level-2 sibling a trailing period (`1.2.`). That made
    the printed reference unresolvable — `§1.` was also a chapter reference
    followed by a sentence full stop, and `§1.2.` was both the second section
    and a subsection plus punctuation. Every level now carries its full path, so
    the heading, the contents and the `§` reference print the same number and no
    number ends with a period. A terminal branch follows its own section.
    """
    path = _write(
        "numbering",
        [
            _chapter([_paragraph("b-open", "OPEN. " + LONG * 3)], title="First Chapter"),
            _chapter([_paragraph("b-sec", "SEC. " + LONG * 2)], level=2, title="Section One"),
            _chapter(
                [
                    _paragraph("b-sub", "SUB. " + LONG * 2),
                    {"id": "b-branch-a", "type": "branch", "text": "The first terminal branch."},
                    {"id": "b-branch-b", "type": "branch", "text": "The second terminal branch."},
                ],
                level=3,
                title="Subsection One",
            ),
            _chapter([_paragraph("b-deep", "DEEP. " + LONG * 2)], level=4, title="Continuing Branch"),
        ],
        _metadata("Numbering Check"),
    )
    document = normalize.build(model.load(path, root=ROOT), {}).data
    printed = [section["printed"] for section in document["sections"]]

    assert printed == ["1", "1.1", "1.1.1", "1.1.1.1"], printed
    assert document["sections"][2]["blocks"][1]["marker"] == "1.1.1 a)"
    assert document["sections"][2]["blocks"][2]["marker"] == "1.1.1 b)"


def test_a_level_four_section_is_in_the_contents_and_passes_xrefs() -> None:
    """Contents depth must reach level 4, or a real manuscript fails xrefs."""
    sections = [
        _chapter([_paragraph("b-open", "OPEN. " + LONG * 6)], title="First Chapter"),
        _chapter([_paragraph("b-sec", "SEC. " + LONG * 3)], level=2, title="Section One"),
        _chapter([_paragraph("b-sub", "SUB. " + LONG * 3)], level=3, title="Subsection One"),
        _chapter([_paragraph("b-deep", "DEEP. " + LONG * 3)], level=4, title="Deep Subheading"),
    ]
    path, result = _build("level-four", sections, _metadata("Level Four Book"))
    check = xrefs.check(result.pdf, model.load(path, root=ROOT))

    assert check.status == "pass", check.detail


def test_a_centred_figure_section_keeps_the_heading_above_gap() -> None:
    """A pure-plate section is a keep unit; its heading still needs its 32 pt gap.

    Wrapping heading+figure in `block(breakable: false)` currently swallows the
    heading's `above` spacing: the measured h2 above gap is 19.70 pt, below the
    36.0 pt the rhythm gate requires.
    """
    sections = [
        _chapter(
            [
                _paragraph(
                    "b-open",
                    "OPEN. A measured paragraph of public-safe prose that leaves the next "
                    "heading in the middle of a page. " * 2,
                )
            ],
            title="First Chapter",
        ),
        _chapter(
            [
                {
                    "id": "b-photo",
                    "type": "illustration",
                    "illustrationId": "hist-1",
                    "caption": "A centred photograph directly under the heading.",
                    "composition": {"preset": "centred"},
                }
            ],
            level=2,
            title="Under a Figure",
        ),
    ]
    path, result = _build("pure-plate-heading", sections, _metadata("Pure Plate Heading"))
    check = rhythm.check(result.pdf, model.load(path, root=ROOT))

    assert check.status == "pass", check.detail
    entry = next(item for item in check.evidence["headingClearance"] if item["section"] == "Under a Figure")
    assert entry["clearancePt"] is not None


def test_a2_chart_caption_and_plate_are_measured_in_their_column() -> None:
    """An A2 chart occupies one 229.64 pt column, not the whole page.

    The caption is centred in its own column and the report records a column
    visual at its real width; it must not claim a 475.28 pt plate or fail the
    page-centre caption check.
    """
    sections = [
        _chapter(
            [
                _paragraph("b-before", "BEFORE. " + LONG * 4),
                {
                    "id": "b-chart",
                    "type": "chart",
                    "caption": "A synthetic chart inside a two-column chapter, with a caption long enough to wrap and show its column centring.",
                    "confidence": "inferred",
                    "note": "Synthetic values authored for this verification manuscript; not measurements.",
                    "chart": {
                        "kind": "grouped_bar",
                        "categories": ["A", "B", "C"],
                        "series": [{"id": "s1", "label": "Value"}],
                        "values": [[72], [64], [58]],
                        "axis": {"unit": "units", "min": 0, "max": 100},
                        "verification": "synthetic",
                        "notes": "Authored for this verification; no external data.",
                    },
                },
                _paragraph("b-after", "AFTER. " + LONG * 4),
            ],
            title="Columns with a Chart",
            layout={"columns": 2},
            standfirst="The standfirst spans the full measure above both columns.",
        )
    ]
    path, result = _build("a2-chart", sections, _metadata("A Two-Column Book"))
    manuscript = model.load(path, root=ROOT)
    check = captions.check(result.pdf, manuscript)

    assert check.status == "pass", check.detail
    assert result.report["plates"] == []
    visuals = result.report["visuals"]
    assert len(visuals) == 1
    assert visuals[0]["preset"] == "full"
    assert abs(visuals[0]["widthPt"] - 229.64) <= 2.0
    assert visuals[0]["basis"] == "measured"


def test_cover_five_renders_a_two_line_title() -> None:
    """Cover 5 must wrap a realistic title, not clip it off the page.

    The current fitted title box runs past the page; a 45-character title fails
    the build as "cover title was not rendered completely".
    """
    path, result = _build(
        "cover-five",
        [
            _chapter([_paragraph("b-one", LONG * 6)], title="Sources"),
            _chapter([_paragraph("b-two", LONG * 6)], title="Method"),
        ],
        _metadata("Evidence and Interpretation in Modern History", cover={"composition": "cover-5"}),
    )

    assert result.pdf.is_file()
    page = captions.read_lines(result.pdf)
    assert any("Modern History" in line.text or "Modern" in line.text for line in page if line.page == 1)


@pytest.mark.parametrize("composition", ["cover-6", "cover-7"])
def test_two_line_cover_title_does_not_collide_with_its_subtitle(composition: str) -> None:
    """A subtitle must not be printed through a two-line title.

    Covers 6 and 7 position the support line for a one-line title only; with a
    normal two-line title the subtitle overlaps the title ink (and the build and
    cover check both pass).
    """
    _, result = _build(
        f"{composition}-overlap",
        [
            _chapter([_paragraph("b-one", LONG * 6)], title="Sources"),
            _chapter([_paragraph("b-two", LONG * 6)], title="Method"),
        ],
        _metadata(
            "Evidence and Interpretation in Modern History",
            subtitle="A short book of method",
            cover={"composition": composition},
        ),
    )
    page = [line for line in captions.read_lines(result.pdf) if line.page == 1]
    title_stream = _stream("Evidence and Interpretation in Modern History")
    subtitle_stream = _stream("A short book of method")

    title_lines = [
        line for line in page
        if _stream(line.text) and _stream(line.text) in title_stream and _stream(line.text) != subtitle_stream
    ]
    subtitle = next(line for line in page if _stream(line.text) == subtitle_stream)
    assert title_lines, page
    for title_line in title_lines:
        _assert_rectangles_do_not_overlap(title_line, subtitle)


def test_cover_rejects_no_chapter_title_when_it_matches_other_metadata() -> None:
    """A chapter title that is a word in the course or subtitle is not an index.

    The cover check currently searches the whole cover text for each chapter
    title, so `Method` matches `Methods 101` and every cover fails with
    "cover prints chapter titles: 1".
    """
    path, result = _build(
        "cover-substring",
        [
            _chapter([_paragraph("b-one", LONG * 6)], title="Sources"),
            _chapter([_paragraph("b-two", LONG * 6)], title="Method"),
        ],
        _metadata(
            "Evidence and Interpretation in Modern History",
            subtitle="A short book of method",
            course="Methods 101",
            cover={"composition": "cover-3"},
        ),
    )
    check = cover.check(result.pdf, model.load(path, root=ROOT))

    assert check.status == "pass", check.detail


def test_cross_reference_numbers_are_unique_for_every_section() -> None:
    """`number` is the cross-reference form; two sections may not share it.

    Regression guard for the retired `1.` / `1.2.` scheme, under which the
    chapter and the first level-2 heading both had the reference `1`, and a
    subsection (`1.2`) shared its reference with the second level-2 sibling.
    The hierarchical path makes the field injective by construction, so this test
    must keep failing any scheme that reintroduces a collision.
    """
    sections = [
        _chapter([_paragraph("b-ch", "A chapter paragraph.")], title="First Chapter"),
        _chapter([_paragraph("b-a", "Section A.")], level=2, title="Section A"),
        _chapter([_paragraph("b-a1", "Subsection A1.")], level=3, title="Subsection A1"),
        _chapter([_paragraph("b-a2", "Subsection A2.")], level=3, title="Subsection A2"),
        _chapter([_paragraph("b-b", "Section B.")], level=2, title="Section B"),
    ]
    path = _write("unique-numbers", sections, _metadata("Unique Numbers"))
    manuscript = model.load(path, root=ROOT)
    numbers = normalize.section_numbers(manuscript)

    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for number in numbers:
        if number["number"] in seen:
            duplicates.append(f'{number["number"]} ({seen[number["number"]]} / {number["printed"]})')
        seen[number["number"]] = number["printed"]
    assert not duplicates, duplicates


def test_level_five_section_rhythm_does_not_crash() -> None:
    """A level-5 section must be measurable, not a `KeyError: 5` in verify."""
    sections = [
        _chapter([_paragraph("b-1", "A chapter paragraph. " * 8)], title="First Chapter"),
        _chapter([_paragraph("b-2", "A section paragraph. " * 8)], level=2, title="Section"),
        _chapter([_paragraph("b-3", "A subsection paragraph. " * 8)], level=3, title="Subsection"),
        _chapter([_paragraph("b-4", "A branch paragraph. " * 8)], level=4, title="Branch"),
        _chapter([_paragraph("b-5", "A deeper paragraph. " * 8)], level=5, title="Deeper Branch"),
    ]
    path, result = _build("level-five-rhythm", sections, _metadata("Level Five"))
    check = rhythm.check(result.pdf, model.load(path, root=ROOT))

    assert check.status in {"pass", "warn"}, check.detail
    assert any(item["section"] == "Deeper Branch" for item in check.evidence["headingClearance"])


def test_a2_descendant_figure_caption_is_measured_in_its_column() -> None:
    """A figure in an A2 descendant section is still inside the columns.

    `expected_captions` currently reads only the block's own section layout; a
    level-2 child has no `layout`, so its caption is measured against the page
    centre and fails by ~123 pt even though it is centred in its column.
    """
    sections = [
        _chapter(
            [_paragraph(f"b-p{i}", "PARA. " + LONG * 2) for i in range(1, 5)],
            title="Two Columns",
            layout={"columns": 2},
            standfirst="The standfirst spans the full measure.",
        ),
        _chapter(
            [
                _paragraph("b-pre", "PRE. " + LONG * 2),
                {
                    "id": "b-chart",
                    "type": "chart",
                    "caption": "A chart in a descendant section of a two-column chapter, with a caption long enough to wrap.",
                    "confidence": "inferred",
                    "note": "Synthetic values authored for this verification; not measurements.",
                    "chart": {
                        "kind": "grouped_bar",
                        "categories": ["A", "B", "C"],
                        "series": [{"id": "s1", "label": "Value"}],
                        "values": [[72], [64], [58]],
                        "axis": {"unit": "units", "min": 0, "max": 100},
                        "verification": "synthetic",
                        "notes": "Authored for this verification; no external data.",
                    },
                },
                _paragraph("b-post", "POST. " + LONG * 2),
            ],
            level=2,
            title="A Subsection With a Figure",
        ),
    ]
    path, result = _build("a2-descendant-figure", sections, _metadata("Descendant Figure"))
    manuscript = model.load(path, root=ROOT)
    check = captions.check(result.pdf, manuscript)
    assert check.status == "pass", check.detail


def test_mixed_page_does_not_mark_single_column_chapter_pages_as_columns() -> None:
    """A chapter authored `breakBefore: auto` after an A2 chapter stays single.

    The two-column page declaration currently runs to the next level-1 start
    that is *later* than the A2 start; a chapter starting on the same page is
    skipped, so all of its following single-column pages are declared columns.
    """
    sections = [
        _chapter(
            [_paragraph(f"b-a{i}", "COL. " + LONG * 4) for i in range(1, 5)],
            title="Two Columns",
            layout={"columns": 2},
            standfirst="The standfirst spans the full measure.",
        ),
        _chapter(
            [_paragraph(f"b-s{i}", "SINGLE. " + LONG * 6) for i in range(1, 6)],
            title="Single Column After",
            breakBefore="auto",
        ),
        _chapter(
            [_paragraph("b-sub", "SUBSECTION. " + LONG * 4)],
            level=2,
            title="Single Subsection",
        ),
    ]
    path, result = _build("mixed-boundary", sections, _metadata("Mixed Boundary"))
    check = rhythm.check(result.pdf, model.load(path, root=ROOT))

    assert check.status in {"pass", "warn"}, check.detail
    assert 4 not in check.evidence["columnPages"], check.evidence["columnPages"]


def test_a_realistic_three_line_title_builds_on_every_cover() -> None:
    """A 57-character title is three lines at the full measure; all seven covers.

    Covers 5 and 6 currently need four lines because their title boxes are
    narrower than the measure, so those two compositions fail for a title the
    other five accept.
    """
    title = "Evidence and Interpretation in Modern Historical Practice"
    sections = [
        _chapter([_paragraph("b-one", LONG * 6)], title="Sources"),
        _chapter([_paragraph("b-two", LONG * 6)], title="Method"),
    ]
    failures: list[str] = []
    for index in range(1, 8):
        try:
            _build(
                f"three-line-cover-{index}",
                sections,
                _metadata(title, cover={"composition": f"cover-{index}"}),
            )
        except Exception as error:  # noqa: BLE001 - the build error is the finding
            failures.append(f"cover-{index}: {error}")
    assert not failures, failures


def test_side_composition_is_refused_in_a_two_column_descendant(tmp_path: Path) -> None:
    """A side grid cannot exist inside an A2 column, even in a child section.

    The model refuses a side composition only when its own section has
    `layout.columns == 2`; a level-2 child of a two-column chapter inherits the
    column flow at render time but passes validation, and the build then squeezes
    a 46 % image column plus a one-word-wide prose column into 229.64 pt.
    """
    from bookify.errors import BookifyError

    sections = [
        _chapter(
            [_paragraph(f"b-p{i}", "PARA. " + LONG * 4) for i in range(1, 5)],
            title="Two Columns",
            layout={"columns": 2},
            standfirst="The standfirst spans the full measure.",
        ),
        _chapter(
            [
                {
                    "id": "b-photo",
                    "type": "illustration",
                    "illustrationId": "hist-1",
                    "caption": "A side photograph inside a descendant of a two-column chapter.",
                    "composition": {"preset": "side-left", "companion": "b-text"},
                },
                _paragraph("b-text", "Companion prose."),
            ],
            level=2,
            title="Side Subsection",
        ),
    ]
    path = _write("a2-side-descendant", sections, _metadata("Side In Descendant"))
    with pytest.raises(BookifyError) as error:
        model.load(path, root=ROOT)

    assert error.value.code == "SCHEMA_INVALID"
    assert "two-column" in str(error.value)
    assert error.value.locator.endswith(".composition")


def test_pure_plate_chapter_keeps_its_heading_above_gap() -> None:
    """A level-1 keep unit still needs a visible gap above its heading.

    A chapter authored `breakBefore: auto` whose only block is a figure is a
    keep unit. `keep-above` is supposed to put the 17 pt heading gap on the block,
    but the rendered heading sits 2.3 pt below the preceding prose
    (`Chapter 2: Plate Only` at y=143.5 after a line ending at y=141.2).
    """
    sections = [
        _chapter([_paragraph("b-p1", "P1. " + LONG * 2)], title="Prose Chapter"),
        _chapter(
            [
                {
                    "id": "b-photo",
                    "type": "illustration",
                    "illustrationId": "hist-1",
                    "caption": "A plate-only chapter directly under its heading.",
                    "composition": {"preset": "centred"},
                }
            ],
            title="Plate Only",
            breakBefore="auto",
        ),
    ]
    path, result = _build("pure-plate-chapter", sections, _metadata("Pure Plate Chapter"))
    all_lines = list(captions.read_lines(result.pdf))
    heading = next(line for line in all_lines if line.text.startswith("Chapter 2:"))
    lines = sorted(
        [line for line in all_lines if line.page == heading.page],
        key=lambda line: line.y_min,
    )
    previous = max((line for line in lines if line.y_max <= heading.y_min), key=lambda line: line.y_max)

    assert heading.y_min - previous.y_max >= 15.30, (
        heading.y_min - previous.y_max,
        previous.text,
        heading.text,
    )


def test_printed_cross_references_are_unambiguous_in_sentence_context() -> None:
    """A printed `§` token must identify one target, with or without punctuation.

    No number ends with a period, so punctuation after a reference cannot make it
    look like a shorter one: `§1.1.` is section `1.1` plus a full stop, and no
    section is numbered `1.1.`. This is the reader-facing counterpart of
    `test_cross_reference_numbers_are_unique_for_every_section`.
    """
    sections = [
        {
            "id": "s-ch",
            "title": "First Chapter",
            "level": 1,
            "blocks": [
                _paragraph("b-ref-chapter", "Chapter target: {ref:s-ch}."),
                _paragraph("b-ref-section-a", "Section A target: {ref:s-a} in text."),
                _paragraph("b-ref-subsection-a2", "Subsection A2 target: {ref:s-a2}."),
                _paragraph("b-ref-section-b", "Section B target: {ref:s-b} in text."),
            ],
        },
        {"id": "s-a", "title": "Section A", "level": 2, "blocks": [_paragraph("b-a", "A.")]},
        {"id": "s-a1", "title": "Subsection A1", "level": 3, "blocks": [_paragraph("b-a1", "A1.")]},
        {"id": "s-a2", "title": "Subsection A2", "level": 3, "blocks": [_paragraph("b-a2", "A2.")]},
        {"id": "s-b", "title": "Section B", "level": 2, "blocks": [_paragraph("b-b", "B.")]},
    ]
    path = _write("reference-ambiguity", sections, _metadata("Reference Ambiguity"))
    document = normalize.build(model.load(path, root=ROOT), {}).data
    texts = {
        block["id"]: block["text"]
        for section in document["sections"]
        for block in section["blocks"]
        if block["id"].startswith("b-ref-")
    }

    tokens: dict[str, str] = {}
    for block_id, text in texts.items():
        match = re.search(r"§[0-9A-Z.]+", text)
        assert match, (block_id, text)
        tokens[block_id] = match.group(0)
    assert len(set(tokens.values())) == len(tokens), tokens
