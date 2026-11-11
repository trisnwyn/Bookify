"""Task 41: the reviewed catalogue inventory gate.

These tests prove the fixture and the content-level inventory without needing the
chart/diagram renderers. A text-only Typst fixture exercises the PDF text branch;
the real double build belongs to Task 43.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from helpers import ROOT, compile_typ
from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.verify import runner
from bookify.verify.checks import Check, passed as check_passed
from bookify.verify.checks import captions
from bookify.verify.checks import catalogue as catalogue_check
from bookify.verify.checks import (
    determinism,
    glyphs,
    illustration_limit,
    offline,
    pages,
    rights,
    text,
    xrefs,
)

CATALOGUE = ROOT / "content" / "catalogue.yaml"
FIXTURE = ROOT / "fixtures" / "expected" / "catalogue.json"


@pytest.fixture(scope="module")
def manuscript() -> model.Manuscript:
    return model.load(CATALOGUE)


@pytest.fixture(scope="module")
def expected() -> dict:
    return catalogue_check.load_expected(FIXTURE)


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _load_variant(tmp_path: Path, mutate) -> model.Manuscript:
    data = yaml.safe_load(CATALOGUE.read_text())
    mutate(data)
    target = tmp_path / "catalogue-variant.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return model.load(target, root=ROOT)


def _chart_block(block_id: str = "b-chart-extra") -> dict:
    return {
        "id": block_id,
        "type": "chart",
        "caption": "Extra chart for a negative inventory test.",
        "chart": {
            "kind": "bar",
            "categories": ["A"],
            "series": [{"id": "s", "label": "Series"}],
            "values": [[1]],
            "axis": {"unit": "index", "min": 0},
            "verification": "synthetic",
            "notes": "Synthetic fixture value.",
        },
    }


def _diagram_block(block_id: str = "b-diagram-extra") -> dict:
    return {
        "id": block_id,
        "type": "diagram",
        "caption": "Extra diagram for a negative inventory test.",
        "note": "Illustrative schematic; no source evidence.",
        "diagram": {
            "preset": "process",
            "synthetic": True,
            "nodes": [{"id": "n-a", "label": "A"}, {"id": "n-b", "label": "B"}],
            "edges": [{"from": "n-a", "to": "n-b"}],
        },
    }


def _illustration_block(block_id: str = "b-illustration-extra") -> dict:
    return {"id": block_id, "type": "illustration", "illustrationId": "photo-1"}


def _coverage_table(data: dict) -> dict:
    return next(
        block
        for section in data["sections"]
        for block in section["blocks"]
        if block["id"] == "b-coverage-table"
    )


def _text_pdf(
    name: str,
    manuscript: model.Manuscript,
    expected: dict,
    *,
    omit_caption: str | None = None,
    omit_family: str | None = None,
    duplicate_caption: str | None = None,
    same_page_photos: bool = False,
) -> Path:
    parts = [
        '#import "/typst/theme.typ": fonts',
        '#set page(width: 595pt, height: 842pt, margin: 40pt)',
        '#set text(font: (fonts.latin, fonts.japanese), size: 8pt)',
        "#set par(justify: false)",
    ]
    specs = captions.expected_captions(manuscript)
    photo_blocks = {entry["blockId"] for entry in expected["illustrationFamilies"]}

    ordinary = [spec for spec in specs if spec.block_id not in photo_blocks]
    photos = [spec for spec in specs if spec.block_id in photo_blocks]
    for index, spec in enumerate(ordinary):
        if index:
            parts.append("#pagebreak()")
        if spec.block_id != omit_caption:
            parts.append(f"#text({_q(spec.text)})")

    parts.append("#pagebreak()")
    for index, row in enumerate(expected["coverageRows"]):
        label = "REMOVED FAMILY" if row["familyLabel"] == omit_family else row["familyLabel"]
        row_text = f"{label} | {row['kindCell']} | {row['figureCell']}"
        parts.append(f"#text({_q(row_text)})")
        if index < len(expected["coverageRows"]) - 1:
            parts.append("#linebreak()")

    for index, spec in enumerate(photos):
        if index == 0:
            parts.append("#pagebreak()")
        elif not (same_page_photos and index == 1):
            parts.append("#pagebreak()")
        elif same_page_photos and index == 1:
            parts.append("#linebreak()")
        if spec.block_id != omit_caption:
            parts.append(f"#text({_q(spec.text)})")
            if duplicate_caption == spec.block_id:
                parts.append("#linebreak()")
                parts.append(f"#text({_q(spec.text)})")

    return compile_typ("\n".join(parts), name)


def test_reviewed_fixture_is_exactly_the_spec_inventory(expected: dict) -> None:
    counts = expected["counts"]
    assert counts == {
        "chartFamilies": 15,
        "charts": 16,
        "diagramPresets": 10,
        "diagrams": 10,
        "illustrations": 4,
        "figures": 26,
        "photographs": 4,
        "tables": 1,
        "coverageRows": 29,
    }
    assert [family["kind"] for family in expected["chartFamilies"]].count("pie") == 1
    pie = next(family for family in expected["chartFamilies"] if family["kind"] == "pie")
    assert [variant["variant"] for variant in pie["variants"]] == ["pie", "donut"]
    assert len(expected["coverageRows"]) == 29
    assert len({row["familyLabel"] for row in expected["coverageRows"]}) == 29


def test_inventory_matches_authored_content_without_renderers(
    manuscript: model.Manuscript, expected: dict
) -> None:
    assert catalogue_check.inventory_problems(manuscript, expected) == []


def test_fixture_has_missing_and_extra_blocks_in_both_directions(
    manuscript: model.Manuscript, expected: dict
) -> None:
    doctored = copy.deepcopy(expected)
    doctored["chartFamilies"][0]["variants"][0]["blockId"] = "b-chart-expected-extra"

    problems = catalogue_check.inventory_problems(manuscript, doctored)

    assert any("missing chart block(s): b-chart-expected-extra" in problem for problem in problems)
    assert any("extra chart block(s): b-chart-bar" in problem for problem in problems)


def test_extra_manuscript_chart_block_fails(manuscript: model.Manuscript, expected: dict, tmp_path: Path) -> None:
    def mutate(data: dict) -> None:
        data["sections"][-1]["blocks"].append(_chart_block())

    problems = catalogue_check.inventory_problems(_load_variant(tmp_path, mutate), expected)
    assert any("extra chart block(s): b-chart-extra" in problem for problem in problems)


def test_missing_manuscript_chart_block_fails(expected: dict, tmp_path: Path) -> None:
    def mutate(data: dict) -> None:
        for section in data["sections"]:
            section["blocks"] = [block for block in section["blocks"] if block["id"] != "b-chart-grouped"]

    problems = catalogue_check.inventory_problems(_load_variant(tmp_path, mutate), expected)
    assert any("missing chart block(s): b-chart-grouped" in problem for problem in problems)


def test_extra_manuscript_diagram_and_illustration_fail(
    expected: dict, tmp_path: Path
) -> None:
    def mutate(data: dict) -> None:
        data["sections"][-1]["blocks"].extend([_diagram_block(), _illustration_block()])

    problems = catalogue_check.inventory_problems(_load_variant(tmp_path, mutate), expected)
    assert any("extra diagram block(s): b-diagram-extra" in problem for problem in problems)
    assert any("extra illustration block(s): b-illustration-extra" in problem for problem in problems)


def test_pie_donut_variant_mismatch_fails(expected: dict, tmp_path: Path) -> None:
    def mutate(data: dict) -> None:
        for section in data["sections"]:
            for block in section["blocks"]:
                if block["id"] == "b-chart-donut":
                    block["chart"]["hole"] = 0

    problems = catalogue_check.inventory_problems(_load_variant(tmp_path, mutate), expected)
    assert any("chart variant is pie, expected donut" in problem for problem in problems)


def test_coverage_table_must_have_exactly_29_rows(expected: dict, tmp_path: Path) -> None:
    def mutate(data: dict) -> None:
        table = _coverage_table(data)
        table["rows"] = table["rows"][:-1]

    problems = catalogue_check.inventory_problems(_load_variant(tmp_path, mutate), expected)
    assert any("coverage table has 28 rows, expected 29" in problem for problem in problems)


def test_coverage_table_row_content_is_checked(expected: dict, tmp_path: Path) -> None:
    def mutate(data: dict) -> None:
        table = _coverage_table(data)
        table["rows"][0][0] = "Not Bar"

    problems = catalogue_check.inventory_problems(_load_variant(tmp_path, mutate), expected)
    assert any("coverage row 1" in problem for problem in problems)


def test_coverage_table_must_not_have_an_extra_row(expected: dict, tmp_path: Path) -> None:
    def mutate(data: dict) -> None:
        table = _coverage_table(data)
        table["rows"] = table["rows"] + [list(table["rows"][-1])]

    problems = catalogue_check.inventory_problems(_load_variant(tmp_path, mutate), expected)
    assert any("coverage table has 30 rows, expected 29" in problem for problem in problems)


def test_diagram_preset_mismatch_fails(expected: dict, tmp_path: Path) -> None:
    def mutate(data: dict) -> None:
        for section in data["sections"]:
            for block in section["blocks"]:
                if block["id"] == "b-diagram-cycle":
                    block["diagram"]["preset"] = "network"

    problems = catalogue_check.inventory_problems(_load_variant(tmp_path, mutate), expected)
    assert any("diagram preset is network, expected cycle" in problem for problem in problems)


def test_missing_xref_token_fails(manuscript: model.Manuscript, expected: dict) -> None:
    doctored = copy.deepcopy(expected)
    doctored["xrefs"].append({"blockId": "b-not-referenced", "label": "Figure 1"})

    problems = catalogue_check.inventory_problems(manuscript, doctored)

    assert any("missing cross-reference token {ref:b-not-referenced}" in problem for problem in problems)


def test_editorial_and_reconstruction_caption_wording_is_checked(
    manuscript: model.Manuscript, expected: dict
) -> None:
    doctored = copy.deepcopy(expected)
    editorial = next(
        entry for entry in doctored["illustrationFamilies"] if entry["illustrationId"] == "art-1"
    )
    editorial["captionRequires"] = ["a phrase that is definitely absent"]

    problems = catalogue_check.inventory_problems(manuscript, doctored)

    assert any("does not contain 'a phrase that is definitely absent'" in problem for problem in problems)


def test_record_kind_and_local_licence_are_checked(manuscript: model.Manuscript, expected: dict) -> None:
    doctored = copy.deepcopy(expected)
    historical = next(
        entry for entry in doctored["illustrationFamilies"] if entry["illustrationId"] == "hist-1"
    )
    historical["recordKind"] = "later_depiction"
    editorial = next(
        entry for entry in doctored["illustrationFamilies"] if entry["illustrationId"] == "art-1"
    )
    editorial["licence"] = "Wrong licence"

    problems = catalogue_check.inventory_problems(manuscript, doctored)

    assert any("record kind is contemporary_photograph, expected later_depiction" in problem for problem in problems)
    assert any("licence is 'Original work created for this catalogue'" in problem for problem in problems)


def test_missing_fixture_fails_closed(tmp_path: Path, manuscript: model.Manuscript) -> None:
    fake_pdf = tmp_path / "not-read.pdf"
    fake_pdf.write_bytes(b"not a pdf")

    result = catalogue_check.check(fake_pdf, manuscript, tmp_path / "missing.json")

    assert result.status == "fail"
    assert result.code == "VERIFY_FAILED"
    assert "not found" in result.detail


def test_fixture_rejects_a_non_spec_inventory(tmp_path: Path, expected: dict) -> None:
    doctored = copy.deepcopy(expected)
    doctored["chartFamilies"].append(
        {
            "family": "unknown",
            "familyLabel": "Unknown",
            "kind": "unknown",
            "variants": [{"variant": "default", "blockId": "b-chart-unknown", "label": "Figure 17"}],
        }
    )
    target = tmp_path / "bad.json"
    target.write_text(json.dumps(doctored))

    with pytest.raises(BookifyError) as caught:
        catalogue_check.load_expected(target)

    assert caught.value.code == "VERIFY_FAILED"


@pytest.fixture(scope="module")
def complete_pdf(manuscript: model.Manuscript, expected: dict) -> Path:
    return _text_pdf("catalogue-inventory-complete", manuscript, expected)


def test_catalogue_check_passes_on_complete_text(
    complete_pdf: Path, manuscript: model.Manuscript, expected: dict
) -> None:
    result = catalogue_check.check(complete_pdf, manuscript)

    assert result.status == "pass", result.detail
    assert result.evidence["counts"]["charts"] == 16
    assert result.evidence["counts"]["diagrams"] == 10
    assert result.evidence["counts"]["illustrations"] == 4
    assert result.evidence["coverageRows"] == 29
    assert result.evidence["figureLabels"] == [f"Figure {number}" for number in range(1, 27)]


def _printed_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        found: list[str] = []
        for key in sorted(value):
            found.extend(_printed_strings(value[key]))
        return found
    if isinstance(value, list):
        found = []
        for item in value:
            found.extend(_printed_strings(item))
        return found
    return []


def test_text_probe_accepts_the_printed_catalogue_captions(manuscript: model.Manuscript) -> None:
    """Regression for C1: the extraction probe and the printed caption share one rule."""
    import subprocess

    from bookify.publish import normalize

    figure_paths = {
        block["id"]: "/unused.svg"
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    }
    document = normalize.build(manuscript, figure_paths, draft=True)
    strings = list(dict.fromkeys(text for text in _printed_strings(document.data) if text.strip()))
    parts = [
        '#import "/typst/theme.typ": fonts',
        '#set page(width: 595pt, height: 842pt, margin: 40pt)',
        '#set text(font: (fonts.latin, fonts.japanese), size: 8pt)',
        "#set par(justify: false)",
    ]
    for item in strings:
        escaped = item.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        parts.append(f'#text("{escaped}")')
        parts.append("#linebreak()")
    pdf = compile_typ("\n".join(parts), "catalogue-printed-captions")

    result = text.check(pdf, manuscript)

    assert result.status == "pass", result.detail
    extracted = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    normalised = " ".join(extracted.split())
    assert "conceptual reconstruction" in normalised
    assert "Reconstruction." not in normalised, "the honest prose class name must not be duplicated"


def test_check_rejects_a_doctored_fixture_in_both_directions(
    complete_pdf: Path, manuscript: model.Manuscript, expected: dict, tmp_path: Path
) -> None:
    doctored = copy.deepcopy(expected)
    doctored["chartFamilies"][0]["variants"][0]["blockId"] = "b-chart-expected-extra"
    target = tmp_path / "doctored.json"
    target.write_text(json.dumps(doctored))

    result = catalogue_check.check(complete_pdf, manuscript, target)

    assert result.status == "fail"
    assert any("missing chart block(s): b-chart-expected-extra" in problem for problem in result.evidence["problems"])
    assert any("extra chart block(s): b-chart-bar" in problem for problem in result.evidence["problems"])


def test_check_fails_when_a_family_label_is_missing_from_the_pdf(
    manuscript: model.Manuscript, expected: dict
) -> None:
    pdf = _text_pdf("catalogue-missing-family", manuscript, expected, omit_family="Swimlane")

    result = catalogue_check.check(pdf, manuscript)

    assert result.status == "fail"
    assert any("coverage familyLabel not extractable: 'Swimlane'" in problem for problem in result.evidence["problems"])


def test_check_fails_when_a_figure_label_is_missing_from_the_pdf(
    manuscript: model.Manuscript, expected: dict
) -> None:
    pdf = _text_pdf("catalogue-missing-figure", manuscript, expected, omit_caption="b-diagram-venn")

    result = catalogue_check.check(pdf, manuscript)

    assert result.status == "fail"
    assert any("Figure 25: printed figure label not found" in problem for problem in result.evidence["problems"])


def test_check_fails_when_an_illustration_caption_is_duplicated(
    manuscript: model.Manuscript, expected: dict
) -> None:
    pdf = _text_pdf(
        "catalogue-duplicate-photo",
        manuscript,
        expected,
        duplicate_caption="b-illustration-photo",
    )

    result = catalogue_check.check(pdf, manuscript)

    assert result.status == "fail"
    assert any("Photograph 1: printed caption occurs 2 time(s)" in problem for problem in result.evidence["problems"])


def test_check_fails_when_two_photographs_share_a_page(
    manuscript: model.Manuscript, expected: dict
) -> None:
    pdf = _text_pdf(
        "catalogue-two-photos-one-page",
        manuscript,
        expected,
        same_page_photos=True,
    )

    result = catalogue_check.check(pdf, manuscript)

    assert result.status == "fail"
    assert any("pages hold more than one photograph" in problem for problem in result.evidence["problems"])


def _stub_runner_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    def pass_(identifier: str):
        def check(*_args, **_kwargs) -> Check:
            return check_passed(identifier, "stub")

        return check

    for module, identifier in (
        (offline, "offline"),
        (determinism, "determinism"),
        (glyphs, "glyphs"),
        (text, "text"),
        (illustration_limit, "illustration-limit"),
        (rights, "rights"),
        (xrefs, "xrefs"),
    ):
        monkeypatch.setattr(module, "check", pass_(identifier))
    monkeypatch.setattr(pages, "check_geometry", pass_("pages"))
    monkeypatch.setattr(runner.geometry_check, "check", pass_("figure-geometry"))
    monkeypatch.setattr(runner, "_review", lambda *_args: check_passed("review", "stub"))


def _run_wiring(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, manuscript_id: str) -> tuple[dict, list[dict], list[dict]]:
    _stub_runner_checks(monkeypatch)
    captions_calls: list[dict] = []
    catalogue_calls: list[dict] = []

    def captions_spy(_pdf, _manuscript, **kwargs):
        captions_calls.append(kwargs)
        return check_passed("captions", "stub")

    def catalogue_spy(_pdf, _manuscript, **_kwargs):
        catalogue_calls.append({"called": True})
        return check_passed("catalogue", "stub")

    monkeypatch.setattr(runner.captions_check, "check", captions_spy)
    monkeypatch.setattr(runner.catalogue_check, "check", catalogue_spy)
    fake_manuscript = SimpleNamespace(id=manuscript_id, revision=1, root=tmp_path, sections=(), data={})
    monkeypatch.setattr(runner.model, "load", lambda _path: fake_manuscript)
    pdf = tmp_path / "wiring.pdf"
    pdf.write_bytes(b"stub")
    manuscript_path = tmp_path / "wiring.yaml"
    manuscript_path.write_text("stub")

    report = runner.run(pdf, manuscript_path, None)
    return report, captions_calls, catalogue_calls


def test_runner_enables_coverage_and_catalogue_only_for_the_catalogue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report, captions_calls, catalogue_calls = _run_wiring(monkeypatch, tmp_path, "visual-catalogue")
    ids = {check["id"] for check in report["checks"]}

    assert "catalogue" in ids
    assert captions_calls[-1]["require_coverage"] is True
    assert catalogue_calls == [{"called": True}]


def test_runner_leaves_the_specimen_check_set_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report, captions_calls, catalogue_calls = _run_wiring(monkeypatch, tmp_path, "specimen")
    ids = {check["id"] for check in report["checks"]}

    assert "catalogue" not in ids
    assert captions_calls[-1]["require_coverage"] is False
    assert catalogue_calls == []
