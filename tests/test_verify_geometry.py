"""Task 48: catalogue figure geometry from rendered ink, not declared boxes."""

from __future__ import annotations

from pathlib import Path

import yaml

from helpers import ROOT, SPECIMEN, build_report_path, compile_typ, specimen_build
from bookify.manuscript import model
from bookify.publish import normalize
from bookify.verify import runner
from bookify.verify.checks import captions, geometry
from bookify.verify.checks import pages as pages_check


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _chart(caption: str = "A chart measured by the geometry gate.") -> dict:
    return {
        "id": "b-chart",
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


def _diagram(caption: str = "A diagram measured by the geometry gate.") -> dict:
    return {
        "id": "b-diagram",
        "type": "diagram",
        "caption": caption,
        "diagram": {
            "preset": "process",
            "nodes": [{"id": "n-a", "label": "A"}, {"id": "n-b", "label": "B"}],
            "edges": [{"from": "n-a", "to": "n-b"}],
        },
    }


def _manuscript(tmp_path: Path, blocks: list[dict], name: str = "geometry") -> model.Manuscript:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": name,
        "metadata": {"title": "Geometry fixture", "languages": ["en", "vi", "ja"]},
        "sections": [{"id": "sec-a", "title": "Geometry", "blocks": blocks}],
    }
    target = tmp_path / f"{name}.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return model.load(target, root=ROOT)


def _companion(block_id: str, text: str) -> dict:
    return {"id": block_id, "type": "paragraph", "text": text}


def _all_three_manuscript(tmp_path: Path) -> model.Manuscript:
    return _manuscript(
        tmp_path,
        [
            _chart(),
            _diagram(),
            {
                "id": "b-photo",
                "type": "illustration",
                "illustrationId": "photo-1",
                "composition": {"preset": "side-left", "companion": "b-photo-text"},
            },
            _companion(
                "b-photo-text",
                "Companion prose beside the photograph, which must never be counted as figure ink.",
            ),
        ],
        name="geometry-all",
    )


def _all_three_pdf(manuscript: model.Manuscript) -> Path:
    specs = captions.expected_captions(manuscript)
    by_kind = {spec.kind: spec for spec in specs}
    companion = normalize.build(
        manuscript,
        {block["id"]: "unused.svg" for section in manuscript.sections for block in section["blocks"] if block["type"] == "chart"},
        draft=True,
    ).data["sections"][0]["blocks"][2]["companion"]["text"]
    return compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f"#preset-chart(rect(width: 280pt, height: 100pt, fill: black), caption: {_q(by_kind['chart'].text)})\n"
        "#pagebreak()\n"
        f"#preset-diagram(rect(width: 400pt, height: 100pt, fill: black), caption: {_q(by_kind['diagram'].text)})\n"
        "#pagebreak()\n"
        "#preset-illustration(\n"
        "  rect(width: 100%, height: 70pt, fill: black),\n"
        f"  caption: {_q(by_kind['illustration'].text)},\n"
        f"  credit: {_q(by_kind['illustration'].credit or '')},\n"
        '  composition: "side-left",\n'
        f"  companion: [#preset-paragraph({_q(companion)})],\n"
        ")\n",
        "geometry-all",
    )


def test_geometry_passes_for_centred_chart_diagram_and_side_illustration(tmp_path: Path) -> None:
    manuscript = _all_three_manuscript(tmp_path)
    pdf = _all_three_pdf(manuscript)

    result = geometry.check(pdf, manuscript)

    assert result.status == "pass", result.detail
    assert result.evidence["kinds"] == {"chart": 1, "diagram": 1, "illustration": 1}
    assert result.evidence["maxInkDeltaPt"] <= geometry.INK_TOLERANCE_PT
    assert result.evidence["maxCaptionDeltaPt"] <= geometry.INK_TOLERANCE_PT
    for figure in result.evidence["figures"]:
        assert {"canvas", "frame", "ink", "caption"} <= set(figure)
        assert figure["ink"]["contained"] is True
        assert abs(figure["ink"]["deltaPt"]) <= geometry.INK_TOLERANCE_PT


def test_a_left_positioned_figure_fails_on_ink_not_on_its_box(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path, [_chart("A left-positioned figure control.")], "geometry-left")
    spec = captions.expected_captions(manuscript)[0]
    pdf = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#block(width: 100%)[#rect(width: 120pt, height: 40pt, fill: black)]\n"
        f"#preset-figure-caption({_q(spec.text)})\n",
        "geometry-left",
    )

    result = geometry.check(pdf, manuscript)

    assert result.status == "fail"
    assert result.code == "VERIFY_FAILED"
    assert "visible ink off the declared canvas centre" in result.detail


def test_a_band_without_ink_fails_closed(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path, [_chart("A caption with no figure.")], "geometry-empty")
    spec = captions.expected_captions(manuscript)[0]
    pdf = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f"#preset-figure-caption({_q(spec.text)})\n",
        "geometry-empty",
    )

    result = geometry.check(pdf, manuscript)

    assert result.status == "fail"
    assert "no ink" in result.detail


def test_prose_above_a_figure_is_excluded_from_its_ink(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path, [_chart("A chart after a paragraph of prose.")], "geometry-prose")
    spec = captions.expected_captions(manuscript)[0]
    prose = (
        "This paragraph sits above the figure and is flush with the page margin. "
        "If its ink were included the measured band would run past the declared chart "
        "canvas and the containment gate would fail."
    )
    pdf = compile_typ(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        f"#preset-paragraph({_q(prose)})\n"
        f"#preset-chart(rect(width: 280pt, height: 90pt, fill: black), caption: {_q(spec.text)})\n",
        "geometry-prose",
    )

    result = geometry.check(pdf, manuscript)

    assert result.status == "pass", result.detail
    figure = result.evidence["figures"][0]
    assert figure["ink"]["leftPt"] >= figure["canvas"]["leftPt"] - 2
    assert figure["ink"]["rightPt"] <= figure["canvas"]["rightPt"] + 2


def test_runner_wires_the_geometry_gate_only_for_the_catalogue(monkeypatch) -> None:
    pdf, previous, sheet = specimen_build()
    data = yaml.safe_load(SPECIMEN.read_text())
    data["id"] = "visual-catalogue"
    work = ROOT / ".cache" / "geometry-runner"
    work.mkdir(parents=True, exist_ok=True)
    manuscript = work / "catalogue.yaml"
    manuscript.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    calls: list[str] = []

    def fake_geometry(pdf_path: Path, manuscript_object: model.Manuscript):
        calls.append(str(pdf_path))
        from bookify.verify.checks import passed

        return passed("figure-geometry", "stub")

    def fake_catalogue(pdf_path: Path, manuscript_object: model.Manuscript):
        from bookify.verify.checks import passed

        return passed("catalogue", "stub")

    monkeypatch.setattr(runner.geometry_check, "check", fake_geometry)
    monkeypatch.setattr(runner.catalogue_check, "check", fake_catalogue)

    report = runner.run(
        pdf, manuscript, None,
        previous_pdf=previous, build_report=build_report_path(),
        contact_sheet=sheet, reviewed_by="agent", reviewed_at="2026-11-10T18:00:00",
    )

    assert calls == [str(pdf)]
    assert "figure-geometry" in {check["id"] for check in report["checks"]}
    assert pages_check.pdf_info(pdf)["Pages"] == "6"
