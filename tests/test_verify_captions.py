"""Task 23: rendered figure descriptions are centred on every line."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml
from PIL import Image

from helpers import ROOT, SPECIMEN, compile_typ, specimen_build
from bookify.manuscript import model
from bookify.verify.checks import captions, pages


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _chart(block_id: str, caption: str, **extra) -> dict:
    block = {
        "id": block_id,
        "type": "chart",
        "caption": caption,
        "chart": {
            "kind": "grouped_bar",
            "categories": ["A"],
            "series": [{"id": "s", "label": "Series"}],
            "values": [[1]],
            "axis": {"unit": "index", "min": 0, "max": 2},
            "source": {"sourceId": "fixture", "page": 1},
            "verification": "verified",
        },
    }
    block.update(extra)
    return block


def _diagram(block_id: str, caption: str) -> dict:
    return {
        "id": block_id,
        "type": "diagram",
        "caption": caption,
        "diagram": {
            "preset": "process",
            "nodes": [{"id": "n-a", "label": "A"}, {"id": "n-b", "label": "B"}],
            "edges": [{"from": "n-a", "to": "n-b"}],
        },
    }


def _illustration(block_id: str, caption: str) -> dict:
    return {
        "id": block_id,
        "type": "illustration",
        "illustrationId": "photo-1",
        "caption": caption,
    }


def _manuscript(tmp_path: Path, blocks: list[dict], name: str = "captions") -> model.Manuscript:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": name,
        "metadata": {"title": "Caption fixture", "languages": ["en"]},
        "sections": [{"id": "sec-a", "title": "Captions", "blocks": blocks}],
    }
    target = tmp_path / f"{name}.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return model.load(target, root=ROOT)


def _six_caption_manuscript(tmp_path: Path) -> model.Manuscript:
    return _manuscript(
        tmp_path,
        [
            _chart("b-chart-short", "Short chart."),
            _chart(
                "b-chart-long",
                "A deliberately long chart description that must wrap onto at least two rendered lines "
                "so the centred alignment of every wrapped line is measured.",
            ),
            _diagram("b-diagram-short", "Short diagram."),
            _diagram(
                "b-diagram-long",
                "A deliberately long diagram description that must wrap onto at least two rendered lines "
                "so the centred alignment of every wrapped line is measured.",
            ),
            _illustration("b-photo-short", "Short photograph."),
            _illustration(
                "b-photo-long",
                "A deliberately long photograph description that must wrap onto at least two rendered lines "
                "so the centred alignment of every wrapped line is measured.",
            ),
        ],
    )


def _caption_pdf(tmp_path: Path, manuscript: model.Manuscript) -> Path:
    parts = [
        '#import "/typst/theme.typ": book_base',
        '#import "/typst/blocks.typ": *',
        '#set page(width: 300pt, height: 700pt, margin: 30pt)',
        "#show: book_base",
    ]
    for spec in captions.expected_captions(manuscript):
        if spec.kind == "chart":
            note = ', note: "Short note."' if spec.block_id == "b-chart-short" else ""
            parts.append(
                f"#preset-chart(rect(width: 120pt, height: 30pt, fill: black), caption: {_q(spec.text)}{note})"
            )
        elif spec.kind == "diagram":
            parts.append(
                f"#preset-diagram(rect(width: 120pt, height: 30pt, fill: black), caption: {_q(spec.text)})"
            )
        else:
            credit = ', credit: "Short credit."' if spec.block_id == "b-photo-short" else ""
            parts.append(
                f"#preset-illustration(rect(width: 120pt, height: 30pt, fill: black), caption: {_q(spec.text)}{credit})"
            )
        parts.append("#pagebreak()")
    return compile_typ("\n".join(parts), "caption-fixture")


def _line_with(lines, prefix: str):
    return next(line for line in lines if line.text.startswith(prefix))


GEOMETRY_SCALE = 150 / 72


def _ink_centre_above_caption(pdf: Path, line) -> float:
    """Raster ink centre of the figure band above one caption line, in points."""
    prefix = ROOT / ".cache" / "verify-snippets" / f"caption-geometry-{pdf.stem}-{line.page}"
    subprocess.run(
        [
            "pdftoppm", "-png", "-r", "150", "-f", str(line.page), "-l", str(line.page),
            "-singlefile", str(pdf), str(prefix),
        ],
        check=True,
    )
    image = Image.open(f"{prefix}.png").convert("L")
    width, height = image.size
    bottom = max(1, min(height, int(line.y_min * GEOMETRY_SCALE)))
    band = image.crop((0, 0, width, bottom))
    bbox = band.point(lambda value: 255 if value < 245 else 0).getbbox()
    assert bbox is not None, "the figure band above the caption contains no ink"
    x_min, _y_min, x_max, _y_max = bbox
    return (x_min + x_max) / 2 / GEOMETRY_SCALE


def test_figure_content_and_description_share_a_centre(tmp_path: Path) -> None:
    manuscript = _six_caption_manuscript(tmp_path)
    pdf = _caption_pdf(tmp_path, manuscript)
    lines = captions.read_lines(pdf)
    kinds: set[str] = set()

    for spec in captions.expected_captions(manuscript):
        line = _line_with(lines, f"{spec.label}.")
        figure_centre = _ink_centre_above_caption(pdf, line)
        assert abs(figure_centre - line.centre) <= captions.TOLERANCE_PT, (
            f"{spec.label}: figure centre {figure_centre:.2f} vs caption {line.centre:.2f}"
        )
        assert abs(figure_centre - line.page_width / 2) <= captions.TOLERANCE_PT
        kinds.add(spec.kind)

    assert kinds == {"chart", "diagram", "illustration"}


def test_left_positioned_figure_control_fails_the_geometry_rule(tmp_path: Path) -> None:
    line_text = "Figure 1. A left-positioned figure control."
    pdf = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        '#set page(width: 300pt, height: 300pt, margin: 30pt)\n'
        "#show: book_base\n"
        "#block(width: 100%)[#rect(width: 120pt, height: 30pt, fill: black)]\n"
        f"#preset-figure-caption({_q(line_text)})\n",
        "caption-figure-left-control",
    )
    line = _line_with(captions.read_lines(pdf), "Figure 1.")
    figure_centre = _ink_centre_above_caption(pdf, line)

    assert abs(figure_centre - line.centre) > captions.TOLERANCE_PT, (
        "a figure left at the margin must not satisfy the figure/caption geometry rule"
    )


def test_short_and_wrapped_captions_are_centred_for_every_group(tmp_path: Path) -> None:
    manuscript = _six_caption_manuscript(tmp_path)
    pdf = _caption_pdf(tmp_path, manuscript)

    result = captions.check(pdf, manuscript, require_coverage=True)

    assert result.status == "pass", result.detail
    assert result.evidence["groups"] == {
        "chart": {"single": 1, "wrapped": 1},
        "diagram": {"single": 1, "wrapped": 1},
        "illustration": {"single": 1, "wrapped": 1},
    }
    assert result.evidence["maxDeltaPt"] <= captions.TOLERANCE_PT


def test_left_aligned_caption_control_fails(tmp_path: Path) -> None:
    manuscript = _manuscript(
        tmp_path,
        [
            _chart(
                "b-chart-left",
                "A left-aligned control caption that is deliberately long enough to wrap onto more than one line.",
            )
        ],
    )
    expected = captions.expected_captions(manuscript)[0].text
    pdf = compile_typ(
        '#set page(width: 300pt, height: 300pt, margin: 30pt)\n'
        f"#align(left)[{expected}]\n",
        "caption-left-control",
    )

    result = captions.check(pdf, manuscript)

    assert result.status == "fail"
    assert result.code == "VERIFY_FAILED"
    assert "off centre" in result.detail


def test_caption_that_cannot_be_isolated_fails_loudly(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path, [_chart("b-chart-mismatch", "Expected caption text.")])
    expected = captions.expected_captions(manuscript)[0].text
    wrong = expected.replace("Expected caption text.", "Totally different caption text.")
    pdf = compile_typ(
        '#set page(width: 300pt, height: 300pt, margin: 30pt)\n'
        f"#align(center)[{wrong}]\n",
        "caption-unmatched",
    )

    result = captions.check(pdf, manuscript)

    assert result.status == "fail"
    assert result.code == "VERIFY_FAILED"
    assert "could not be isolated" in result.detail


def test_table_and_equation_captions_are_ignored_and_stay_left(tmp_path: Path) -> None:
    manuscript = _manuscript(
        tmp_path,
        [
            {
                "id": "b-table",
                "type": "table",
                "caption": "A left-aligned table caption.",
                "header": ["A"],
                "rows": [["1"]],
            },
            {"id": "b-equation", "type": "equation", "typst": "x = 1", "caption": "Equation caption stays left."},
            _chart("b-chart-centered", "Centred chart."),
        ],
    )
    table_caption = "Table 1. A left-aligned table caption."
    equation_caption = "Equation caption stays left."
    pdf = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        '#set page(width: 300pt, height: 500pt, margin: 30pt)\n'
        "#show: book_base\n"
        f'#preset-table(([A],), (([1],),), caption: {_q(table_caption)})\n'
        f"#preset-equation($x = 1$, caption: {_q(equation_caption)})\n"
        '#preset-chart(rect(width: 120pt, height: 30pt), caption: "Figure 1. Centred chart.")\n',
        "caption-table-equation",
    )

    result = captions.check(pdf, manuscript)

    assert result.status == "pass", result.detail
    lines = captions.read_lines(pdf)
    table_line = _line_with(lines, "Table 1.")
    equation_line = _line_with(lines, "Equation caption")
    assert abs(table_line.centre - table_line.page_width / 2) > 20
    assert abs(equation_line.centre - equation_line.page_width / 2) > 20


def test_note_and_credit_stay_left_while_the_description_is_centred(tmp_path: Path) -> None:
    manuscript = _six_caption_manuscript(tmp_path)
    pdf = _caption_pdf(tmp_path, manuscript)

    lines = captions.read_lines(pdf)
    note = _line_with(lines, "Short note.")
    credit = _line_with(lines, "Short credit.")

    assert abs(note.centre - note.page_width / 2) > 20
    assert abs(credit.centre - credit.page_width / 2) > 20
    assert note.x_min < note.page_width / 3
    assert credit.x_min < credit.page_width / 3


def test_wrapped_centred_illustration_caption_still_maps(tmp_path: Path) -> None:
    manuscript = _six_caption_manuscript(tmp_path)
    pdf = _caption_pdf(tmp_path, manuscript)

    texts = pages.page_texts(pdf)
    labels = pages.numbered_labels(texts)
    illustrations = pages.illustration_pages(texts)

    assert "Photograph 1" in labels and "Photograph 2" in labels
    assert any("Photograph 2" in found for found in illustrations.values())


def test_specimen_captions_are_centred() -> None:
    pdf, _previous, _sheet = specimen_build()

    result = captions.check(pdf, model.load(SPECIMEN))

    assert result.status == "pass", result.detail
    assert result.evidence["groups"]["chart"]["wrapped"] >= 1
    assert result.evidence["groups"]["diagram"]["wrapped"] >= 1
    assert result.evidence["groups"]["illustration"]["wrapped"] >= 1


def _side_manuscript(
    tmp_path: Path,
    preset: str,
    caption: str,
    companion: str,
    name: str,
) -> model.Manuscript:
    return _manuscript(
        tmp_path,
        [
            {
                "id": "b-photo",
                "type": "illustration",
                "illustrationId": "photo-1",
                "caption": caption,
                "composition": {"preset": preset, "companion": "b-text"},
            },
            {"id": "b-text", "type": "paragraph", "text": companion},
        ],
        name=name,
    )


def _side_pdf(
    manuscript: model.Manuscript,
    companion: str,
    *,
    composition: str | None = None,
    credit: str | None = None,
    name: str = "side-caption",
) -> Path:
    spec = captions.expected_captions(manuscript)[0]
    preset = composition or spec.preset
    credit_source = _q(credit if credit is not None else (spec.credit or ""))
    return compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#preset-illustration(\n"
        "  rect(width: 100%, height: 70pt, fill: black),\n"
        f"  caption: {_q(spec.text)},\n"
        f"  credit: {credit_source},\n"
        f"  composition: {_q(preset)},\n"
        f"  companion: [#preset-paragraph({_q(companion)})],\n"
        ")\n",
        name,
    )


SIDE_COMPANION = (
    "The companion prose runs beside the image in its own column, so caption isolation "
    "must ignore these interleaved lines and measure only the image-column text."
)


def test_side_left_caption_wraps_to_three_lines_and_passes_geometry(tmp_path: Path) -> None:
    caption = (
        "Lễ đón tiếp: 東京の皇居で、両陛下が並んで立つ。写真は2014年の歓迎式典を記録する。"
        "The narrow image column wraps this bilingual description across at least three lines."
    )
    manuscript = _side_manuscript(tmp_path, "side-left", caption, SIDE_COMPANION, "side-left")
    pdf = _side_pdf(manuscript, SIDE_COMPANION)

    result = captions.check(pdf, manuscript)

    assert result.status == "pass", result.detail
    entry = result.evidence["captions"][0]
    assert entry["preset"] == "side-left"
    assert entry["lines"] >= 3
    assert abs(entry["targetCentrePt"] - 169.31) <= 0.1
    assert result.evidence["maxDeltaPt"] <= captions.TOLERANCE_PT
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    assert "東京" in text and "Lễ đón tiếp" in text


def test_side_right_caption_is_measured_against_its_own_column(tmp_path: Path) -> None:
    caption = (
        "A second description long enough to wrap inside the right-hand image column "
        "so each rendered line is measured against that column's own centre, not the page."
    )
    manuscript = _side_manuscript(tmp_path, "side-right", caption, SIDE_COMPANION, "side-right")
    pdf = _side_pdf(manuscript, SIDE_COMPANION, name="side-right")

    result = captions.check(pdf, manuscript)

    assert result.status == "pass", result.detail
    entry = result.evidence["captions"][0]
    assert entry["preset"] == "side-right"
    assert abs(entry["targetCentrePt"] - 425.97) <= 0.1
    assert entry["lines"] >= 2


def test_a_page_centred_side_caption_fails_loudly(tmp_path: Path) -> None:
    caption = (
        "A description that is deliberately rendered on the page centre, which is not the "
        "declared centre of either image column and must fail rather than pass by coincidence."
    )
    manuscript = _side_manuscript(tmp_path, "side-left", caption, SIDE_COMPANION, "side-page-centred")
    pdf = _side_pdf(manuscript, SIDE_COMPANION, composition="full", name="side-page-centred")

    result = captions.check(pdf, manuscript)

    assert result.status == "fail"
    assert result.code == "VERIFY_FAILED"
    assert "image column" in result.detail


def test_side_credit_is_left_aligned_at_the_column_edge(tmp_path: Path) -> None:
    caption = "A short description beside a credit."
    manuscript = _side_manuscript(tmp_path, "side-left", caption, SIDE_COMPANION, "side-credit")
    pdf = _side_pdf(manuscript, SIDE_COMPANION, name="side-credit")

    result = captions.check(pdf, manuscript)

    assert result.status == "pass", result.detail
    assert result.evidence["maxCreditDeltaPt"] <= captions.TOLERANCE_PT


def test_a_right_aligned_side_credit_control_fails(tmp_path: Path) -> None:
    caption = "A short description beside a misplaced credit."
    manuscript = _side_manuscript(tmp_path, "side-left", caption, SIDE_COMPANION, "side-credit-control")
    spec = captions.expected_captions(manuscript)[0]
    credit = f'block(inset: (left: 80pt))[{spec.credit or ""}]'
    pdf = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#preset-illustration(\n"
        "  rect(width: 100%, height: 70pt, fill: black),\n"
        f"  caption: {_q(spec.text)},\n"
        f"  credit: {credit},\n"
        '  composition: "side-left",\n'
        f"  companion: [#preset-paragraph({_q(SIDE_COMPANION)})],\n"
        ")\n",
        "side-credit-control",
    )

    result = captions.check(pdf, manuscript)

    assert result.status == "fail"
    assert result.code == "VERIFY_FAILED"
    assert "credit" in result.detail


def test_duplicate_side_caption_labels_fail_loudly(tmp_path: Path) -> None:
    caption = "A description rendered twice in the same image column."
    manuscript = _side_manuscript(tmp_path, "side-left", caption, SIDE_COMPANION, "side-ambiguous")
    spec = captions.expected_captions(manuscript)[0]
    block = (
        "#preset-illustration(\n"
        "  rect(width: 100%, height: 60pt, fill: black),\n"
        f"  caption: {_q(spec.text)},\n"
        f"  credit: {_q(spec.credit or '')},\n"
        '  composition: "side-left",\n'
        f"  companion: [#preset-paragraph({_q(SIDE_COMPANION)})],\n"
        ")\n"
    )
    pdf = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        + block + block,
        "side-ambiguous",
    )

    result = captions.check(pdf, manuscript)

    assert result.status == "fail"
    assert "more than once" in result.detail
