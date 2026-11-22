"""Task 47: token-driven full, side-left and side-right illustration composition."""

from __future__ import annotations

import re
import subprocess

import pytest
from pathlib import Path

import yaml

from helpers import ROOT, compile_typ
from bookify.design import lint, tokens
from bookify.manuscript import model
from bookify.publish import report, typst_driver
from bookify.verify.checks import captions, rhythm

PAGE_MARGIN = 60.0
BODY = 475.28
SIDE_FRACTION = 0.46
SIDE_GUTTER = 16.0
LEFT_CENTRE = PAGE_MARGIN + BODY * SIDE_FRACTION / 2  # 169.31
RIGHT_CENTRE = PAGE_MARGIN + BODY - BODY * SIDE_FRACTION / 2  # 425.97
LEFT_EDGE = PAGE_MARGIN  # 60
RIGHT_EDGE = PAGE_MARGIN + BODY - BODY * SIDE_FRACTION  # 316.65
PROSE_LEFT = PAGE_MARGIN + BODY * SIDE_FRACTION + SIDE_GUTTER  # 294.63
PROSE_RIGHT = PAGE_MARGIN + BODY  # 535.28


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _lines(pdf: Path):
    return captions.read_lines(pdf)


def _line(lines, prefix: str):
    return next(line for line in lines if line.text.startswith(prefix))


def _caption_group(lines, label: str, text: str):
    expected = text.split()
    start = next(index for index, line in enumerate(lines) if line.text.startswith(label.split()[0]))
    collected = [lines[start]]
    consumed = len(lines[start].text.split())
    for line in lines[start + 1 :]:
        if consumed >= len(expected):
            break
        words = line.text.split()
        if words == expected[consumed : consumed + len(words)]:
            collected.append(line)
            consumed += len(words)
    assert consumed == len(expected), f"caption not fully rendered: {consumed}/{len(expected)}"
    return collected


def _side_source(
    preset: str,
    caption: str,
    companion: str,
    credit: str = "Photo: A credited source.",
) -> str:
    return (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#preset-illustration(\n"
        "  rect(width: 100%, height: 90pt, fill: black),\n"
        f"  caption: {_q(caption)},\n"
        f"  credit: {_q(credit)},\n"
        f"  composition: {_q(preset)},\n"
        f"  companion: [#preset-paragraph({_q(companion)})],\n"
        ")\n"
    )


def test_theme_carries_the_two_side_tokens_and_the_python_mirror() -> None:
    theme = (ROOT / "typst" / "theme.typ").read_text()

    assert re.search(r"side_fraction:\s*0\.46\b", theme)
    assert re.search(r"side_gutter:\s*16pt\b", theme)
    for name in ("side_fraction", "side_gutter"):
        assert name in tokens.LEAF_NAMES, f"{name} missing from the Python token mirror"


def test_no_visual_literals_and_one_preset_per_block_type_still_hold() -> None:
    assert lint.lint(ROOT) == []
    assert lint.missing_presets(ROOT) == set()


def test_side_left_places_the_image_column_left_and_centres_each_caption_line() -> None:
    caption = (
        "Photograph 1. A deliberately long caption that must wrap onto at least three lines "
        "inside the narrow image column so every wrapped line's centre is measured."
    )
    pdf = compile_typ(
        _side_source("side-left", caption, "Companion prose sits in the right-hand column."),
        "layout-side-left",
    )
    lines = _lines(pdf)

    caption_lines = _caption_group(lines, "Photograph 1.", caption)
    assert len(caption_lines) >= 3
    for line in caption_lines:
        assert abs(line.centre - LEFT_CENTRE) <= 2.0, line.text

    credit = _line(lines, "Photo:")
    assert abs(credit.x_min - LEFT_EDGE) <= 2.0

    prose = _line(lines, "Companion prose")
    assert prose.x_min >= PROSE_LEFT - 1.0
    assert credit.x_min < prose.x_min, "side-left reads image unit then prose"


def test_side_right_mirrors_the_columns_and_credit_edge() -> None:
    caption = (
        "Photograph 2. A deliberately long caption that must wrap onto at least three lines "
        "inside the narrow image column so every wrapped line's centre is measured."
    )
    pdf = compile_typ(
        _side_source("side-right", caption, "Companion prose sits in the left-hand column."),
        "layout-side-right",
    )
    lines = _lines(pdf)

    caption_lines = _caption_group(lines, "Photograph 2.", caption)
    assert len(caption_lines) >= 3
    for line in caption_lines:
        assert abs(line.centre - RIGHT_CENTRE) <= 2.0, line.text

    credit = _line(lines, "Photo:")
    assert abs(credit.x_min - RIGHT_EDGE) <= 2.0

    prose = _line(lines, "Companion prose")
    assert prose.x_max <= PROSE_RIGHT - SIDE_GUTTER + 1.0
    assert prose.x_min < caption_lines[0].x_min, "side-right reads prose then image unit"


def test_full_composition_keeps_the_page_centred_path() -> None:
    caption = "Photograph 1. The full path keeps its page-centred description."
    pdf = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f"#preset-illustration(rect(width: 88%, height: 90pt), caption: {_q(caption)}, "
        'credit: "Photo: Full credit.")\n',
        "layout-full",
    )
    lines = _lines(pdf)
    page_width = lines[0].page_width

    for line in _caption_group(lines, "Photograph 1.", caption):
        assert abs(line.centre - page_width / 2) <= 2.0
    assert abs(_line(lines, "Photo:").x_min - PAGE_MARGIN) <= 2.0


def test_template_renders_all_three_compositions_once() -> None:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "layout-composition",
        "metadata": {"title": "Layout composition", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-a",
                "title": "Compositions",
                "blocks": [
                    {
                        "id": "b-photo",
                        "type": "illustration",
                        "illustrationId": "photo-1",
                        "composition": {"preset": "side-left", "companion": "b-photo-text"},
                    },
                    {
                        "id": "b-photo-text",
                        "type": "paragraph",
                        "text": "SIDE-LEFT-COMPANION-MARKER sits beside the first photograph.",
                    },
                    {
                        "id": "b-hist",
                        "type": "illustration",
                        "illustrationId": "hist-1",
                        "composition": {"preset": "side-right", "companion": "b-hist-text"},
                    },
                    {
                        "id": "b-hist-text",
                        "type": "paragraph",
                        "text": "SIDE-RIGHT-COMPANION-MARKER sits beside the second photograph.",
                    },
                    {
                        "id": "b-art",
                        "type": "illustration",
                        "illustrationId": "art-1",
                        "composition": {"preset": "full"},
                    },
                ],
            }
        ],
    }
    work = ROOT / ".cache" / "layout-composition"
    work.mkdir(parents=True, exist_ok=True)
    manuscript = work / "manuscript.yaml"
    manuscript.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    result = typst_driver.build(manuscript, work / "out.pdf", work / "build", offline=True)
    text = subprocess.run(
        ["pdftotext", "-layout", str(result.pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    normalised = " ".join(text.split())

    assert normalised.count("SIDE-LEFT-COMPANION-MARKER") == 1
    assert normalised.count("SIDE-RIGHT-COMPANION-MARKER") == 1
    assert "Photograph 1." in normalised
    assert "Photograph 2." in normalised
    assert "Photograph 3." in normalised
    pages = [placement["page"] for placement in result.report["placements"]]
    entries = {entry["blockId"]: entry for entry in result.report["compositions"]}
    assert set(entries) == {"b-photo", "b-hist", "b-art"}
    assert entries["b-photo"]["preset"] == "side-left"
    assert entries["b-photo"]["companionId"] == "b-photo-text"
    assert entries["b-hist"]["preset"] == "side-right"
    assert entries["b-hist"]["companionId"] == "b-hist-text"
    assert entries["b-art"] == {
        "blockId": "b-art", "type": "illustration", "preset": "full", "companionId": None,
        "companionIds": [], "page": pages[2], "deferred": entries["b-art"]["deferred"],
    }
    assert len(set(pages)) == 3, f"one illustration per final page: {pages}"
    assert [entries[block]["page"] for block in ("b-photo", "b-hist", "b-art")] == pages
    assert all(isinstance(entry["deferred"], bool) for entry in entries.values())
    assert any(entry["deferred"] for entry in entries.values()), "the second illustration must be deferred"


def test_a_companion_renders_through_its_prose_preset_with_a_note() -> None:
    companion = (
        'companion-content((type: "definition", term: "Protocol", '
        'definition: "The agreed order of an encounter.", note: "NOTE-MARKER."))'
    )
    pdf = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#preset-illustration(\n"
        "  rect(width: 100%, height: 60pt, fill: black),\n"
        '  caption: "Photograph 1. Companion preset.",\n'
        '  credit: "Photo: Credit.",\n'
        '  composition: "side-left",\n'
        f"  companion: {companion},\n"
        ")\n",
        "layout-companion-preset",
    )
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    normalised = " ".join(text.split())

    assert "Protocol" in normalised
    assert "The agreed order of an encounter." in normalised
    assert "NOTE-MARKER." in normalised


# --- Production integration: A1 centred/side group, A2 columns, branches ---


def _build_with(name: str, sections: list[dict], metadata: dict | None = None):
    work = ROOT / ".cache" / "layout-integration" / name
    work.mkdir(parents=True, exist_ok=True)
    path = work / "manuscript.yaml"
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": name,
        "metadata": metadata or {"title": "Layout integration", "languages": ["en"]},
        "sections": sections,
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return typst_driver.build(path, work / f"{name}.pdf", work / "build", offline=True)


def _paragraph(block_id: str, text: str) -> dict:
    return {"id": block_id, "type": "paragraph", "text": text}


def test_centred_composition_places_the_visual_at_the_figure_width() -> None:
    result = _build_with(
        "centred",
        [
            {
                "id": "sec-a",
                "title": "A centred visual",
                "blocks": [
                    _paragraph("b-intro", "Body prose above a centred visual at the figure width."),
                    {
                        "id": "b-photo",
                        "type": "illustration",
                        "illustrationId": "photo-1",
                        "caption": "A centred photograph.",
                        "composition": {"preset": "centred"},
                    },
                ],
            }
        ],
    )

    boxes = report.figure_boxes(result.pdf)
    widths = [box[2] for page in boxes.values() for box in page]
    assert widths, "no placed figure box"
    assert min(abs(width - tokens.FIGURE_WIDTH_PT) for width in widths) <= tokens.PLATE_TOLERANCE_PT

    # A centred visual is not a plate at the full measure, and the report says
    # the width it really occupies.
    assert result.report["plates"] == []
    visuals = result.report["visuals"]
    assert len(visuals) == 1
    assert visuals[0]["preset"] == "centred"
    assert abs(visuals[0]["widthPt"] - tokens.FIGURE_WIDTH_PT) <= tokens.PLATE_TOLERANCE_PT
    assert visuals[0]["basis"] == "measured"


def test_side_composition_renders_a_multi_block_prose_group_once() -> None:
    result = _build_with(
        "side-group",
        [
            {
                "id": "sec-a",
                "title": "A side visual with a prose group",
                "blocks": [
                    {
                        "id": "b-photo",
                        "type": "illustration",
                        "illustrationId": "photo-1",
                        "caption": "A side photograph beside three prose blocks.",
                        "composition": {
                            "preset": "side-right",
                            "companions": ["b-p1", "b-def", "b-p2"],
                        },
                    },
                    _paragraph("b-p1", "SIDE-GROUP-FIRST sits in the prose column."),
                    {
                        "id": "b-def",
                        "type": "definition",
                        "term": "Companion",
                        "definition": "SIDE-GROUP-SECOND stays inline in the group.",
                    },
                    _paragraph("b-p2", "SIDE-GROUP-THIRD closes the group."),
                    _paragraph("b-after", "AFTER-GROUP prose follows the whole unit."),
                ],
            }
        ],
    )
    text = subprocess.run(
        ["pdftotext", "-layout", str(result.pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    normalised = " ".join(text.split())
    for marker in ("SIDE-GROUP-FIRST", "SIDE-GROUP-SECOND", "SIDE-GROUP-THIRD", "AFTER-GROUP"):
        assert normalised.count(marker) == 1, marker
    entry = next(item for item in result.report["compositions"] if item["blockId"] == "b-photo")
    assert entry["preset"] == "side-right"
    assert entry["companionIds"] == ["b-p1", "b-def", "b-p2"]
    assert "b-def" not in {block["id"] for block in result.report["compositions"] if block["blockId"] != "b-photo"}

    prose = captions.read_lines(result.pdf)
    first = next(line for line in prose if "SIDE-GROUP-FIRST" in line.text)
    caption = next(line for line in prose if line.text.startswith("Photograph 1."))
    assert first.x_min < caption.x_min, "side-right reads prose then the image column"


def test_two_column_chapter_flows_in_two_columns_and_keeps_headings_clear() -> None:
    long = (
        "A two-column chapter sets the heading and standfirst at the full measure and then "
        "flows the body in two equal columns, continuing across the page break without "
        "restarting the section. "
    )
    blocks = [
        _paragraph(f"b-body-{index}", f"COL-{index} " + long * 2)
        for index in range(1, 9)
    ]
    result = _build_with(
        "two-column",
        [
            {
                "id": "sec-a",
                "title": "Two columns",
                "level": 1,
                "layout": {"columns": 2},
                "standfirst": "The standfirst spans the full measure above both columns.",
                "blocks": blocks,
            },
            {
                "id": "sec-b",
                "title": "One column",
                "level": 1,
                "blocks": [_paragraph("b-single", "SINGLE-COLUMN stays at the full measure.")],
            },
        ],
    )

    lines = captions.read_lines(result.pdf)
    body = [line for line in lines if line.text.startswith("COL-")]
    assert body, "no column body text found"
    left = [line for line in body if line.x_min < PAGE_MARGIN + BODY / 2]
    right = [line for line in body if line.x_min >= PAGE_MARGIN + BODY / 2]
    assert left and right, "the chapter did not set in two columns"
    for line in body:
        assert line.x_max <= PAGE_MARGIN + BODY + 3.0
    mid = PAGE_MARGIN + BODY / 2
    gutter_low, gutter_high = mid - SIDE_GUTTER / 2, mid + SIDE_GUTTER / 2
    starts_in_gutter = [
        line for line in body if gutter_low + 0.5 < line.x_min < gutter_high - 0.5
    ]
    assert starts_in_gutter == [], [line.text for line in starts_in_gutter]
    crossing = [
        line for line in body
        if line.x_min < mid and line.x_max > gutter_high + 1.0 and line.x_max < PAGE_MARGIN + BODY - 1.0
    ]
    assert crossing == [], [line.text for line in crossing]

    single = next(line for line in lines if "SINGLE-COLUMN" in line.text)
    assert single.x_min <= PAGE_MARGIN + 1.0

    check = rhythm.check(result.pdf, model.load(Path(result.report["manuscript"]["path"]), root=ROOT))
    assert check.status in ("pass", "warn"), check.detail
    assert check.evidence["columnPages"], "the rhythm check did not detect the two-column page"
    assert any(item["clearancePt"] and item["clearancePt"] >= 15.30 for item in check.evidence["headingClearance"])


def test_branch_blocks_render_run_in_terminal_labels() -> None:
    result = _build_with(
        "branches",
        [
            {
                "id": "sec-a",
                "title": "Terminal branches",
                "blocks": [
                    _paragraph("b-intro", "Prose under the chapter heading."),
                    {"id": "b-br-a", "type": "branch", "text": "The first terminal branch."},
                    {"id": "b-br-b", "type": "branch", "text": "The second terminal branch."},
                ],
            }
        ],
    )
    text = subprocess.run(
        ["pdftotext", "-layout", str(result.pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    normalised = " ".join(text.split())
    assert "1 a) The first terminal branch." in normalised
    assert "1 b) The second terminal branch." in normalised

    branch = next(line for line in captions.read_lines(result.pdf) if "1 a)" in line.text)
    assert abs((branch.y_max - branch.y_min) / 1.5217 - 10.1) <= 0.5, "a branch label stays body size"


# --- A2: descendant flow, column-local visuals, authored column evidence ---

LONG_COLUMN = (
    "A measured paragraph of public-safe prose that fills a column and carries the "
    "reader onward. "
) * 2


def _two_column_sections() -> list[dict]:
    return [
        {
            "id": "sec-two-column",
            "title": "Two Columns",
            "level": 1,
            "layout": {"columns": 2},
            "standfirst": "The standfirst spans the full measure above both columns.",
            "blocks": [
                _paragraph("b-left-a", "LEFT. " + LONG_COLUMN * 3),
                _paragraph("b-left-b", "LEFT. " + LONG_COLUMN * 3),
                {
                    "id": "b-centred",
                    "type": "illustration",
                    "illustrationId": "hist-1",
                    "caption": "A centred photograph inside a column with a caption long enough to wrap in the column.",
                    "composition": {"preset": "centred"},
                },
            ],
        },
        {
            "id": "sec-section",
            "title": "A Section",
            "level": 2,
            "blocks": [_paragraph("b-section", "SECTION. " + LONG_COLUMN * 4)],
        },
        {
            "id": "sec-subsection",
            "title": "A Subsection",
            "level": 3,
            "blocks": [
                _paragraph("b-subsection", "SUB. " + LONG_COLUMN * 2),
                {"id": "b-branch", "type": "branch", "text": "A terminal branch inside a column."},
            ],
        },
        {
            "id": "sec-deep",
            "title": "Deeper",
            "level": 4,
            "blocks": [_paragraph("b-deep", "DEEP. " + LONG_COLUMN * 2)],
        },
    ]


def test_two_column_chapter_flows_descendant_sections_inside_the_columns() -> None:
    result = _build_with("a2-descendants", _two_column_sections(), {"title": "Descendants", "languages": ["en"], "institution": "Example Institute", "course": "Layout", "author": "Bookify"})
    lines = captions.read_lines(result.pdf)
    mid = PAGE_MARGIN + BODY / 2
    start_page = min(line.page for line in lines if line.text.startswith("Chapter 1:"))
    body_pages = {line.page for line in lines if line.page >= start_page}

    # The descendant headings and the branch are part of the column flow: each
    # starts at a column edge, not at a full-measure heading position.
    right_edge = PAGE_MARGIN + tokens.COLUMN_WIDTH_PT + SIDE_GUTTER
    for marker in ("1.1.1 A Subsection", "1.1.1.1 Deeper", "1.1.1 a) A terminal branch"):
        line = next(
            line for line in lines if marker in line.text and line.page in body_pages
        )
        assert min(abs(line.x_min - PAGE_MARGIN), abs(line.x_min - right_edge)) <= 2.0, (
            marker,
            line.x_min,
        )

    # No column line starts in the gutter.
    body = [
        line for line in lines
        if line.text.strip().startswith(("LEFT.", "SECTION.", "SUB.", "DEEP."))
    ]
    assert body, "no column prose found"
    for line in body:
        assert not (mid - SIDE_GUTTER / 2 + 0.5 < line.x_min < mid + SIDE_GUTTER / 2 - 0.5)

    check = captions.check(result.pdf, model.load(Path(result.report["manuscript"]["path"]), root=ROOT))
    assert check.status == "pass", check.detail
    rhythm_check = rhythm.check(result.pdf, model.load(Path(result.report["manuscript"]["path"]), root=ROOT))
    assert rhythm_check.status == "pass", rhythm_check.detail
    assert rhythm_check.evidence["columnPages"]


def test_centred_illustration_inside_a_column_takes_the_column_width() -> None:
    result = _build_with(
        "a2-centred",
        _two_column_sections(),
        {"title": "Descendants", "languages": ["en"]},
    )
    boxes = [box for page in report.figure_boxes(result.pdf).values() for box in page]
    assert boxes, "the photograph was not placed"
    assert min(box[2] for box in boxes) == pytest.approx(tokens.COLUMN_WIDTH_PT, abs=2.0)

    visuals = result.report["visuals"]
    assert len(visuals) == 1 and visuals[0]["preset"] == "centred"
    assert visuals[0]["widthPt"] == pytest.approx(tokens.COLUMN_WIDTH_PT, abs=2.0)
    assert visuals[0]["column"] is True
    assert result.report["plates"] == []


def test_diagram_inside_a_column_fits_the_column() -> None:
    sections = [
        {
            "id": "sec-two-column",
            "title": "Columns with a Diagram",
            "level": 1,
            "layout": {"columns": 2},
            "standfirst": "The standfirst spans the full measure above both columns.",
            "blocks": [
                _paragraph("b-before", "BEFORE. " + LONG_COLUMN * 3),
                {
                    "id": "b-diagram",
                    "type": "diagram",
                    "caption": "A synthetic diagram inside a two-column chapter with a caption long enough to wrap.",
                    "confidence": "inferred",
                    "note": "Illustrative diagram authored for this verification; not a reconstruction.",
                    "diagram": {
                        "preset": "process",
                        "nodes": [{"id": "n-a", "label": "Alpha"}, {"id": "n-b", "label": "Beta"}, {"id": "n-c", "label": "Gamma"}],
                        "edges": [{"from": "n-a", "to": "n-b"}, {"from": "n-b", "to": "n-c"}],
                    },
                },
                _paragraph("b-after", "AFTER. " + LONG_COLUMN * 3),
            ],
        }
    ]
    result = _build_with("a2-diagram", sections, {"title": "A Two-Column Book", "languages": ["en"]})
    lines = captions.read_lines(result.pdf)
    mid = PAGE_MARGIN + BODY / 2
    for marker in ("Alpha", "Beta", "Gamma"):
        line = next(line for line in lines if marker in line.text)
        assert line.x_max <= mid - SIDE_GUTTER / 2 + 3.0, (marker, line.x_min, line.x_max)

    check = captions.check(result.pdf, model.load(Path(result.report["manuscript"]["path"]), root=ROOT))
    assert check.status == "pass", check.detail
    assert result.report["plates"] == []
    assert result.report["visuals"] and result.report["visuals"][0]["column"] is True


def test_side_composition_is_refused_inside_a_two_column_chapter(tmp_path: Path) -> None:
    from bookify.errors import BookifyError
    from bookify.manuscript import model

    sections = [
        {
            "id": "sec-two-column",
            "title": "Two Columns",
            "level": 1,
            "layout": {"columns": 2},
            "blocks": [
                {
                    "id": "b-photo",
                    "type": "illustration",
                    "illustrationId": "photo-1",
                    "caption": "A side photograph.",
                    "composition": {"preset": "side-left", "companion": "b-text"},
                },
                {"id": "b-text", "type": "paragraph", "text": "Companion prose."},
            ],
        }
    ]
    path = tmp_path / "side-in-columns.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schemaVersion": "1.0",
                "revision": 1,
                "id": "side-in-columns",
                "metadata": {"title": "Side in columns", "languages": ["en"]},
                "sections": sections,
            },
            sort_keys=False,
        )
    )
    with pytest.raises(BookifyError) as error:
        model.load(path, root=ROOT)

    assert error.value.code == "SCHEMA_INVALID"
    assert "two-column" in str(error.value)


def test_rhythm_column_pages_come_from_the_authored_layout_not_a_guess() -> None:
    single = _build_with(
        "single-column-table",
        [
            {
                "id": "sec-a",
                "title": "One column",
                "level": 1,
                "blocks": [
                    _paragraph("b-a", "A single column of prose that no heuristic should call two columns. " * 6),
                    {
                        "id": "b-table",
                        "type": "table",
                        "caption": "A table with cells on the right side of the measure.",
                        "header": ["Left", "Middle", "Right"],
                        "rows": [["one", "two", "three"], ["four", "five", "six"]],
                    },
                    _paragraph("b-b", "More single-column prose under the table. " * 6),
                ],
            }
        ],
        {"title": "One Column", "languages": ["en"]},
    )
    single_check = rhythm.check(single.pdf, model.load(Path(single.report["manuscript"]["path"]), root=ROOT))
    assert single_check.evidence["columnPages"] == []

    two = _build_with("a2-evidence", _two_column_sections(), {"title": "Descendants", "languages": ["en"]})
    two_check = rhythm.check(two.pdf, model.load(Path(two.report["manuscript"]["path"]), root=ROOT))
    assert two_check.evidence["columnPages"], "the authored two-column page was not recorded"
    for page in two_check.evidence["columnPages"]:
        assert page in {line.page for line in captions.read_lines(two.pdf)}


def _workspace_book(tmp_path: Path, artwork_path: str, artwork_id: str = "art-1") -> Path:
    import shutil

    workspace = tmp_path / "workspace"
    (workspace / "assets" / "illustrations" / artwork_id).mkdir(parents=True, exist_ok=True)
    sha = ""
    (workspace / "assets" / "illustrations" / artwork_id / "record.yaml").write_text(
        "\n".join(
            [
                'schemaVersion: "1.0"',
                f"id: {artwork_id}",
                f"path: {artwork_path}",
                'originUrl: "local:fixture"',
                'creator: "Bookify fixture"',
                'licence: "Original work"',
                'credit: "Artwork: fixture."',
                'caption: "A fixture artwork."',
                'alt: "A fixture artwork."',
                "kind: conceptual_artwork",
                "rightsStatus: verified",
                sha,
            ]
        )
        + "\n"
    )
    return workspace


def test_workspace_build_stages_cover_artwork_outside_the_illustration_folder(tmp_path: Path) -> None:
    import shutil

    workspace = _workspace_book(
        tmp_path, "assets/catalogue/artwork/art-1.svg"
    )
    (workspace / "assets" / "catalogue" / "artwork").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        ROOT / "assets" / "catalogue" / "artwork" / "art-1.svg",
        workspace / "assets" / "catalogue" / "artwork" / "art-1.svg",
    )
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "workspace-art",
        "metadata": {
            "title": "Workspace Artwork",
            "languages": ["en"],
            "cover": {"composition": "cover-1", "artwork": "art-1"},
        },
        "sections": [
            {"id": "sec-a", "title": "Chapter", "blocks": [{"id": "b-a", "type": "paragraph", "text": "Text."}]}
        ],
    }
    path = workspace / "book.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False))

    result = typst_driver.build(path, workspace / "out.pdf", workspace / "build", offline=True, workspace=workspace)

    assert result.report["cover"]["artwork"] == "present"
    assert result.report["cover"]["composition"] == "cover-1"


def test_workspace_build_refuses_an_asset_that_escapes_the_book_root(tmp_path: Path) -> None:
    from bookify.errors import BookifyError

    workspace = _workspace_book(tmp_path, "../outside.svg")
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "workspace-escape",
        "metadata": {
            "title": "Workspace Escape",
            "languages": ["en"],
            "cover": {"composition": "cover-1", "artwork": "art-1"},
        },
        "sections": [
            {"id": "sec-a", "title": "Chapter", "blocks": [{"id": "b-a", "type": "paragraph", "text": "Text."}]}
        ],
    }
    path = workspace / "book.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    (tmp_path / "outside.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'/>")

    with pytest.raises(BookifyError) as error:
        typst_driver.build(path, workspace / "out.pdf", workspace / "build", offline=True, workspace=workspace)

    assert error.value.code == "BUILD_FAILED"
    assert "outside the book root" in error.value.message


def test_geometry_canvas_follows_the_authored_column() -> None:
    from bookify.verify.checks import captions as captions_check
    from bookify.verify.checks import geometry

    line = captions_check.LineBox(
        page=5,
        page_width=595.2756,
        text="Figure 1. A column caption.",
        x_min=305.64,
        x_max=500.0,
        y_min=100.0,
        y_max=111.2,
    )
    spec = captions_check.CaptionSpec(
        block_id="b-chart",
        kind="chart",
        label="Figure 1",
        text="A column caption.",
        preset="full",
        columns=2,
    )
    measurement = captions_check.CaptionMeasurement(
        block_id="b-chart",
        kind="chart",
        label="Figure 1",
        page=5,
        lines=(line,),
        preset="full",
        target_centre_pt=0.0,
    )
    canvas = geometry._canvas(spec, 595.2756, measurement)

    assert canvas.column is True
    assert canvas.left == pytest.approx(PAGE_MARGIN + tokens.COLUMN_WIDTH_PT + SIDE_GUTTER, abs=0.1)
    assert canvas.width == pytest.approx(tokens.COLUMN_WIDTH_PT, abs=0.1)
    assert canvas.centre == pytest.approx(canvas.left + tokens.COLUMN_WIDTH_PT / 2, abs=0.1)


def test_a_right_column_descendant_figure_is_recorded_in_its_column() -> None:
    """A label that shares a baseline with the left column is still a label.

    `pdftotext -layout` merges the neighbouring column's prose with a
    right-column caption, so the report must read the per-line text boxes; an
    unreported column figure would silently lose its placement evidence.
    """
    sections = [
        {
            "id": "sec-two-column",
            "title": "Two Columns",
            "level": 1,
            "layout": {"columns": 2},
            "standfirst": "The standfirst spans the full measure.",
            "blocks": [
                _paragraph(f"b-fill-{index}", "PARA. " + LONG_COLUMN * 8)
                for index in range(1, 17)
            ],
        },
        {
            "id": "sec-figure",
            "title": "A Figure Section",
            "level": 2,
            "blocks": [
                _paragraph("b-pre", "PRE. " + LONG_COLUMN * 10),
                {
                    "id": "b-chart",
                    "type": "chart",
                    "caption": "A chart in the right column of a two-column chapter, with a caption long enough to wrap.",
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
            ],
        },
    ]
    result = _build_with("a2-right-column", sections, {"title": "Right Column", "languages": ["en"]})

    assert result.report["numbered"].get("Figure 1")
    visuals = result.report["visuals"]
    assert len(visuals) == 1
    assert visuals[0]["column"] is True
    assert visuals[0]["widthPt"] == pytest.approx(tokens.COLUMN_WIDTH_PT, abs=2.0)
    assert visuals[0]["leftPt"] >= PAGE_MARGIN + BODY / 2
    assert result.report["plates"] == []
