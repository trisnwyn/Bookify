"""Task 49: adversarial side compositions, read order and the one-per-page limit."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from helpers import ROOT
from bookify.design import tokens
from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.publish import normalize, report, typst_driver
from bookify.verify.checks import captions, pages

FIXTURE = ROOT / "fixtures" / "adversarial" / "compositions.yaml"
LEFT_CENTRE = 60.0 + 475.28 * 0.46 / 2
RIGHT_CENTRE = 60.0 + 475.28 - 475.28 * 0.46 / 2
LEFT_EDGE = 60.0
RIGHT_EDGE = 60.0 + 475.28 - 475.28 * 0.46
PROSE_LEFT = 60.0 + 475.28 * 0.46 + 16.0
PROSE_RIGHT = 60.0 + 475.28


@pytest.fixture(scope="module")
def built() -> tuple[typst_driver.BuildResult, model.Manuscript]:
    work = ROOT / ".cache" / "layout-adversarial"
    work.mkdir(parents=True, exist_ok=True)
    result = typst_driver.build(FIXTURE, work / "adversarial.pdf", work / "build", offline=True)
    return result, model.load(FIXTURE)


def _page_text(pdf: Path, page: int) -> str:
    return pages.page_texts(pdf)[page - 1]


def _measurements(manuscript: model.Manuscript, pdf: Path) -> dict[str, captions.CaptionMeasurement]:
    lines = captions.read_lines(pdf)
    measured = {}
    for spec in captions.expected_captions(manuscript):
        outcome = captions.measure(spec, lines)
        assert not isinstance(outcome, str), outcome
        measured[spec.block_id] = outcome
    return measured


def test_two_side_compositions_defer_exactly_one_and_never_share_a_page(built) -> None:
    result, _manuscript_object = built
    placements = result.report["placements"]

    assert len(placements) == 2
    assert len({placement["page"] for placement in placements}) == 2
    assert result.report["deferredIllustrations"] == ["photo-b"]
    entries = result.report["compositions"]
    assert [entry["blockId"] for entry in entries] == ["b-photo-a", "b-photo-b"]
    assert [entry["preset"] for entry in entries] == ["side-left", "side-right"]
    assert [entry["deferred"] for entry in entries] == [False, True]

    for page in {placement["page"] for placement in placements}:
        text = _page_text(result.pdf, page)
        assert text.count("Photograph ") == 1, f"page {page} holds two illustrations"


def test_the_whole_group_moves_never_the_companion_alone(built) -> None:
    result, manuscript = built
    placements = result.report["placements"]
    second_page = placements[1]["page"]

    page_text = _page_text(result.pdf, second_page)
    assert "Photograph 2." in page_text
    assert "RIGHT-COMPANION-MARKER" in page_text
    for placement in placements:
        other = _page_text(result.pdf, placement["page"])
        assert other.count("RIGHT-COMPANION-MARKER") <= 1
    measurements = _measurements(manuscript, result.pdf)
    assert measurements["b-photo-b"].page == second_page


def test_side_left_reads_image_unit_then_prose_and_stays_in_its_columns(built) -> None:
    result, manuscript = built
    lines = captions.read_lines(result.pdf)
    measurement = _measurements(manuscript, result.pdf)["b-photo-a"]

    caption_lines = measurement.lines
    assert all(abs(line.centre - LEFT_CENTRE) <= captions.TOLERANCE_PT for line in caption_lines)
    assert all(line.x_max <= LEFT_EDGE + 475.28 * 0.46 + captions.TOLERANCE_PT for line in caption_lines)
    companion = next(line for line in lines if line.text.startswith("LEFT-COMPANION-MARKER."))
    assert companion.page == measurement.page
    assert companion.x_min >= PROSE_LEFT - 1.0
    assert max(line.x_max for line in caption_lines) < companion.x_min


def test_side_right_reads_prose_then_image_unit_and_stays_in_its_columns(built) -> None:
    result, manuscript = built
    lines = captions.read_lines(result.pdf)
    measurement = _measurements(manuscript, result.pdf)["b-photo-b"]

    caption_lines = measurement.lines
    assert all(abs(line.centre - RIGHT_CENTRE) <= captions.TOLERANCE_PT for line in caption_lines)
    assert all(line.x_min >= RIGHT_EDGE - captions.TOLERANCE_PT for line in caption_lines)
    companion = next(line for line in lines if line.text.startswith("RIGHT-COMPANION-MARKER."))
    assert companion.page == measurement.page
    assert companion.x_max <= PROSE_RIGHT + 1.0
    assert companion.x_max < min(line.x_min for line in caption_lines)


def test_each_companion_and_caption_appears_exactly_once(built) -> None:
    result, _manuscript_object = built
    texts = pages.page_texts(result.pdf)
    text = " ".join(texts)

    assert text.count("LEFT-COMPANION-MARKER") == 1
    assert text.count("RIGHT-COMPANION-MARKER") == 1
    assert text.count("Photograph 1.") == 1
    assert text.count("Photograph 2.") == 1
    assert len(texts) == 4


def test_no_composition_is_split_across_a_page_boundary(built) -> None:
    result, manuscript = built

    check = captions.check(result.pdf, manuscript)

    assert check.status == "pass", check.detail
    assert check.evidence["maxCreditDeltaPt"] <= captions.TOLERANCE_PT
    for measurement in _measurements(manuscript, result.pdf).values():
        assert len({line.page for line in measurement.lines}) == 1


def test_all_three_presets_compile_in_one_document() -> None:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "adversarial-three-presets",
        "metadata": {"title": "Three presets", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-a",
                "title": "Three presets",
                "blocks": [
                    {
                        "id": "b-left",
                        "type": "illustration",
                        "illustrationId": "photo-a",
                        "composition": {"preset": "side-left", "companion": "b-left-text"},
                    },
                    {"id": "b-left-text", "type": "paragraph", "text": "Left companion."},
                    {
                        "id": "b-right",
                        "type": "illustration",
                        "illustrationId": "photo-b",
                        "composition": {"preset": "side-right", "companion": "b-right-text"},
                    },
                    {"id": "b-right-text", "type": "paragraph", "text": "Right companion."},
                    {
                        "id": "b-full",
                        "type": "illustration",
                        "illustrationId": "photo-1",
                        "composition": {"preset": "full"},
                    },
                ],
            }
        ],
    }
    work = ROOT / ".cache" / "layout-three-presets"
    work.mkdir(parents=True, exist_ok=True)
    manuscript = work / "manuscript.yaml"
    manuscript.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    result = typst_driver.build(manuscript, work / "out.pdf", work / "build", offline=True)

    assert {entry["preset"] for entry in result.report["compositions"]} == {
        "side-left", "side-right", "full",
    }
    pages_used = [placement["page"] for placement in result.report["placements"]]
    assert len(set(pages_used)) == 3


def _overflow_pdf() -> Path:
    work = ROOT / ".cache" / "layout-overflow"
    work.mkdir(parents=True, exist_ok=True)
    source = work / "over.typ"
    source.write_text(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#block(breakable: false, {\n"
        "  block(width: 100%, align(center, rect(width: 100%, height: 1300pt, fill: black)))\n"
        '  preset-figure-caption("Photograph 1. An over-tall composition.")\n'
        "})\n"
    )
    pdf = work / "over.pdf"
    import subprocess

    subprocess.run(
        [
            "bwrap", "--unshare-net", "--bind", "/", "/", "--chdir", str(ROOT), "--",
            str(ROOT / "tools" / "typst" / "typst"), "compile",
            "--ignore-system-fonts", "--font-path", "assets/fonts",
            "--package-path", "vendor/typst",
            "--package-cache-path", ".cache/empty-pkg",
            "--root", ".", str(source.relative_to(ROOT)), str(pdf),
        ],
        check=True, capture_output=True, text=True, cwd=ROOT,
    )
    return pdf


def test_an_over_tall_composition_fails_loudly_instead_of_clipping() -> None:
    pdf = _overflow_pdf()
    document = {
        "sections": [
            {
                "blocks": [
                    {
                        "id": "b-photo",
                        "type": "illustration",
                        "label": "Photograph 1",
                        "composition": "side-left",
                        "companion": {"id": "b-text", "type": "paragraph", "text": "Companion."},
                    }
                ]
            }
        ]
    }

    with pytest.raises(BookifyError) as error:
        report.require_composition_fit(pdf, document, {"Photograph 1": 1}, 841.89)

    assert error.value.code == "BUILD_FAILED"
    assert error.value.locator == "b-photo"
    assert "does not fit" in error.value.message


def _side_document() -> dict:
    return {
        "sections": [
            {
                "blocks": [
                    {
                        "id": "b-photo",
                        "type": "illustration",
                        "label": "Photograph 1",
                        "composition": "side-left",
                    }
                ]
            }
        ]
    }


def _stub_page_x_max(monkeypatch: pytest.MonkeyPatch, x_max: float) -> None:
    line = ("Companion text.", tokens.PAGE_MARGIN_PT, x_max, 100.0, 120.0)
    monkeypatch.setattr(report, "_bbox_lines", lambda _pdf, _page: (595.28, 841.89, [line]))


def test_a_real_fitting_composition_passes_the_fit_measure(built, monkeypatch) -> None:
    result, manuscript = built
    document = normalize.build(manuscript, {})

    side_blocks = [
        block
        for section in document.data["sections"]
        for block in section["blocks"]
        if block.get("type") == "illustration" and block.get("composition") in report.SIDE_PRESETS
    ]
    assert [block["id"] for block in side_blocks] == ["b-photo-a", "b-photo-b"]
    numbered = result.report["numbered"]
    assert {"Photograph 1", "Photograph 2"} <= numbered.keys()
    assert all(block["label"] in numbered for block in side_blocks)

    measured_pages: list[int] = []
    real_bbox_lines = report._bbox_lines

    def recording_bbox_lines(pdf: Path, page: int):
        measured_pages.append(page)
        return real_bbox_lines(pdf, page)

    monkeypatch.setattr(report, "_bbox_lines", recording_bbox_lines)
    report.require_composition_fit(result.pdf, document.data, numbered, 841.89)

    expected_pages = {numbered[block["label"]] for block in side_blocks}
    assert len(expected_pages) == 2
    assert set(measured_pages) == expected_pages


def test_the_fit_allowance_stays_at_the_approved_three_points() -> None:
    assert report.FIT_GLYPH_OVERHANG_PT == 3.0


def test_a_2_5pt_horizontal_overhang_stays_inside_the_fit_allowance(monkeypatch) -> None:
    measure_right = tokens.PAGE_MARGIN_PT + tokens.BODY_MEASURE_PT
    _stub_page_x_max(monkeypatch, measure_right + 2.5)

    report.require_composition_fit(Path("stub.pdf"), _side_document(), {"Photograph 1": 1}, 841.89)


def test_a_3_5pt_horizontal_overhang_fails_the_fit_guard(monkeypatch) -> None:
    measure_right = tokens.PAGE_MARGIN_PT + tokens.BODY_MEASURE_PT
    _stub_page_x_max(monkeypatch, measure_right + 3.5)

    with pytest.raises(BookifyError) as error:
        report.require_composition_fit(Path("stub.pdf"), _side_document(), {"Photograph 1": 1}, 841.89)

    assert error.value.code == "BUILD_FAILED"
    assert error.value.locator == "b-photo"
    assert "leaves its column" in error.value.message
