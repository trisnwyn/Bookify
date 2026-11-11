"""Task 47: token-driven full, side-left and side-right illustration composition."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

from helpers import ROOT, compile_typ
from bookify.design import lint, tokens
from bookify.publish import typst_driver
from bookify.verify.checks import captions

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
        "blockId": "b-art", "preset": "full", "companionId": None,
        "page": pages[2], "deferred": entries["b-art"]["deferred"],
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
