"""Task 7: charts and diagrams are deterministic functions of stored data."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from PIL import Image

from bookify.errors import BookifyError
from bookify.figures import charts, diagrams
from bookify.manuscript import model

ROOT = Path(__file__).resolve().parents[1]
SPECIMEN = ROOT / "content" / "specimen.yaml"


def _blocks(manuscript: model.Manuscript) -> list[dict]:
    return [block for section in manuscript.sections for block in section["blocks"]]


def _chart_block(manuscript: model.Manuscript) -> dict:
    return next(block for block in _blocks(manuscript) if block["type"] == "chart")


def _diagram_block(manuscript: model.Manuscript) -> dict:
    return next(block for block in _blocks(manuscript) if block["type"] == "diagram")


def test_chart_renders_from_stored_values_and_stays_stable(tmp_path: Path) -> None:
    manuscript = model.load(SPECIMEN)
    block = _chart_block(manuscript)

    first = charts.render(block, ROOT, tmp_path)
    second = charts.render(block, ROOT, tmp_path)

    assert first.sha256 == second.sha256
    assert first.bars == (("Alder", "sample-count", 72.0), ("Birch", "sample-count", 64.0), ("Cedar", "sample-count", 58.0))
    assert first.gaps == ()
    assert first.path.is_file() and first.path.suffix == ".svg"
    svg = first.path.read_text()
    assert "<svg" in svg and "<image" not in svg


def test_chart_null_is_a_gap_not_zero(tmp_path: Path) -> None:
    data = yaml.safe_load(SPECIMEN.read_text())
    chart = next(
        block for section in data["sections"] for block in section["blocks"] if block["type"] == "chart"
    )["chart"]
    chart["values"] = [[72], [None], [58]]
    chart["notes"] = "Birch did not report a value."
    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    manuscript = model.load(target, root=ROOT)

    rendered = charts.render(_chart_block(manuscript), ROOT, tmp_path)

    assert rendered.gaps == ("Birch:sample-count",)
    assert len(rendered.bars) == 2
    assert all(value is not None for _, _, value in rendered.bars)


def test_chart_axis_comes_from_data_not_a_hard_coded_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = yaml.safe_load(SPECIMEN.read_text())
    chart = next(
        block for section in data["sections"] for block in section["blocks"] if block["type"] == "chart"
    )
    chart["chart"].pop("axis", None)
    chart["chart"]["values"] = [[120], [300], [450]]
    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    manuscript = model.load(target, root=ROOT)

    import matplotlib.axes

    calls: list[tuple[float, float]] = []
    original = matplotlib.axes.Axes.set_ylim

    def capture(self, lower=None, upper=None, **kwargs):
        if lower is not None and upper is not None:
            calls.append((float(lower), float(upper)))
        return original(self, lower, upper, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "set_ylim", capture)
    charts.render(_chart_block(manuscript), ROOT, tmp_path)

    assert calls and calls[-1][0] <= 0 and calls[-1][1] >= 450


def test_chart_partial_axis_derives_the_missing_bound(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = yaml.safe_load(SPECIMEN.read_text())
    chart_block = next(
        block for section in data["sections"] for block in section["blocks"] if block["type"] == "chart"
    )
    chart_block["chart"].pop("axis", None)
    chart_block["chart"]["values"] = [[120], [300], [450]]
    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    manuscript = model.load(target, root=ROOT)
    block = _chart_block(manuscript)

    import matplotlib.axes

    calls: list[tuple[float, float]] = []
    original = matplotlib.axes.Axes.set_ylim

    def capture(self, lower=None, upper=None, **kwargs):
        if lower is not None and upper is not None:
            calls.append((float(lower), float(upper)))
        return original(self, lower, upper, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "set_ylim", capture)
    block["chart"]["axis"] = {"min": 0}
    charts.render(block, ROOT, tmp_path)
    assert calls[-1][0] == 0 and calls[-1][1] >= 450

    calls.clear()
    block["chart"]["axis"] = {"max": 500}
    charts.render(block, ROOT, tmp_path)
    assert calls[-1][0] <= 0 and calls[-1][1] == 500


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_chart_render_rejects_non_finite_values(tmp_path: Path, value: float) -> None:
    manuscript = model.load(SPECIMEN)
    block = json.loads(json.dumps(_chart_block(manuscript)))
    block["chart"]["values"] = [[value], [64], [58]]

    with pytest.raises(BookifyError) as error:
        charts.render(block, ROOT, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_diagram_renders_ceTZ_from_geometry_and_stays_stable(tmp_path: Path) -> None:
    manuscript = model.load(SPECIMEN)
    block = _diagram_block(manuscript)

    first = diagrams.render(block, tmp_path)
    second = diagrams.render(block, tmp_path)

    assert first.sha256 == second.sha256
    assert "Collect" in first.snippet and "Review" in first.snippet
    assert "from: \"n-observe\"" in first.snippet
    assert first.path.is_file()
    assert first.path.read_text().startswith('#import "/typst/cetz/diagram.typ": diagram')


def _diagram_pdf(block: dict, tmp_path: Path, name: str) -> tuple[Path, str]:
    from helpers import compile_typ

    rendered = diagrams.render(block, tmp_path)
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/cetz/diagram.typ": diagram\n'
        "#show: book_base\n"
        '#set page(paper: "a4", margin: 40pt)\n'
        f"{rendered.snippet}\n"
    )
    return compile_typ(source, name), rendered.snippet


def test_diagram_presets_edges_and_groups_all_render(tmp_path: Path) -> None:
    manuscript = model.load(SPECIMEN)
    base = json.loads(json.dumps(_diagram_block(manuscript)))
    base["diagram"]["edges"] = [
        {"from": "n-observe", "to": "n-interpret", "kind": "line"},
        {"from": "n-observe", "to": "n-respond", "kind": "arrow"},
        {"from": "n-respond", "to": "n-observe", "kind": "arrow"},
    ]
    base["diagram"]["groups"] = [
        {"id": "g-read", "label": "Read the signal", "nodes": ["n-observe", "n-interpret"]},
        {"id": "g-act", "label": "Act on it", "nodes": ["n-respond"]},
    ]

    process_pdf, snippet = _diagram_pdf(base, tmp_path, "diagram-process")
    assert 'preset: "process"' in snippet
    assert 'kind: "line"' in snippet
    assert "Read the signal" in snippet and "Act on it" in snippet
    text = subprocess.run(["pdftotext", str(process_pdf), "-"], capture_output=True, text=True, check=True).stdout
    for label in ("Collect", "Label", "Review", "Read the signal", "Act on it", "feedback"):
        assert label in text

    model_block = json.loads(json.dumps(base))
    model_block["diagram"]["preset"] = "model"
    model_pdf, model_snippet = _diagram_pdf(model_block, tmp_path, "diagram-model")
    assert 'preset: "model"' in model_snippet
    assert model_pdf.read_bytes() != process_pdf.read_bytes()
    model_text = subprocess.run(["pdftotext", str(model_pdf), "-"], capture_output=True, text=True, check=True).stdout
    for label in ("Collect", "Label", "Review", "Read the signal", "Act on it"):
        assert label in model_text


def _page_ink(pdf: Path, name: str) -> int:
    prefix = pdf.with_name(name)
    subprocess.run(["pdftoppm", "-png", "-r", "100", "-singlefile", str(pdf), str(prefix)], check=True)
    with Image.open(f"{prefix}.png") as source:
        image = source.convert("L")
    pixels = image.load()
    width, height = image.size
    return sum(1 for y in range(height) for x in range(width) if pixels[x, y] < 250)


def test_non_adjacent_diagram_edge_is_actually_drawn(tmp_path: Path) -> None:
    manuscript = model.load(SPECIMEN)
    adjacent = json.loads(json.dumps(_diagram_block(manuscript)))
    adjacent["diagram"]["edges"] = [{"from": "n-observe", "to": "n-interpret", "kind": "arrow"}]
    skipped = json.loads(json.dumps(adjacent))
    skipped["diagram"]["edges"].append({"from": "n-observe", "to": "n-respond", "kind": "arrow"})

    adjacent_pdf, _ = _diagram_pdf(adjacent, tmp_path, "diagram-no-skip")
    skipped_pdf, _ = _diagram_pdf(skipped, tmp_path, "diagram-with-skip")

    assert _page_ink(skipped_pdf, "skip-ink") > _page_ink(adjacent_pdf, "adjacent-ink"), (
        "the skip edge must add visible ink; silently dropping it would leave the pages identical"
    )


def test_diagram_line_edge_differs_from_arrow(tmp_path: Path) -> None:
    manuscript = model.load(SPECIMEN)
    arrow = json.loads(json.dumps(_diagram_block(manuscript)))
    arrow["diagram"]["edges"] = [{"from": "n-observe", "to": "n-interpret", "kind": "arrow"}]
    line = json.loads(json.dumps(arrow))
    line["diagram"]["edges"] = [{"from": "n-observe", "to": "n-interpret", "kind": "line"}]

    arrow_pdf, _ = _diagram_pdf(arrow, tmp_path, "diagram-arrow-edge")
    line_pdf, _ = _diagram_pdf(line, tmp_path, "diagram-line-edge")

    assert arrow_pdf.read_bytes() != line_pdf.read_bytes()


def test_diagram_self_edge_is_rejected(tmp_path: Path) -> None:
    data = json.loads(json.dumps({"sections": [{"blocks": [_diagram_block(model.load(SPECIMEN))]}]}))
    import yaml

    block = data["sections"][0]["blocks"][0]
    block["diagram"]["edges"].append({"from": "n-observe", "to": "n-observe", "kind": "arrow"})
    manuscript_data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "self-edge",
        "metadata": {"title": "Self edge", "languages": ["en"]},
        "sections": [
            {"id": "sec-a", "title": "A", "blocks": [block]},
        ],
    }
    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(manuscript_data, sort_keys=False, allow_unicode=True))

    with pytest.raises(BookifyError) as error:
        model.load(target, root=ROOT)

    assert error.value.code == "SCHEMA_INVALID"
    assert "self edge" in error.value.message


def test_diagram_rejects_an_edge_to_an_unknown_node(tmp_path: Path) -> None:
    manuscript = model.load(SPECIMEN)
    block = json.loads(json.dumps(_diagram_block(manuscript)))
    block["diagram"]["edges"].append({"from": "n-observe", "to": "n-missing"})

    with pytest.raises(BookifyError) as error:
        diagrams.render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_cli_figures_render_writes_a_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from bookify.toolchain.cli import main

    assert main(["figures", "render", "--manuscript", str(SPECIMEN), "--out", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert {item["kind"] for item in payload["figures"]} == {"chart", "diagram"}
    for item in payload["figures"]:
        assert (ROOT / item["path"]).is_file() if not Path(item["path"]).is_absolute() else Path(item["path"]).is_file()
