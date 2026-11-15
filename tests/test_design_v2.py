"""Bookify v2 design defaults D1-D7, measured from rendered PDFs.

Fixtures are synthetic and public-safe. Every measurement comes from the actual
PDF through `pdftotext -bbox-layout` and `pdftoppm`; no tolerance is widened to
hide a defect. Snippet compiles use the same theme and presets the books use.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from helpers import ROOT, compile_typ
from bookify.design import lint, tokens

THEME = ROOT / "typst" / "theme.typ"
BLOCKS = ROOT / "typst" / "blocks.typ"
TEMPLATE = ROOT / "typst" / "templates" / "book.typ"


def _theme_text() -> str:
    return THEME.read_text()


def _token(text: str, name: str, value: float) -> bool:
    matches = re.findall(rf"\b{re.escape(name)}:\s*([0-9.]+)pt", text)
    assert matches, f"theme is missing a numeric token {name!r}"
    return any(abs(float(match) - value) < 1e-9 for match in matches)


# --- D6: spacing tokens -----------------------------------------------------


def test_heading_spacing_tokens_sit_above_the_paragraph_gap() -> None:
    theme = _theme_text()
    paragraph_gap = 20.70

    assert _token(theme, "before_h2", 32.0)
    assert _token(theme, "before_h3", 25.0)
    assert _token(theme, "before_heading", 17.0)
    assert 32.0 > 25.0 > paragraph_gap > 17.0


def test_v2_cover_and_opener_tokens_exist() -> None:
    theme = _theme_text()

    assert _token(theme, "cover_title", 34.0)
    assert _token(theme, "cover_subtitle", 12.6)
    assert _token(theme, "cover_meta", 8.4)
    assert _token(theme, "cover_index", 8.6)
    assert _token(theme, "opener_numeral", 40.0)
    assert _token(theme, "opener_rule", 12.0)
    assert _token(theme, "opener_title", 14.0)
    assert _token(theme, "cover_rule", 12.0)
    assert _token(theme, "cover_footer", 24.0)
    assert _token(theme, "plate", tokens.BODY_MEASURE_PT)
    assert _token(theme, "cover", 0.6)
    assert _token(theme, "opener", 0.6)


def test_v2_token_leaves_are_named_for_the_linter() -> None:
    for name in (
        "cover_title",
        "cover_subtitle",
        "cover_meta",
        "cover_index",
        "opener_numeral",
        "before_h2",
        "before_h3",
        "opener_rule",
        "opener_title",
        "cover_rule",
        "cover_footer",
        "plate",
        "cover",
        "opener",
    ):
        assert name in tokens.LEAF_NAMES, name


def test_blocks_and_templates_stay_literal_free() -> None:
    assert lint.lint(ROOT) == []


# --- rendered measurement helpers ------------------------------------------

LATIN = (
    "Alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
    "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu "
) * 2


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _lines(pdf: Path):
    from bookify.verify.checks import captions

    return captions.read_lines(pdf)


def _page_lines(pdf: Path, page: int = 1):
    return [line for line in _lines(pdf) if line.page == page and not line.text.strip().isdigit()]


def _bands(pdf: Path, page: int, y_from: float, y_to: float) -> list[tuple[float, float]]:
    """Merge inked rows between two point positions, in points."""
    work = ROOT / ".cache" / "design-v2-ink"
    work.mkdir(parents=True, exist_ok=True)
    stem = work / f"{pdf.stem}-p{page}"
    subprocess.run(
        ["pdftoppm", "-f", str(page), "-l", str(page), "-png", "-r", "300", "-singlefile", str(pdf), str(stem)],
        check=True,
        capture_output=True,
    )
    image = Image.open(f"{stem}.png").convert("L")
    pixels = image.load()
    scale = 300 / 72
    x0, x1 = int(58 * scale), int(538 * scale)
    rows = [
        y
        for y in range(max(0, int(y_from * scale)), min(image.height, int(y_to * scale)))
        if any(pixels[x, y] < 250 for x in range(x0, x1))
    ]
    assert rows, f"no ink between {y_from} and {y_to} pt on page {page}"
    bands: list[tuple[float, float]] = []
    start = previous = rows[0]
    for row in rows[1:]:
        if row - previous > 1:
            bands.append((start / scale, previous / scale))
            start = row
        previous = row
    bands.append((start / scale, previous / scale))
    return bands


def _heading_gap(pdf: Path, page: int, heading_marker: str) -> tuple[float, float]:
    """Baseline delta from the previous body line and the white band above it."""
    lines = sorted(_page_lines(pdf, page), key=lambda line: line.y_min)
    index = next(i for i, line in enumerate(lines) if heading_marker in line.text)
    assert index > 0, f"{heading_marker} is the first line on the page; no previous body line"
    delta = lines[index].y_min - lines[index - 1].y_min
    bands = _bands(pdf, page, lines[index - 1].y_min - 1, lines[index].y_min + 6)
    assert len(bands) >= 2, "heading ink touches the previous line; no white band"
    return delta, bands[1][0] - bands[0][1]


def test_h2_and_h3_open_a_measured_white_band_above_the_paragraph_gap() -> None:
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f"#preset-paragraph({_q('BODY-MARKER ' + LATIN)})\n"
        f"#preset-paragraph({_q('SECOND-MARKER ' + LATIN)})\n"
        "#heading(level: 2)[H2-MARKER Minor section]\n"
        f"#preset-paragraph({_q('AFTER-H2 ' + LATIN)})\n"
        "#pagebreak()\n"
        f"#preset-paragraph({_q('BODY3-MARKER ' + LATIN)})\n"
        "#heading(level: 3)[H3-MARKER Subsection]\n"
        f"#preset-paragraph({_q('AFTER-H3 ' + LATIN)})\n"
    )
    pdf = compile_typ(source, "design-v2-heading-rhythm")

    h2_delta, h2_band = _heading_gap(pdf, 1, "H2-MARKER")
    h3_delta, h3_band = _heading_gap(pdf, 2, "H3-MARKER")

    assert h2_delta >= 36.0, f"h2 baseline delta {h2_delta}"
    assert h2_band >= 8.0, f"h2 white band {h2_band}"
    assert h3_delta >= 31.0, f"h3 baseline delta {h3_delta}"
    assert h3_band >= 5.0, f"h3 white band {h3_band}"
    assert h2_delta > h3_delta


def test_body_pitch_and_paragraph_gap_keep_their_measured_values() -> None:
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f"#preset-paragraph({_q('ONE-MARKER ' + LATIN)})\n"
        f"#preset-paragraph({_q('TWO-MARKER ' + LATIN)})\n"
    )
    pdf = compile_typ(source, "design-v2-body-rhythm")
    lines = sorted(_page_lines(pdf), key=lambda line: line.y_min)
    two = next(i for i, line in enumerate(lines) if line.text.startswith("TWO-MARKER"))
    body = [round(later.y_min - earlier.y_min, 2) for earlier, later in zip(lines[:two], lines[1:two])]
    body = [pitch for pitch in body if pitch > 1.0]
    assert body, "no body pitch sample"
    for pitch in body:
        assert abs(pitch - 15.30) <= 0.15, body
    gap = round(lines[two].y_min - lines[two - 1].y_min, 2)
    assert abs(gap - 20.70) <= 0.15, gap


# --- D1: definitions are inline -------------------------------------------


def test_definition_renders_as_one_body_paragraph_with_no_role_label() -> None:
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f"#preset-paragraph({_q('BEFORE-MARKER ' + LATIN)})\n"
        f"#preset-definition({_q('Protocol')}, {_q('The agreed order of an encounter, recorded before the reading begins, and kept with its context and limits so a later reader can see how the judgement was made.')})\n"
        "#heading(level: 2)[AFTER-HEADING]\n"
    )
    pdf = compile_typ(source, "design-v2-definition")
    lines = sorted(_page_lines(pdf), key=lambda line: line.y_min)

    definition = next(line for line in lines if line.text.startswith("Protocol:"))
    assert definition.text.startswith("Protocol: The agreed order")

    # No isolated grey term line: the term never appears alone at any size.
    alone = [line for line in lines if line.text.strip() == "Protocol"]
    assert alone == []

    # One body paragraph: the definition's first line pitch to its second line
    # is the body pitch, and the gap from the preceding paragraph is 20.70 pt.
    start = next(i for i, line in enumerate(lines) if line.text.startswith("Protocol:"))
    assert start + 1 < len(lines)
    assert abs(lines[start + 1].y_min - lines[start].y_min - 15.30) <= 0.15
    assert abs(lines[start].y_min - lines[start - 1].y_min - 20.70) <= 0.15


def test_definition_preset_never_renders_a_role_label() -> None:
    blocks = BLOCKS.read_text()
    body = blocks.split("#let preset-definition(", 1)[1].split("\n#let ", 1)[0]

    assert "role-label" not in body
    assert "[*#term*:" in body
    assert "between_paragraphs" in body


def test_a_glossary_table_remains_an_authored_table() -> None:
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        '#preset-table(([Term], [Definition]), (([Protocol], [The agreed order of an encounter.]),), caption: "GLOSSARY-CAPTION")\n'
    )
    pdf = compile_typ(source, "design-v2-glossary")
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    assert "GLOSSARY-CAPTION" in text and "Protocol" in text


def test_existing_definition_blocks_keep_their_fields_and_render_inline(tmp_path) -> None:
    import yaml

    from bookify.manuscript import model
    from bookify.publish import normalize

    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "design-v2-definition-block",
        "metadata": {"title": "Definition compatibility", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-a",
                "title": "Definitions",
                "blocks": [
                    {
                        "id": "b-def",
                        "type": "definition",
                        "term": "Sample",
                        "definition": "A bounded piece of material selected for inspection.",
                    }
                ],
            }
        ],
    }
    path = tmp_path / "manuscript.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    manuscript = model.load(path, root=ROOT)
    entry = normalize.build(manuscript, {}).data["sections"][0]["blocks"][0]

    assert entry["term"] == "Sample"
    assert entry["definition"] == "A bounded piece of material selected for inspection."


# --- D3: numbering ---------------------------------------------------------


def _write_manuscript(tmp_path: Path, name: str, sections: list[dict], metadata: dict | None = None) -> Path:
    import yaml

    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": name,
        "metadata": metadata or {"title": name.replace("-", " ").title(), "languages": ["en"]},
        "sections": sections,
    }
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return path


def _small(block_id: str, text: str = "A short synthetic paragraph for the numbering fixture.") -> dict:
    return {"id": block_id, "type": "paragraph", "text": text}


NUMBERING_SECTIONS = [
    {
        "id": "sec-one",
        "title": "First chapter",
        "level": 1,
        "blocks": [
            _small(
                "b-one",
                "The first chapter references {ref:b-two} and {ref:b-appendix-values}.",
            )
        ],
    },
    {
        "id": "sec-one-one",
        "title": "First subsection",
        "level": 2,
        "blocks": [_small("b-two", "A subsection with a reference to {ref:b-deep}.")],
    },
    {
        "id": "sec-one-one-one",
        "title": "Deep detail",
        "level": 3,
        "blocks": [_small("b-deep", "A level-three paragraph.")],
    },
    {
        "id": "sec-two",
        "title": "Second chapter",
        "level": 1,
        "blocks": [_small("b-second", "A second chapter.")],
    },
    {
        "id": "sec-appendix",
        "title": "Data tables",
        "level": 1,
        "role": "appendix",
        "blocks": [_small("b-appendix-note", "Back matter follows the chapters.")],
    },
    {
        "id": "sec-appendix-one",
        "title": "Source values",
        "level": 2,
        "blocks": [_small("b-appendix-values", "The appendix subsection.")],
    },
]


def test_section_numbers_follow_chapters_and_appendices(tmp_path: Path) -> None:
    from bookify.manuscript import model
    from bookify.publish import normalize

    path = _write_manuscript(tmp_path, "numbering", NUMBERING_SECTIONS)
    manuscript = model.load(path, root=ROOT)

    numbers = normalize.section_numbers(manuscript)

    assert [item["printed"] for item in numbers] == [
        "1",
        "1.1",
        "1.1.1",
        "2",
        "Appendix A",
        "A.1",
    ]
    assert [item["number"] for item in numbers] == ["1", "1.1", "1.1.1", "2", "A", "A.1"]

    document = normalize.build(manuscript, {}).data
    assert document["numbering"] == {"chapters": 2, "appendices": 1, "levels": 3}
    assert [entry["number"] for entry in document["cover"]["index"]] == ["1", "2", "Appendix A"]
    assert document["cover"]["indexMode"] == "list"
    body = document["sections"][0]["blocks"][0]["text"]
    assert "§1.1" in body and "§A.1" in body


def test_cover_index_switches_to_the_ledger_motif_beyond_twelve_chapters(tmp_path: Path) -> None:
    from bookify.manuscript import model
    from bookify.publish import normalize

    sections = [
        {"id": f"sec-{index}", "title": f"Chapter {index}", "level": 1, "blocks": [_small(f"b-{index}")]}
        for index in range(1, 14)
    ]
    path = _write_manuscript(tmp_path, "ledger-cover", sections)
    document = normalize.build(model.load(path, root=ROOT), {}).data

    assert len(document["cover"]["index"]) == 13
    assert document["cover"]["indexMode"] == "ledger"


@pytest.mark.parametrize(
    "sections, locator",
    [
        (
            [
                {"id": "sec-a", "title": "Back first", "role": "appendix", "blocks": [_small("b-a")]},
            ],
            "sections[0].role",
        ),
        (
            [
                {"id": "sec-a", "title": "Chapter", "blocks": [_small("b-a")]},
                {"id": "sec-b", "title": "Appendix", "role": "appendix", "blocks": [_small("b-b")]},
                {"id": "sec-c", "title": "Chapter again", "blocks": [_small("b-c")]},
            ],
            "sections[2].role",
        ),
        (
            [
                {"id": "sec-a", "title": "Chapter", "blocks": [_small("b-a")]},
                {"id": "sec-b", "title": "Sub", "level": 2, "role": "appendix", "blocks": [_small("b-b")]},
            ],
            "sections[1].role",
        ),
    ],
)
def test_invalid_back_matter_is_refused_with_a_locator(tmp_path: Path, sections: list[dict], locator: str) -> None:
    from bookify.errors import BookifyError
    from bookify.manuscript import model

    path = _write_manuscript(tmp_path, "bad-matter", sections)
    with pytest.raises(BookifyError) as error:
        model.load(path, root=ROOT)

    assert error.value.code == "SCHEMA_INVALID"
    assert error.value.locator == locator


def test_numbered_book_renders_numbers_in_contents_and_headings(tmp_path: Path) -> None:
    from bookify.publish import typst_driver
    from bookify.publish import report as report_mod
    from bookify.verify.checks import xrefs as xrefs_check
    from bookify.manuscript import model

    work = ROOT / ".cache" / "design-v2-numbering"
    work.mkdir(parents=True, exist_ok=True)
    path = _write_manuscript(work, "numbered-book", NUMBERING_SECTIONS)
    result = typst_driver.build(path, work / "numbered.pdf", work / "build", offline=True)

    text = subprocess.run(["pdftotext", "-layout", str(result.pdf), "-"], capture_output=True, text=True, check=True).stdout
    contents = report_mod.contents_pages(text.split("\f")[:])
    assert contents, "contents page not found"
    contents_text = "\n".join(text.split("\f")[index - 1] for index in contents)
    for expected in ("1", "1.1", "1.1.1", "2", "Appendix A", "A.1"):
        assert expected in contents_text, f"contents is missing the number {expected}"
    assert "Contents" in contents_text

    body = text.split("\f")
    assert any("Appendix A Data tables" in page for page in body)
    assert any("A.1 Source values" in page for page in body)
    assert any("§1.1" in page and "§A.1" in page for page in body)

    manuscript = model.load(path, root=ROOT)
    check = xrefs_check.check(result.pdf, manuscript)
    assert check.status == "pass", check.detail


# --- D2: designed typographic cover ---------------------------------------


def _build_book(name: str, sections: list[dict], metadata: dict | None = None):
    from bookify.publish import typst_driver

    work = ROOT / ".cache" / "design-v2-cover" / name
    work.mkdir(parents=True, exist_ok=True)
    path = _write_manuscript(work, name, sections, metadata=metadata)
    return typst_driver.build(path, work / f"{name}.pdf", work / "build", offline=True)


SPECIMEN_METADATA = {
    "title": "Reading a Sample",
    "subtitle": "A synthetic specimen for the offline publishing pipeline",
    "languages": ["en"],
    "institution": "Example Institute",
    "course": "Specimen Methods",
    "author": "Bookify specimen",
}


TWO_CHAPTERS = [
    {"id": "sec-one", "title": "First chapter", "level": 1, "blocks": [_small("b-one")]},
    {"id": "sec-two", "title": "Second chapter", "level": 1, "blocks": [_small("b-two")]},
]


def test_cover_renders_the_house_typographic_defaults() -> None:
    from bookify.design import tokens as design_tokens
    from bookify.manuscript import model
    from bookify.verify.checks import cover as cover_check

    result = _build_book("cover-default", TWO_CHAPTERS, SPECIMEN_METADATA)
    manuscript = model.load(Path(result.report["manuscript"]["path"]), root=ROOT)
    check = cover_check.check(result.pdf, manuscript)

    assert check.status == "pass", check.detail
    assert check.evidence["titleSizePt"] == pytest.approx(34.0, abs=1.0)
    assert check.evidence["titleLines"] <= design_tokens.COVER_TITLE_MAX_LINES
    assert check.evidence["chromaticPixels"] == 0
    assert check.evidence["images"] == 0
    assert check.evidence["indexMode"] == "list"
    assert check.evidence["entries"] == 2
    assert len(check.evidence["rules"]) >= 2
    assert result.report["cover"]["folio"] is False
    assert result.report["cover"]["coverIndex"] == "listed"

    text = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "1", str(result.pdf), "-"], capture_output=True, text=True, check=True).stdout
    for expected in ("Example Institute", "Reading a Sample", "Bookify specimen", "Specimen Methods", "First chapter", "Second chapter"):
        assert expected in " ".join(text.split()), expected
    # The institution appears once; the footer never repeats it.
    assert " ".join(text.split()).count("Example Institute") == 1
    # The cover carries no folio of its own.
    assert not any(line.strip().isdigit() for line in text.splitlines()[-3:])


def test_cover_index_beyond_twelve_chapters_uses_the_ledger_motif() -> None:
    from bookify.manuscript import model
    from bookify.verify.checks import cover as cover_check

    sections = [
        {"id": f"sec-{index}", "title": f"Chapter {index}", "level": 1, "blocks": [_small(f"b-{index}")]}
        for index in range(1, 14)
    ]
    result = _build_book("cover-ledger", sections, {"title": "Ledger Cover", "languages": ["en"]})

    assert result.report["cover"]["indexMode"] == "ledger"
    assert result.report["cover"]["coverIndex"] == "omitted"
    assert result.report["cover"]["entries"] == 13

    page = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "1", str(result.pdf), "-"], capture_output=True, text=True, check=True).stdout
    assert "Chapter 1" not in page and "Chapter 13" not in page
    manuscript = model.load(Path(result.report["manuscript"]["path"]), root=ROOT)
    check = cover_check.check(result.pdf, manuscript)
    assert check.status == "pass", check.detail
    assert check.evidence["ledger"] is True


def test_cover_title_overflow_fails_with_the_metadata_locator() -> None:
    from bookify.errors import BookifyError

    long_title = " ".join(["A deliberately overlong cover title that must be fixed in the metadata rather than shrunk by the template"] * 3)
    with pytest.raises(BookifyError) as error:
        _build_book("cover-overflow", TWO_CHAPTERS, {"title": long_title, "languages": ["en"]})

    assert error.value.code == "BUILD_FAILED"
    assert error.value.locator == "metadata.title"


def test_absent_cover_metadata_is_omitted_cleanly() -> None:
    result = _build_book("cover-minimal", TWO_CHAPTERS, {"title": "Minimal Cover", "languages": ["en"]})

    page = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "1", str(result.pdf), "-"], capture_output=True, text=True, check=True).stdout
    normalised = " ".join(page.split())
    assert "Minimal Cover" in normalised
    assert "First chapter" in normalised
    for absent in ("None", "none", "Example Institute", "Specimen Methods"):
        assert absent not in normalised
    assert result.report["cover"]["folio"] is False


# --- D4: openers and plates ------------------------------------------------


def test_chapter_opener_prints_numeral_rule_and_title() -> None:
    from bookify.verify.checks import cover as cover_check
    from bookify.verify.checks import plates as plates_check
    from bookify.manuscript import model

    result = _build_book("opener", TWO_CHAPTERS, SPECIMEN_METADATA)
    manuscript = model.load(Path(result.report["manuscript"]["path"]), root=ROOT)
    first = next(section for section in result.report["sections"] if section["printed"] == "1")
    assert first["page"] == 3

    lines = [line for line in _lines(result.pdf) if line.page == first["page"]]
    numeral = next(line for line in lines if line.text.strip() == "1")
    size = (numeral.y_max - numeral.y_min) / cover_check.LINE_BOX_EM
    assert size == pytest.approx(40.0, abs=1.0)

    # Poppler groups the opener title into one line ("First chapter") or, for a
    # tighter following gap, two word-lines; both are the same 25 pt title row.
    title = next(line for line in lines if line.text.strip().startswith("First"))
    title_size = (title.y_max - title.y_min) / cover_check.LINE_BOX_EM
    assert title_size == pytest.approx(25.0, abs=1.0)

    image = cover_check.raster(result.pdf, first["page"], 300)
    dark = (image.mean(axis=2) < cover_check.RULE_DARK).sum(axis=1)
    measure_px = int(475.28 * 300 / 72)
    band = range(int(numeral.y_max * 300 / 72), int(title.y_min * 300 / 72))
    assert any(dark[row] >= measure_px * cover_check.RULE_MIN_FRACTION for row in band), "no opener rule"

    check = plates_check.check(result.pdf, manuscript)
    assert check.status == "pass", check.detail


def test_visuals_are_placed_at_the_plate_measure() -> None:
    template = TEMPLATE.read_text()

    assert 'image(block.path, width: 100%)' in template
    assert "tokens.measure.plate" in template
    assert "88%" not in template and "72%" not in template

    from bookify.manuscript import model
    from bookify.verify.checks import plates as plates_check

    result = _build_book("plate-measure", TWO_CHAPTERS + [
        {
            "id": "sec-visual",
            "title": "A visual chapter",
            "level": 1,
            "blocks": [
                {
                    "id": "b-photo",
                    "type": "illustration",
                    "illustrationId": "photo-1",
                    "caption": "A plate at the full text measure.",
                }
            ],
        }
    ], SPECIMEN_METADATA)
    manuscript = model.load(Path(result.report["manuscript"]["path"]), root=ROOT)
    check = plates_check.check(result.pdf, manuscript)

    assert check.status == "pass", check.detail
    for plate in check.evidence["plates"]:
        assert abs(plate["widthPt"] - 475.28) <= 1.0, plate
    assert any(plate["basis"] == "measured" for plate in check.evidence["plates"])
    assert any(plate["basis"] == "declared" for plate in check.evidence["plates"]) is False


def test_a_chapter_with_only_a_side_visual_warns_for_a_missing_plate() -> None:
    from bookify.manuscript import model
    from bookify.verify.checks import plates as plates_check

    result = _build_book("plate-gap", [
        {
            "id": "sec-side",
            "title": "A side visual",
            "level": 1,
            "blocks": [
                {
                    "id": "b-photo",
                    "type": "illustration",
                    "illustrationId": "photo-1",
                    "caption": "A side photograph.",
                    "composition": {"preset": "side-left", "companion": "b-text"},
                },
                {"id": "b-text", "type": "paragraph", "text": "Companion prose beside the plate."},
            ],
        }
    ], SPECIMEN_METADATA)
    manuscript = model.load(Path(result.report["manuscript"]["path"]), root=ROOT)
    check = plates_check.check(result.pdf, manuscript)

    assert check.status == "warn", check.detail
    assert check.evidence["gaps"][0]["chapter"] == "1"
    assert check.evidence["gaps"][0]["reason"] is None


# --- D5: one centred caption carrying description and provenance -----------


def test_provenance_joins_the_centred_caption_while_the_credit_stays_left() -> None:
    from bookify.manuscript import model
    from bookify.verify.checks import captions as captions_check

    result = _build_book("captions", TWO_CHAPTERS + [
        {
            "id": "sec-figure",
            "title": "A figure chapter",
            "level": 1,
            "blocks": [
                {
                    "id": "b-photo",
                    "type": "illustration",
                    "illustrationId": "photo-1",
                    "caption": "A photograph whose description and provenance share one centred caption.",
                    "note": "Source: synthetic fixture; values are source-valued.",
                }
            ],
        }
    ], SPECIMEN_METADATA)
    manuscript = model.load(Path(result.report["manuscript"]["path"]), root=ROOT)
    check = captions_check.check(result.pdf, manuscript)
    assert check.status == "pass", check.detail
    assert result.report["captions"] == {"unified": 1, "separateNotes": 0}

    lines = captions_check.read_lines(result.pdf)
    provenance = next(line for line in lines if "Source: synthetic fixture" in line.text)
    caption = next(line for line in lines if line.text.startswith("Photograph 1."))
    credit = next(line for line in lines if line.text.startswith("Photo: William Ng"))
    assert abs(provenance.centre - provenance.page_width / 2) <= captions_check.TOLERANCE_PT
    assert abs(caption.centre - caption.page_width / 2) <= captions_check.TOLERANCE_PT
    assert abs(credit.centre - credit.page_width / 2) > 20
    assert abs((provenance.y_max - provenance.y_min) / 1.5217 - 8.2) <= 0.5
    assert abs((credit.y_max - credit.y_min) / 1.5217 - 7.6) <= 0.5
    # The retired 9.2 pt figure note is not rendered anywhere on the page.
    for line in lines:
        if line.page != credit.page:
            continue
        size = (line.y_max - line.y_min) / 1.5217
        assert not (abs(size - 9.2) <= 0.3 and "Source" in line.text), line.text


# --- D7: readability is measured, never a quota ----------------------------


def test_readability_metrics_are_reported_with_pages_and_exemptions() -> None:
    from bookify.manuscript import model
    from bookify.publish import readability
    from bookify.verify.checks import readability as readability_check

    pdf = ROOT / ".cache" / "v2-cover" / "specimen.pdf"
    manuscript = model.load(Path("content/specimen.yaml"))
    metrics = readability.measure_manuscript(pdf, manuscript)

    assert set(metrics) >= {
        "wordsPerPage", "tablesPerPage", "paragraphWords",
        "consecutiveDensePages", "exemptions", "warnings", "bands",
    }
    assert metrics["wordsPerPage"]["median"] > 0
    assert metrics["wordsPerPage"]["pages"]
    reasons = {entry["reason"] for entry in metrics["exemptions"]}
    assert {"cover", "contents", "chapter opener"} <= reasons
    for warning in metrics["warnings"]:
        assert warning["id"].startswith("readability:")
        assert "band" in warning and "pages" in warning

    check = readability_check.check(pdf, manuscript)
    assert check.status in {"pass", "warn"}
    assert check.ok is True, "a density warning is never a gate failure"

    # No target: the band is guidance and no minimum page or word count exists.
    assert "wordsPerPageMedian" in metrics["bands"]
    assert "pageQuota" not in metrics and "minimumWords" not in metrics


def test_a_wall_of_text_and_table_stack_warn_without_a_hard_failure() -> None:
    from bookify.manuscript import model
    from bookify.publish import readability
    from bookify.verify import runner

    wall = " ".join(["word"] * 300)
    tables = [
        {
            "id": f"b-table-{index}",
            "type": "table",
            "caption": f"Small table {index}.",
            "header": ["A", "B"],
            "rows": [["1", "2"]],
        }
        for index in range(3)
    ]
    result = _build_book("readability-warn", [
        {"id": "sec-a", "title": "A dense chapter", "level": 1, "blocks": [{"id": "b-wall", "type": "paragraph", "text": wall}] + tables},
    ], SPECIMEN_METADATA)
    manuscript = model.load(Path(result.report["manuscript"]["path"]), root=ROOT)
    metrics = readability.measure_manuscript(result.pdf, manuscript)
    ids = {warning["id"] for warning in metrics["warnings"]}

    assert "readability:paragraphWords:max" in ids
    assert any(identifier.startswith("readability:tablesPerPage:") for identifier in ids)

    work = ROOT / ".cache" / "design-v2-readability"
    work.mkdir(parents=True, exist_ok=True)
    notes = work / "notes.json"
    notes.write_text(json.dumps({identifier: "Reference page; deliberate." for identifier in ids}))
    report = runner.run(
        result.pdf, Path(result.report["manuscript"]["path"]), None,
        build_report=work / "missing-build.json",
        contact_sheet=ROOT / ".cache" / "verify-base" / "contact.png",
        reviewed_by="agent", reviewed_at="2026-11-14T00:00:00",
        review_notes=notes,
    )
    statuses = {check["id"]: check["status"] for check in report["checks"]}
    assert statuses["readability"] == "warn"
    assert report["warnings"], report["warnings"]
    assert any(warning["id"].startswith("readability:tablesPerPage:") for warning in report["warnings"])

    unanswered = runner.run(
        result.pdf, Path(result.report["manuscript"]["path"]), None,
        build_report=work / "missing-build.json",
        contact_sheet=ROOT / ".cache" / "verify-base" / "contact.png",
        reviewed_by="agent", reviewed_at="2026-11-14T00:00:00",
        review_notes=None,
    )
    review = next(check for check in unanswered["checks"] if check["id"] == "review")
    assert review["status"] == "fail"
    assert "not answered" in review["detail"]


# --- rendered verify checks for D1 and D6 ---------------------------------


def test_definitions_check_passes_inline_and_fails_a_role_label() -> None:
    from bookify.manuscript import model
    from bookify.publish import typst_driver
    from bookify.verify.checks import definitions as definitions_check

    work = ROOT / ".cache" / "design-v2-definitions"
    work.mkdir(parents=True, exist_ok=True)
    path = _write_manuscript(work, "definitions", [
        {
            "id": "sec-a",
            "title": "Definitions",
            "level": 1,
            "blocks": [
                {
                    "id": "b-def",
                    "type": "definition",
                    "term": "Protocol",
                    "definition": "The agreed order of an encounter, recorded with its context.",
                }
            ],
        }
    ])
    result = typst_driver.build(path, work / "book.pdf", work / "build", offline=True)
    manuscript = model.load(path, root=ROOT)
    assert definitions_check.check(result.pdf, manuscript).status == "pass"

    bad = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        '#role-label("definition", "Protocol")\n'
        '#preset-paragraph("The agreed order of an encounter, recorded with its context.")\n',
        "design-v2-definition-label",
    )
    failed = definitions_check.check(bad, manuscript)
    assert failed.status == "fail"
    assert any("inline" in problem or "isolated" in problem for problem in failed.evidence["problems"])


def test_rhythm_check_measures_headings_and_body_and_fails_a_collapsed_gap() -> None:
    from bookify.manuscript import model
    from bookify.publish import typst_driver
    from bookify.verify.checks import rhythm as rhythm_check

    work = ROOT / ".cache" / "design-v2-rhythm"
    work.mkdir(parents=True, exist_ok=True)
    path = _write_manuscript(work, "rhythm", [
        {
            "id": "sec-a",
            "title": "Rhythm chapter",
            "level": 1,
            "blocks": [_small("b-a", "A synthetic paragraph that fills enough of the measure to wrap onto a second line so the body pitch can be sampled from the rendered page.")],
        },
        {
            "id": "sec-b",
            "title": "Minor section",
            "level": 2,
            "blocks": [_small("b-b", "A synthetic paragraph that fills enough of the measure to wrap onto a second line so the body pitch can be sampled from the rendered page.")],
        },
        {
            "id": "sec-c",
            "title": "Subsection",
            "level": 3,
            "blocks": [_small("b-c", "A synthetic paragraph that fills enough of the measure to wrap onto a second line so the body pitch can be sampled.")],
        },
    ])
    result = typst_driver.build(path, work / "book.pdf", work / "build", offline=True)
    manuscript = model.load(path, root=ROOT)
    check = rhythm_check.check(result.pdf, manuscript)
    assert check.status == "pass", check.detail
    assert check.evidence["h2Samples"] == 1
    assert check.evidence["h3Samples"] == 1
    bands = {entry["level"]: entry for entry in check.evidence["headingBands"]}
    assert set(bands) == {2, 3}
    assert bands[2]["bandPt"] is not None and bands[2]["bandPt"] >= 8.0
    assert bands[3]["bandPt"] is not None and bands[3]["bandPt"] >= 5.0

    collapsed = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#show heading.where(level: 2): set block(above: 0pt, below: 4.5pt)\n"
        + f"#preset-paragraph({_q('BODY-MARKER ' + LATIN)})\n"
        + "#heading(level: 2)[Minor section]\n"
        + f"#preset-paragraph({_q('AFTER-MARKER ' + LATIN)})\n",
        "design-v2-rhythm-collapsed",
    )
    failed = rhythm_check.check(collapsed, manuscript)
    assert failed.status == "fail"
    assert any("h2 gap" in problem for problem in failed.evidence["problems"])


def test_rhythm_fails_when_a_heading_band_is_unmeasurable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D6: a heading with no measurable ink band is a failure, not a blank pass."""
    from bookify.manuscript import model
    from bookify.publish import typst_driver
    from bookify.verify.checks import rhythm as rhythm_check

    work = ROOT / ".cache" / "design-v2-rhythm-unmeasurable"
    work.mkdir(parents=True, exist_ok=True)
    path = _write_manuscript(work, "rhythm-unmeasurable", [
        {
            "id": "sec-a",
            "title": "Rhythm chapter",
            "level": 1,
            "blocks": [_small("b-a", "A synthetic paragraph that fills enough of the measure to wrap onto a second line so the body pitch can be sampled from the rendered page.")],
        },
        {
            "id": "sec-b",
            "title": "Minor section",
            "level": 2,
            "blocks": [_small("b-b", "A synthetic paragraph that fills enough of the measure to wrap onto a second line so the body pitch can be sampled from the rendered page.")],
        },
    ])
    result = typst_driver.build(path, work / "book.pdf", work / "build", offline=True)
    manuscript = model.load(path, root=ROOT)
    monkeypatch.setattr(rhythm_check, "_ink_band", lambda *_args, **_kwargs: None)
    check = rhythm_check.check(result.pdf, manuscript)

    assert check.status == "fail", check.detail
    assert any("unmeasurable" in problem for problem in check.evidence["problems"])
    assert check.evidence["h2Samples"] == 1
    assert [entry["bandPt"] for entry in check.evidence["headingBands"]] == [None]


def test_heading_clearance_below_every_level_is_derived_from_font_metrics() -> None:
    """The heading gap reserves descender ink, not just the layout line box."""
    theme = _theme_text()
    template = TEMPLATE.read_text()

    assert _token(theme, "heading_clearance", 0.5)
    for metric, value in (("line_box_em", 0.660), ("ascent_em", 0.750), ("descent_em", 0.240)):
        assert re.search(rf"\b{metric}:\s*{value}", theme), metric
    # The gap is computed from the metrics, not written as a bare point value.
    for level in ("h1", "h2", "h3"):
        assert f"below: heading-below(tokens.type.{level})" in theme, level
    assert "below: heading-below(tokens.type.h1)" in template
    assert "below: tokens.space.after_heading" not in theme
    assert "below: tokens.space.after_heading" not in template


def test_h1_keeps_clearance_below_and_the_old_below_gap_fails_the_check() -> None:
    """F1 page 4: a lead-less h1 must not strike its first body line."""
    from bookify.manuscript import model
    from bookify.publish import typst_driver
    from bookify.verify.checks import rhythm as rhythm_check

    work = ROOT / ".cache" / "design-v2-h1-clearance"
    work.mkdir(parents=True, exist_ok=True)
    path = _write_manuscript(work, "h1-clearance", [
        {
            "id": "sec-image",
            "title": "A page that is only an image",
            "level": 1,
            "blocks": [_small(
                "b-image",
                "The second page has no text layer at all. Adequate OCR makes it "
                "extracted-with-uncertainty: the page is not treated as verified, and "
                "the receipt total is checked by the table's own arithmetic.",
            )],
        },
        {
            "id": "sec-checked",
            "title": "How the reconstruction was checked",
            "level": 2,
            "blocks": [_small("b-checked", "Each region is read twice and the two reads are compared token by token.")],
        },
        {
            "id": "sec-cell",
            "title": "Reading a cell",
            "level": 3,
            "blocks": [_small("b-cell", "A cell is used only when its line reaches the eligible band.")],
        },
    ])
    result = typst_driver.build(path, work / "book.pdf", work / "build", offline=True)
    manuscript = model.load(path, root=ROOT)
    check = rhythm_check.check(result.pdf, manuscript)

    assert check.status == "pass", check.detail
    entries = {entry["section"]: entry for entry in check.evidence["headingClearance"]}
    assert set(entries) == {"A page that is only an image", "How the reconstruction was checked", "Reading a cell"}
    h1 = entries["A page that is only an image"]["clearancePt"]
    assert h1 is not None and h1 >= 0.4, f"h1 clearance {h1}"

    # The pre-fix gap (the plain after_heading below a 25 pt title) is a
    # rendered collision: the same check must fail it.
    collapsed = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#show heading.where(level: 1): set block(below: 4.5pt)\n"
        "#heading(level: 1)[A page that is only an image]\n"
        + f"#preset-paragraph({_q('The second page has no text layer at all. Adequate OCR makes it extracted-with-uncertainty: the page is not treated as verified.')})\n",
        "design-v2-h1-clearance-collapsed",
    )
    failed = rhythm_check.check(collapsed, manuscript)
    assert failed.status == "fail"
    assert any("touches the heading" in problem for problem in failed.evidence["problems"])
    assert [entry["clearancePt"] for entry in failed.evidence["headingClearance"]] == [None]


def test_xrefs_rejects_a_body_heading_that_lost_its_number(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from bookify.manuscript import model
    from bookify.verify.checks import xrefs as xrefs_check

    path = _write_manuscript(tmp_path, "lost-number", [
        {"id": "sec-one", "title": "First chapter", "level": 1, "blocks": [_small("b-one")]},
    ])
    manuscript = model.load(path, root=ROOT)
    texts = ["", "1 First chapter .... 3\n", "First chapter\n"]
    monkeypatch.setattr(xrefs_check, "page_texts", lambda _pdf: texts)
    monkeypatch.setattr(xrefs_check, "contents_pages", lambda _texts: {2})
    monkeypatch.setattr(
        xrefs_check,
        "grouped_page_lines",
        lambda _pdf, page: ["1 First chapter"] if page == 2 else ["First chapter"] if page == 3 else [],
    )
    monkeypatch.setattr(xrefs_check, "numbered_labels", lambda _texts: {})

    check = xrefs_check.check(path, manuscript)
    assert check.status == "fail"
    assert any("has no number" in problem for problem in check.evidence["problems"])


def test_rhythm_with_zero_samples_is_unmeasured_not_passed() -> None:
    from bookify.manuscript import model
    from bookify.publish import typst_driver
    from bookify.verify.checks import rhythm as rhythm_check

    work = ROOT / ".cache" / "design-v2-rhythm-zero"
    work.mkdir(parents=True, exist_ok=True)
    path = _write_manuscript(work, "rhythm-zero", TWO_CHAPTERS)
    result = typst_driver.build(path, work / "book.pdf", work / "build", offline=True)
    manuscript = model.load(path, root=ROOT)
    check = rhythm_check.check(result.pdf, manuscript)

    assert check.status == "warn", check.detail
    ids = {warning["id"] for warning in check.evidence["warnings"]}
    assert "rhythm:unmeasured:h2" in ids
    assert "rhythm:unmeasured:h3" in ids


def test_readability_median_warning_names_pages_and_exempts_the_whole_appendix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookify.publish import readability

    exempt = readability.exempt_pages(
        {
            "sections": [
                {"level": 1, "page": 3, "role": "chapter", "title": "One"},
                {"level": 1, "page": 5, "role": "appendix", "title": "Appendix A"},
            ]
        },
        {2},
        [],
        total_pages=8,
    )
    assert [page for page, reason in exempt.items() if reason == "appendix"] == [5, 6, 7, 8]

    texts = ["cover", "contents", "short page", "short page", "short page"]
    monkeypatch.setattr(readability, "page_texts", lambda _pdf: texts)
    monkeypatch.setattr(readability, "numbered_labels", lambda _texts: {})
    monkeypatch.setattr(readability.report, "contents_pages", lambda _texts: {2})
    monkeypatch.setattr(readability.report, "plate_entries", lambda *_args: ([], []))
    monkeypatch.setattr(readability.report, "grouped_page_lines", lambda _pdf, _page: [])
    metrics = readability.measure(Path("unused.pdf"), {"sections": []})
    median = next(
        warning for warning in metrics["warnings"] if warning["id"] == "readability:wordsPerPage:median"
    )
    assert median["pages"] == [3, 4, 5]


def test_plate_accounting_sees_a_visual_in_a_nested_section() -> None:
    from bookify.manuscript import model
    from bookify.verify.checks import plates as plates_check

    result = _build_book("plate-nested", [
        {
            "id": "sec-parent",
            "title": "A chapter whose plate is nested",
            "level": 1,
            "blocks": [_small("b-parent", "A short paragraph before the nested section.")],
        },
        {
            "id": "sec-child",
            "title": "The nested plate",
            "level": 2,
            "blocks": [
                {
                    "id": "b-nested-photo",
                    "type": "illustration",
                    "illustrationId": "photo-1",
                    "caption": "A full-measure photograph inside a level-2 section.",
                }
            ],
        },
    ], SPECIMEN_METADATA)
    manuscript = model.load(Path(result.report["manuscript"]["path"]), root=ROOT)
    check = plates_check.check(result.pdf, manuscript)

    assert check.status == "pass", check.detail
    assert check.evidence["gaps"] == []
    assert [plate["blockId"] for plate in check.evidence["plates"]] == ["b-nested-photo"]
    assert check.evidence["plates"][0]["chapter"] == "1"


def test_an_authored_no_plate_reason_is_recorded_and_passes() -> None:
    from bookify.manuscript import model
    from bookify.verify.checks import plates as plates_check

    reason = "The only visual is a side composition with its companion prose; no full-measure plate is claimed."
    result = _build_book("plate-declared", [
        {
            "id": "sec-side",
            "title": "A side visual",
            "level": 1,
            "noPlate": reason,
            "blocks": [
                {
                    "id": "b-photo",
                    "type": "illustration",
                    "illustrationId": "photo-1",
                    "caption": "A side photograph.",
                    "composition": {"preset": "side-left", "companion": "b-text"},
                },
                {"id": "b-text", "type": "paragraph", "text": "Companion prose beside the plate."},
            ],
        }
    ], SPECIMEN_METADATA)
    manuscript = model.load(Path(result.report["manuscript"]["path"]), root=ROOT)
    check = plates_check.check(result.pdf, manuscript)

    assert check.status == "pass", check.detail
    assert check.evidence["gaps"][0]["reason"] == reason
    assert check.evidence["gaps"][0]["basis"] == "declared"
    assert check.evidence["warnings"] == []
