"""Tasks 24-27: the additive catalogue contract, one validation boundary and provenance.

All catalogue contract tests live in this dedicated file so the shared renderer
tests stay untouched. Payload examples here are the executable form of
`.opencode/catalogue-contracts.md`.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from bookify.errors import BookifyError
from bookify.figures import checks, presets
from bookify.manuscript import model, schema

ROOT = Path(__file__).resolve().parents[1]
SPECIMEN = ROOT / "content" / "specimen.yaml"
EXAMPLE = ROOT / "schemas" / "examples" / "specimen.yaml"
NEGATIVE = ROOT / "schemas" / "examples" / "negative"


def manuscript(blocks: list[dict], identifier: str = "contract-fixture") -> dict:
    return {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": identifier,
        "metadata": {"title": "Contract fixture", "languages": ["en", "vi", "ja"]},
        "sections": [{"id": "sec-contract", "title": "Contract", "blocks": blocks}],
    }


def write_manuscript(tmp_path: Path, blocks: list[dict], name: str = "manuscript.yaml") -> Path:
    target = tmp_path / name
    target.write_text(yaml.safe_dump(manuscript(blocks), sort_keys=False, allow_unicode=True))
    return target


def chart_block(kind: str, **overrides) -> dict:
    chart = copy.deepcopy(VALID_CHARTS[kind])
    chart.update(overrides)
    for key, value in overrides.items():
        if value is None:
            chart.pop(key, None)
    return {"id": f"b-{kind.replace('_', '-')}", "type": "chart", "caption": f"{kind} fixture.", "chart": chart}


def diagram_block(preset: str, **overrides) -> dict:
    diagram = copy.deepcopy(VALID_DIAGRAMS[preset])
    diagram.update(overrides)
    for key, value in overrides.items():
        if value is None:
            diagram.pop(key, None)
    return {
        "id": f"b-{preset.replace('_', '-')}",
        "type": "diagram",
        "caption": f"{preset} fixture.",
        "note": "Illustrative diagram authored for the catalogue; not traced.",
        "diagram": diagram,
    }


SYNTHETIC = "Synthetic values authored for the catalogue; not measurements."

VALID_CHARTS: dict[str, dict] = {
    "grouped_bar": {
        "kind": "grouped_bar",
        "categories": ["Alder", "Birch", "Cedar"],
        "series": [{"id": "sample-count", "label": "Samples recorded"}],
        "values": [[72], [64], [58]],
        "axis": {"unit": "%", "min": 0, "max": 100},
        "source": {"sourceId": "example-source", "page": 28},
        "verification": "inferred",
        "notes": "Values approximated from the printed bars; not exact survey figures.",
    },
    "bar": {
        "kind": "bar",
        "categories": ["Q1", "Q2", "Q3"],
        "series": [{"id": "delta", "label": "Change"}],
        "values": [[4], [-2], [6]],
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "stacked_bar": {
        "kind": "stacked_bar",
        "categories": ["North", "South", "East"],
        "series": [{"id": "base", "label": "Base"}, {"id": "extra", "label": "Extra"}],
        "values": [[3, 2], [4, 1], [2, 5]],
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "line": {
        "kind": "line",
        "categories": ["Jan", "Feb", "Mar", "Apr"],
        "series": [{"id": "trend", "label": "Trend"}],
        "values": [[1.2], [1.5], [1.8], [2.1]],
        "axis": {"unit": "index"},
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "area": {
        "kind": "area",
        "categories": ["A", "B", "C"],
        "series": [{"id": "first", "label": "First"}, {"id": "second", "label": "Second"}],
        "values": [[2, 1], [3, 2], [2.5, 1.5]],
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "scatter": {
        "kind": "scatter",
        "series": [{"id": "group-a", "label": "Group A"}, {"id": "group-b", "label": "Group B"}],
        "points": [
            [[1.0, 2.5], [2.0, 3.1], [3.5, 4.0]],
            [[1.2, 1.8], [2.6, 2.9], [4.1, 3.6]],
        ],
        "xAxis": {"unit": "hours", "min": 0, "max": 6},
        "axis": {"unit": "score"},
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "bubble": {
        "kind": "bubble",
        "series": [{"id": "group-a", "label": "Group A"}, {"id": "group-b", "label": "Group B"}],
        "points": [
            [[1.0, 2.5, 4], [2.0, 3.1, 6], [3.5, 4.0, 8]],
            [[1.2, 1.8, 5], [2.6, 2.9, 7], [4.1, 3.6, 9]],
        ],
        "xAxis": {"unit": "hours", "min": 0, "max": 6},
        "axis": {"unit": "score"},
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "histogram": {
        "kind": "histogram",
        "bins": [0, 10, 20, 30, 40],
        "series": [{"id": "readings", "label": "Readings"}],
        "counts": [[3], [7], [4], [1]],
        "axis": {"unit": "count", "min": 0},
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "box": {
        "kind": "box",
        "categories": ["Group A", "Group B"],
        "series": [{"id": "score", "label": "Score"}],
        "stats": [[[2, 4, 5, 7, 9]], [[1, 3, 4, 6, 8]]],
        "axis": {"unit": "score", "min": 0, "max": 10},
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "violin": {
        "kind": "violin",
        "categories": ["Group A", "Group B"],
        "series": [{"id": "score", "label": "Score"}],
        "samples": [[[1, 2, 3, 4, 5]], [[2, 3, 4, 5, 6]]],
        "axis": {"unit": "score", "min": 0, "max": 7},
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "heatmap": {
        "kind": "heatmap",
        "categories": ["Row one", "Row two"],
        "series": [{"id": "left", "label": "Left"}, {"id": "right", "label": "Right"}],
        "values": [[1, 2], [3, 4]],
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "pie": {
        "kind": "pie",
        "categories": ["Share A", "Share B", "Share C"],
        "series": [{"id": "share", "label": "Share"}],
        "values": [[40], [35], [25]],
        "hole": 0,
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "waterfall": {
        "kind": "waterfall",
        "categories": ["Start", "Gain", "Loss", "End"],
        "series": [{"id": "delta", "label": "Change"}],
        "values": [[40], [12], [-7], [45]],
        "totals": [False, False, False, True],
        "axis": {"unit": "index", "min": 0},
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "radar": {
        "kind": "radar",
        "categories": ["Speed", "Clarity", "Cost", "Reach"],
        "series": [{"id": "current", "label": "Current"}, {"id": "target", "label": "Target"}],
        "values": [[4, 5], [3, 4], [5, 3], [2, 4]],
        "axis": {"unit": "score", "min": 0, "max": 5},
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
    "error_bar": {
        "kind": "error_bar",
        "categories": ["Group A", "Group B"],
        "series": [{"id": "score", "label": "Score"}],
        "values": [[5], [6]],
        "errors": [[0.5], [0.8]],
        "axis": {"unit": "score", "min": 0, "max": 8},
        "verification": "synthetic",
        "notes": SYNTHETIC,
    },
}

VALID_DIAGRAMS: dict[str, dict] = {
    "process": {
        "preset": "process",
        "synthetic": True,
        "nodes": [
            {"id": "n-observe", "label": "Observe", "sub": "signal"},
            {"id": "n-interpret", "label": "Interpret", "sub": "setting"},
            {"id": "n-respond", "label": "Respond", "sub": "action"},
        ],
        "edges": [
            {"from": "n-observe", "to": "n-interpret"},
            {"from": "n-interpret", "to": "n-respond"},
            {"from": "n-respond", "to": "n-observe"},
        ],
        "groups": [{"id": "g-turn", "label": "One turn", "nodes": ["n-observe", "n-interpret", "n-respond"]}],
    },
    "model": {
        "preset": "model",
        "synthetic": True,
        "nodes": [
            {"id": "n-outer", "label": "Read the signal"},
            {"id": "n-inner", "label": "Read the setting"},
        ],
        "edges": [{"from": "n-outer", "to": "n-inner"}],
    },
    "cycle": {
        "preset": "cycle",
        "synthetic": True,
        "nodes": [
            {"id": "n-plan", "label": "Plan"},
            {"id": "n-do", "label": "Do"},
            {"id": "n-check", "label": "Check"},
            {"id": "n-act", "label": "Act"},
        ],
        "edges": [
            {"from": "n-plan", "to": "n-do"},
            {"from": "n-do", "to": "n-check"},
            {"from": "n-check", "to": "n-act"},
            {"from": "n-act", "to": "n-plan"},
        ],
    },
    "hierarchy": {
        "preset": "hierarchy",
        "synthetic": True,
        "nodes": [
            {"id": "n-root", "label": "Protocol"},
            {"id": "n-read", "label": "Read"},
            {"id": "n-act", "label": "Act"},
            {"id": "n-record", "label": "Record"},
        ],
        "edges": [
            {"from": "n-root", "to": "n-read"},
            {"from": "n-root", "to": "n-act"},
            {"from": "n-read", "to": "n-record"},
        ],
    },
    "decision_tree": {
        "preset": "decision_tree",
        "synthetic": True,
        "nodes": [
            {"id": "n-question", "label": "Signal seen?"},
            {"id": "n-yes", "label": "Read the setting"},
            {"id": "n-no", "label": "Record the gap"},
        ],
        "edges": [
            {"from": "n-question", "to": "n-yes", "label": "yes"},
            {"from": "n-question", "to": "n-no", "label": "no"},
        ],
    },
    "network": {
        "preset": "network",
        "synthetic": True,
        "nodes": [
            {"id": "n-a", "label": "Signal"},
            {"id": "n-b", "label": "Setting"},
            {"id": "n-c", "label": "Warrant"},
        ],
        "edges": [
            {"from": "n-a", "to": "n-b"},
            {"from": "n-b", "to": "n-c"},
            {"from": "n-c", "to": "n-a"},
        ],
    },
    "timeline": {
        "preset": "timeline",
        "synthetic": True,
        "events": [
            {"id": "ev-one", "label": "First signal", "sub": "observation", "when": "Step 1"},
            {"id": "ev-two", "label": "Reading", "when": "Step 2"},
            {"id": "ev-three", "label": "Response", "sub": "action", "when": "Step 3"},
        ],
    },
    "matrix": {
        "preset": "matrix",
        "synthetic": True,
        "rows": ["Signal", "Setting"],
        "columns": ["Question", "Failure mode"],
        "cells": [
            ["What happened?", "Reading the gesture alone"],
            ["What does it mean here?", "Assuming your own default"],
        ],
    },
    "venn": {
        "preset": "venn",
        "synthetic": True,
        "sets": [{"id": "set-a", "label": "Observed"}, {"id": "set-b", "label": "Inferred"}],
        "overlaps": [{"id": "ov-both", "label": "Shared reading", "sets": ["set-a", "set-b"]}],
    },
    "swimlane": {
        "preset": "swimlane",
        "synthetic": True,
        "lanes": [{"id": "lane-reader", "label": "Reader"}, {"id": "lane-source", "label": "Source"}],
        "stages": [{"id": "stage-one", "label": "Signal"}, {"id": "stage-two", "label": "Setting"}],
        "nodes": [
            {"id": "n-observe", "label": "Observe", "lane": "lane-reader", "stage": "stage-one"},
            {"id": "n-record", "label": "Record", "lane": "lane-source", "stage": "stage-two"},
        ],
    },
}


# --- Task 24: additive schema -------------------------------------------------

def test_specimen_manuscripts_still_validate() -> None:
    for path in (SPECIMEN, EXAMPLE):
        loaded = model.load(path)
        assert loaded.revision == 1
        assert loaded.id


def test_schema_keeps_version_and_closed_objects() -> None:
    document = schema.load_document()

    assert document["properties"]["schemaVersion"]["const"] == "1.0"
    assert document["additionalProperties"] is False
    assert document["$defs"]["block"]["additionalProperties"] is False
    assert "unevaluatedProperties" in document["$defs"]["block"]
    assert document["$defs"]["chartBlock"]["properties"]["chart"]["additionalProperties"] is False
    assert document["$defs"]["diagramBlock"]["properties"]["diagram"]["additionalProperties"] is False


def test_schema_names_exactly_the_fifteen_chart_families() -> None:
    document = schema.load_document()
    kinds = document["$defs"]["chartBlock"]["properties"]["chart"]["properties"]["kind"]["enum"]

    assert kinds == list(checks.CHART_KINDS)
    assert len(kinds) == 15


def test_schema_names_exactly_the_ten_diagram_presets() -> None:
    document = schema.load_document()
    presets_document = document["$defs"]["diagramBlock"]["properties"]["diagram"]["properties"]["preset"]["enum"]

    assert presets_document == list(checks.DIAGRAM_PRESETS)
    assert len(presets_document) == 10


@pytest.mark.parametrize("kind", sorted(VALID_CHARTS))
def test_every_chart_payload_example_validates(tmp_path: Path, kind: str) -> None:
    loaded = model.load(write_manuscript(tmp_path, [chart_block(kind)]), root=ROOT)

    assert loaded.sections[0]["blocks"][0]["chart"]["kind"] == kind


@pytest.mark.parametrize("preset", sorted(VALID_DIAGRAMS))
def test_every_diagram_payload_example_validates(tmp_path: Path, preset: str) -> None:
    loaded = model.load(write_manuscript(tmp_path, [diagram_block(preset)]), root=ROOT)

    assert loaded.sections[0]["blocks"][0]["diagram"]["preset"] == preset


NEGATIVE_FIXTURES = (
    "catalogue-chart-synthetic-source.yaml",
    "catalogue-chart-payload-cap.yaml",
    "catalogue-diagram-unknown-preset.yaml",
    "catalogue-diagram-synthetic-anchors.yaml",
)


@pytest.mark.parametrize("name", NEGATIVE_FIXTURES)
def test_catalogue_negative_fixtures_fail_with_schema_invalid(name: str) -> None:
    with pytest.raises(BookifyError) as error:
        model.load(NEGATIVE / name)

    assert error.value.code == "SCHEMA_INVALID", f"{name}: {error.value.message}"


def _fixed(name: str, data: dict) -> dict:
    chart = next(block for section in data["sections"] for block in section["blocks"] if block["type"] == "chart")
    diagram = next(block for section in data["sections"] for block in section["blocks"] if block["type"] == "diagram")
    if name == "catalogue-chart-synthetic-source.yaml":
        chart["chart"].pop("source", None)
    elif name == "catalogue-chart-payload-cap.yaml":
        chart["chart"]["categories"] = chart["chart"]["categories"][:8]
        chart["chart"]["values"] = chart["chart"]["values"][:8]
    elif name == "catalogue-diagram-unknown-preset.yaml":
        diagram["diagram"]["preset"] = "process"
    elif name == "catalogue-diagram-synthetic-anchors.yaml":
        diagram.pop("sourceAnchors", None)
    return data


@pytest.mark.parametrize("name", NEGATIVE_FIXTURES)
def test_each_negative_fixture_has_a_passing_control(tmp_path: Path, name: str) -> None:
    data = _fixed(name, yaml.safe_load((NEGATIVE / name).read_text()))
    target = tmp_path / name
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    loaded = model.load(target, root=ROOT)

    assert loaded.revision == 1


# --- Task 25: registries and one validation boundary --------------------------

def test_chart_registry_has_every_family_with_its_caps() -> None:
    assert tuple(presets.CHART_PRESETS) == checks.CHART_KINDS
    assert len(presets.CHART_PRESETS) == 15
    assert presets.CHART_PRESETS["pie"].max_categories == 8
    assert presets.CHART_PRESETS["heatmap"].max_categories == 12
    assert presets.CHART_PRESETS["stacked_bar"].min_series == 2
    assert presets.CHART_PRESETS["scatter"].max_series == 3
    assert {preset.shape for preset in presets.CHART_PRESETS.values()} == {
        "matrix", "points", "histogram", "box", "samples", "pie",
    }


def test_diagram_registry_has_every_preset_with_its_caps() -> None:
    assert tuple(presets.DIAGRAM_PRESETS) == checks.DIAGRAM_PRESETS
    assert len(presets.DIAGRAM_PRESETS) == 10
    assert presets.DIAGRAM_PRESETS["process"].max_nodes == 6
    assert presets.DIAGRAM_PRESETS["network"].max_nodes == 10
    assert presets.DIAGRAM_PRESETS["timeline"].max_events == 8
    assert presets.DIAGRAM_PRESETS["venn"].max_overlaps == 4
    assert presets.DIAGRAM_PRESETS["swimlane"].max_stages == 6


@pytest.mark.parametrize("kind", sorted(VALID_CHARTS))
def test_each_chart_payload_passes_the_validation_boundary(kind: str) -> None:
    block = chart_block(kind)

    validated = checks.validate_chart(block)

    assert validated["kind"] == kind
    assert validated is not block["chart"], "the boundary returns a mapping, not the caller's object"


@pytest.mark.parametrize("preset", sorted(VALID_DIAGRAMS))
def test_each_diagram_payload_passes_the_validation_boundary(preset: str) -> None:
    block = diagram_block(preset)

    validated = checks.validate_diagram(block)

    assert validated["preset"] == preset


def _chart(kind: str, **overrides) -> dict:
    return chart_block(kind, **overrides)


def _diagram(preset: str, **overrides) -> dict:
    return diagram_block(preset, **overrides)


def _nodes(count: int) -> list[dict]:
    return [{"id": f"n-{index}", "label": f"N{index}"} for index in range(count)]


def _series(count: int) -> list[dict]:
    return [{"id": f"s-{index}", "label": f"S{index}"} for index in range(count)]


CHART_VIOLATIONS = [
    ("unknown-kind", {"id": "b-unknown", "type": "chart", "caption": "x", "chart": {**VALID_CHARTS["bar"], "kind": "sankey"}}),
    ("grouped-bar-five-series", _chart(
        "grouped_bar",
        series=[{"id": f"s-{index}", "label": f"S{index}"} for index in range(5)],
        values=[[1, 2, 3, 4, 5]] * 3,
        verification="synthetic",
        notes=SYNTHETIC,
        source=None,
    )),
    ("bar-two-series", _chart(
        "bar",
        series=[{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
        values=[[1, 2], [3, 4], [5, 6]],
    )),
    ("stacked-bar-negative", _chart("stacked_bar", values=[[3, 2], [4, -1], [2, 5]])),
    ("stacked-bar-one-series", _chart(
        "stacked_bar",
        series=_series(1),
        values=[[3], [4], [2]],
    )),
    ("stacked-bar-five-series", _chart(
        "stacked_bar",
        series=_series(5),
        values=[[1, 2, 3, 4, 5], [2, 3, 4, 5, 1], [3, 4, 5, 1, 2]],
    )),
    ("line-five-series", _chart(
        "line",
        series=_series(5),
        values=[[1, 2, 3, 4, 5]] * 4,
    )),
    ("area-five-series", _chart(
        "area",
        series=_series(5),
        values=[[1, 2, 3, 4, 5]] * 3,
    )),
    ("scatter-four-series", _chart(
        "scatter",
        series=_series(4),
        points=[[[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]]] * 4,
    )),
    ("bubble-four-series", _chart(
        "bubble",
        series=_series(4),
        points=[[[1.0, 2.0, 1], [2.0, 3.0, 2], [3.0, 4.0, 3]]] * 4,
    )),
    ("histogram-four-series", _chart(
        "histogram",
        series=_series(4),
        counts=[[1, 1, 1, 1]] * 4,
    )),
    ("box-four-series", _chart(
        "box",
        series=_series(4),
        stats=[[[1, 2, 3, 4, 5]]] * 2,
    )),
    ("violin-four-series", _chart(
        "violin",
        series=_series(4),
        samples=[[[1, 2, 3, 4, 5]]] * 2,
    )),
    ("error-bar-five-series", _chart(
        "error_bar",
        series=_series(5),
        values=[[1, 1, 1, 1, 1], [2, 2, 2, 2, 2]],
        errors=[[0.5, 0.5, 0.5, 0.5, 0.5], [0.5, 0.5, 0.5, 0.5, 0.5]],
    )),
    ("area-negative", _chart("area", values=[[2, 1], [-3, 2], [2.5, 1.5]])),
    ("line-null-without-note", _chart("line", values=[[1.2], [None], [1.8], [2.1]], notes=None)),
    ("heatmap-null", _chart("heatmap", values=[[1, None], [3, 4]])),
    ("scatter-two-points", _chart("scatter", points=[[[1.0, 2.5], [2.0, 3.1]], [[1.2, 1.8], [2.6, 2.9]]])),
    ("scatter-points-missing", _chart("scatter", points=None)),
    ("bubble-zero-size", _chart("bubble", points=[[[1.0, 2.5, 0], [2.0, 3.1, 6], [3.5, 4.0, 8]], [[1.2, 1.8, 5], [2.6, 2.9, 7], [4.1, 3.6, 9]]])),
    ("histogram-bins-not-increasing", _chart("histogram", bins=[0, 20, 10, 30, 40])),
    ("histogram-length-mismatch", _chart("histogram", counts=[[3], [7], [4]])),
    ("histogram-negative-count", _chart("histogram", counts=[[3], [-7], [4], [1]])),
    ("histogram-fractional-count", _chart("histogram", counts=[[3], [7.5], [4], [1]])),
    ("box-summary-order", _chart("box", stats=[[[2, 7, 5, 4, 9]], [[1, 3, 4, 6, 8]]])),
    ("violin-too-few-samples", _chart("violin", samples=[[[1, 2, 3, 4]], [[2, 3, 4, 5, 6]]])),
    ("violin-missing-notes", _chart("violin", notes=None)),
    ("pie-too-few-categories", _chart("pie", categories=["Only"], values=[[1]], hole=0)),
    ("pie-zero-sum", _chart("pie", values=[[0], [0], [0]])),
    ("pie-hole-too-large", _chart("pie", hole=0.9)),
    ("waterfall-totals-length", _chart("waterfall", totals=[False, False, True])),
    ("waterfall-wrong-total", _chart("waterfall", values=[[40], [12], [-7], [50]])),
    ("radar-negative", _chart("radar", values=[[4, 5], [3, -4], [5, 3], [2, 4]])),
    ("error-bar-shape", _chart("error_bar", errors=[[0.5]])),
    ("error-bar-negative", _chart("error_bar", errors=[[-0.5], [0.8]])),
    ("error-bar-null-with-value", _chart("error_bar", errors=[[None], [0.8]])),
    ("error-bar-error-at-null-value", _chart(
        "error_bar", values=[[None], [6]], errors=[[0.5], [0.8]], notes="Q1 was not reported.",
    )),
    ("unknown-payload-key", _chart("bar", hole=0.3)),
    ("duplicate-series", _chart(
        "line",
        series=[{"id": "same", "label": "A"}, {"id": "same", "label": "B"}],
        values=[[72, 64], [64, 58], [58, 60], [60, 62]],
    )),
    ("axis-min-not-below-max", _chart("bar", axis={"min": 10, "max": 0})),
    ("value-outside-axis", _chart("bar", axis={"min": 0, "max": 3})),
    ("non-finite-value", _chart("bar", values=[[float("inf")], [-2], [6]])),
    ("synthetic-with-source", _chart(
        "bar",
        verification="synthetic",
        notes=SYNTHETIC,
        source={"sourceId": "example-source", "page": 28},
    )),
    ("synthetic-without-notes", _chart("bar", verification="synthetic", notes=None)),
    ("verified-without-source", _chart("bar", verification="verified", source=None)),
]


@pytest.mark.parametrize("name, block", CHART_VIOLATIONS, ids=[name for name, _ in CHART_VIOLATIONS])
def test_chart_violations_are_rejected(name: str, block: dict) -> None:
    with pytest.raises(BookifyError) as error:
        checks.validate_chart(block)

    assert error.value.code == "SCHEMA_INVALID", f"{name}: {error.value.message}"


@pytest.mark.parametrize("kind", ["bar", "line"])
def test_chart_null_with_a_note_is_the_documented_gap(kind: str) -> None:
    block = _chart(kind)
    if kind == "line":
        block["chart"]["values"] = [[1.2], [None], [1.8], [2.1]]
        block["chart"]["notes"] = "February was not reported."
    else:
        block["chart"]["values"] = [[4], [None], [6]]
        block["chart"]["notes"] = "Q2 was not reported."

    assert checks.validate_chart(block)


def test_synthetic_chart_with_source_anchor_is_rejected() -> None:
    block = _chart("bar", verification="synthetic", notes=SYNTHETIC, source=None)
    block["sourceAnchors"] = [{"sourceId": "example-source", "page": 1}]

    with pytest.raises(BookifyError) as error:
        checks.validate_chart(block)

    assert error.value.code == "SCHEMA_INVALID"
    assert "sourceAnchors" in error.value.message


def test_japanese_chart_label_fails_with_glyph_missing() -> None:
    block = _chart("bar")
    block["chart"]["categories"][0] = "四半期"

    with pytest.raises(BookifyError) as error:
        checks.validate_chart(block)

    assert error.value.code == "GLYPH_MISSING"


def test_model_routes_a_chart_through_the_boundary(tmp_path: Path) -> None:
    block = _chart("pie", categories=["Only"], values=[[1]], hole=0)

    with pytest.raises(BookifyError) as error:
        model.load(write_manuscript(tmp_path, [block]), root=ROOT)

    assert error.value.code == "SCHEMA_INVALID"
    assert "categories" in (error.value.locator or "")


def test_model_routes_a_japanese_chart_label_to_glyph_missing(tmp_path: Path) -> None:
    block = _chart("bar")
    block["chart"]["series"][0]["label"] = "変化"

    with pytest.raises(BookifyError) as error:
        model.load(write_manuscript(tmp_path, [block]), root=ROOT)

    assert error.value.code == "GLYPH_MISSING"


DIAGRAM_VIOLATIONS = [
    ("unknown-preset", {"id": "b-unknown", "type": "diagram", "caption": "x", "note": "Illustrative diagram authored for the catalogue.", "diagram": {**VALID_DIAGRAMS["process"], "preset": "flowchart"}}),
    ("process-too-many-nodes", _diagram(
        "process",
        nodes=[{"id": f"n-{index}", "label": f"N{index}"} for index in range(7)],
        edges=[],
    )),
    ("model-one-node", _diagram("model", nodes=_nodes(1), edges=[])),
    ("model-seven-nodes", _diagram("model", nodes=_nodes(7), edges=[])),
    ("cycle-two-nodes", _diagram("cycle", nodes=_nodes(2), edges=[])),
    ("cycle-nine-nodes", _diagram("cycle", nodes=_nodes(9), edges=[])),
    ("hierarchy-one-node", _diagram("hierarchy", nodes=_nodes(1), edges=[])),
    ("hierarchy-ten-nodes", _diagram("hierarchy", nodes=_nodes(10), edges=[])),
    ("decision-tree-one-node", _diagram("decision_tree", nodes=_nodes(1), edges=[])),
    ("decision-tree-ten-nodes", _diagram("decision_tree", nodes=_nodes(10), edges=[])),
    ("network-two-nodes", _diagram("network", nodes=_nodes(2), edges=[])),
    ("network-eleven-nodes", _diagram("network", nodes=_nodes(11), edges=[])),
    ("timeline-nine-events", _diagram(
        "timeline",
        events=[
            {"id": f"ev-{index}", "label": f"E{index}", "when": f"Step {index}"}
            for index in range(9)
        ],
    )),
    ("matrix-one-row", _diagram("matrix", rows=["Only"], columns=["A", "B"], cells=[])),
    ("matrix-five-rows", _diagram(
        "matrix", rows=["A", "B", "C", "D", "E"], columns=["A", "B"], cells=[],
    )),
    ("matrix-one-column", _diagram("matrix", rows=["A", "B"], columns=["Only"], cells=[])),
    ("matrix-five-columns", _diagram(
        "matrix", rows=["A", "B"], columns=["A", "B", "C", "D", "E"], cells=[],
    )),
    ("venn-one-set", _diagram(
        "venn", sets=[{"id": "set-a", "label": "A"}], overlaps=[],
    )),
    ("venn-four-sets", _diagram(
        "venn",
        sets=[{"id": f"set-{index}", "label": f"S{index}"} for index in range(4)],
        overlaps=[],
    )),
    ("venn-five-overlaps", _diagram(
        "venn",
        overlaps=[
            {"id": f"ov-{index}", "label": f"O{index}", "sets": ["set-a", "set-b"]}
            for index in range(5)
        ],
    )),
    ("swimlane-one-lane", _diagram(
        "swimlane", lanes=[{"id": "lane-only", "label": "Only"}], nodes=[],
    )),
    ("swimlane-five-lanes", _diagram(
        "swimlane",
        lanes=[{"id": f"lane-{index}", "label": f"L{index}"} for index in range(5)],
        nodes=[],
    )),
    ("swimlane-one-stage", _diagram(
        "swimlane", stages=[{"id": "stage-only", "label": "Only"}], nodes=[],
    )),
    ("swimlane-seven-stages", _diagram(
        "swimlane",
        stages=[{"id": f"stage-{index}", "label": f"S{index}"} for index in range(7)],
        nodes=[],
    )),
    ("cycle-broken-ring", _diagram("cycle", edges=[
        {"from": "n-plan", "to": "n-do"},
        {"from": "n-do", "to": "n-check"},
        {"from": "n-check", "to": "n-plan"},
        {"from": "n-act", "to": "n-plan"},
    ])),
    ("hierarchy-two-roots", _diagram("hierarchy", edges=[
        {"from": "n-read", "to": "n-record"},
        {"from": "n-act", "to": "n-record"},
    ])),
    ("hierarchy-two-parents", _diagram("hierarchy", edges=[
        {"from": "n-root", "to": "n-read"},
        {"from": "n-root", "to": "n-act"},
        {"from": "n-read", "to": "n-record"},
        {"from": "n-act", "to": "n-record"},
    ])),
    ("hierarchy-groups", _diagram("hierarchy", groups=[{"id": "g", "label": "G", "nodes": ["n-root"]}])),
    ("decision-tree-missing-branch-label", _diagram("decision_tree", edges=[
        {"from": "n-question", "to": "n-yes", "label": "yes"},
        {"from": "n-question", "to": "n-no"},
    ])),
    ("network-groups", _diagram("network", groups=[{"id": "g", "label": "G", "nodes": ["n-a"]}])),
    ("timeline-too-few-events", _diagram("timeline", events=[{"id": "ev-one", "label": "One", "when": "1"}])),
    ("timeline-with-nodes", _diagram("timeline", nodes=[{"id": "n-a", "label": "A"}])),
    ("matrix-incomplete-grid", _diagram("matrix", cells=[["What happened?", "Reading the gesture alone"]])),
    ("venn-unknown-set", _diagram("venn", overlaps=[{"id": "ov", "label": "Shared", "sets": ["set-a", "set-missing"]}])),
    ("venn-duplicate-region", _diagram("venn", overlaps=[
        {"id": "ov-one", "label": "Shared", "sets": ["set-a", "set-b"]},
        {"id": "ov-two", "label": "Shared again", "sets": ["set-b", "set-a"]},
    ])),
    ("swimlane-duplicate-cell", _diagram("swimlane", nodes=[
        {"id": "n-one", "label": "One", "lane": "lane-reader", "stage": "stage-one"},
        {"id": "n-two", "label": "Two", "lane": "lane-reader", "stage": "stage-one"},
    ])),
    ("swimlane-unknown-lane", _diagram("swimlane", nodes=[
        {"id": "n-one", "label": "One", "lane": "lane-missing", "stage": "stage-one"},
    ])),
    ("swimlane-edges", _diagram("swimlane", edges=[])),
    ("swimlane-node-without-cell", _diagram("swimlane", nodes=[{"id": "n-one", "label": "One"}])),
    ("self-edge", _diagram("process", edges=[{"from": "n-observe", "to": "n-observe"}])),
    ("duplicate-node", _diagram("process", nodes=[
        {"id": "n-observe", "label": "Observe"},
        {"id": "n-observe", "label": "Again"},
        {"id": "n-respond", "label": "Respond"},
    ], edges=[])),
    ("missing-endpoint", _diagram("process", edges=[{"from": "n-observe", "to": "n-missing"}])),
    ("cycle-groups", _diagram("cycle", groups=[{"id": "g", "label": "G", "nodes": ["n-plan"]}])),
    ("synthetic-without-note", {**_diagram("process"), "note": ""}),
    ("synthetic-with-anchor", {**_diagram("process"), "sourceAnchors": [{"sourceId": "example-source", "page": 1}]}),
]


@pytest.mark.parametrize("name, block", DIAGRAM_VIOLATIONS, ids=[name for name, _ in DIAGRAM_VIOLATIONS])
def test_diagram_violations_are_rejected(name: str, block: dict) -> None:
    with pytest.raises(BookifyError) as error:
        checks.validate_diagram(block)

    assert error.value.code == "SCHEMA_INVALID", f"{name}: {error.value.message}"


def test_model_routes_a_diagram_through_the_boundary(tmp_path: Path) -> None:
    block = _diagram("cycle", edges=[{"from": "n-plan", "to": "n-do"}])

    with pytest.raises(BookifyError) as error:
        model.load(write_manuscript(tmp_path, [block]), root=ROOT)

    assert error.value.code == "SCHEMA_INVALID"
    assert "ring" in error.value.message


def test_specimen_grouped_bar_process_and_model_stay_valid() -> None:
    loaded = model.load(SPECIMEN)
    blocks = [block for section in loaded.sections for block in section["blocks"]]

    chart = next(block for block in blocks if block["type"] == "chart")
    diagram = next(block for block in blocks if block["type"] == "diagram")
    assert checks.validate_chart(chart)["kind"] == "grouped_bar"
    assert checks.validate_diagram(diagram)["preset"] == "process"

    model_block = copy.deepcopy(diagram)
    model_block["diagram"]["preset"] = "model"
    assert checks.validate_diagram(model_block)["preset"] == "model"


# --- Task 26: synthetic and illustrative provenance wording -------------------

def _provenance_manuscript(tmp_path: Path) -> model.Manuscript:
    synthetic_chart = chart_block("grouped_bar")
    synthetic_chart["id"] = "b-synthetic-chart"
    synthetic_chart["chart"] = {
        **copy.deepcopy(VALID_CHARTS["grouped_bar"]),
        "verification": "synthetic",
        "notes": SYNTHETIC,
    }
    synthetic_chart["chart"].pop("source", None)

    inferred_chart = chart_block("grouped_bar")
    inferred_chart["id"] = "b-inferred-chart"

    synthetic_diagram = diagram_block("process")
    synthetic_diagram["id"] = "b-synthetic-diagram"

    reconstruction = diagram_block("process")
    reconstruction["id"] = "b-reconstruction-diagram"
    reconstruction["confidence"] = "inferred"
    reconstruction["diagram"] = copy.deepcopy(VALID_DIAGRAMS["process"])
    reconstruction["diagram"].pop("synthetic", None)
    reconstruction.pop("note", None)

    return model.load(
        write_manuscript(
            tmp_path,
            [synthetic_chart, inferred_chart, synthetic_diagram, reconstruction],
        ),
        root=ROOT,
    )


def _entries(document, identifier: str) -> dict:
    return next(
        block for section in document["sections"] for block in section["blocks"]
        if block["id"] == identifier
    )


def test_synthetic_chart_caption_and_approximate_flag(tmp_path: Path) -> None:
    from bookify.publish import normalize

    loaded = _provenance_manuscript(tmp_path)
    document = normalize.build(loaded, {"b-synthetic-chart": "/chart.svg", "b-inferred-chart": "/chart.svg"})

    synthetic = _entries(document.data, "b-synthetic-chart")
    inferred = _entries(document.data, "b-inferred-chart")

    assert synthetic["caption"].endswith("Synthetic data.")
    assert synthetic["approximate"] is True
    assert inferred["caption"].endswith("Approximate values.")
    assert "Synthetic data." not in inferred["caption"]


def test_synthetic_wording_is_not_duplicated(tmp_path: Path) -> None:
    from bookify.publish import normalize

    blocks = [{
        **chart_block("grouped_bar"),
        "id": "b-synthetic-chart",
        "caption": "Synthetic data shown for review.",
        "chart": {**VALID_CHARTS["grouped_bar"], "verification": "synthetic", "notes": SYNTHETIC},
    }]
    blocks[0]["chart"].pop("source", None)
    loaded = model.load(write_manuscript(tmp_path, blocks), root=ROOT)

    document = normalize.build(loaded, {"b-synthetic-chart": "/chart.svg"})

    caption = _entries(document.data, "b-synthetic-chart")["caption"]
    assert caption.lower().count("synthetic data") == 1


def test_illustrative_diagram_wording_replaces_reconstruction(tmp_path: Path) -> None:
    from bookify.publish import normalize

    loaded = _provenance_manuscript(tmp_path)
    document = normalize.build(loaded, {"b-synthetic-chart": "/chart.svg", "b-inferred-chart": "/chart.svg"})

    synthetic = _entries(document.data, "b-synthetic-diagram")
    reconstruction = _entries(document.data, "b-reconstruction-diagram")

    assert synthetic["caption"].endswith("Illustrative diagram.")
    assert "Reconstruction." not in synthetic["caption"]
    assert synthetic["approximate"] is True
    assert reconstruction["caption"].endswith("Reconstruction.")
    assert "Illustrative diagram." not in reconstruction["caption"]


def test_synthetic_provenance_rules_at_the_model_boundary(tmp_path: Path) -> None:
    anchored = chart_block("bar", verification="synthetic", notes=SYNTHETIC)
    anchored["sourceAnchors"] = [{"sourceId": "example-source", "page": 1}]
    with pytest.raises(BookifyError) as error:
        model.load(write_manuscript(tmp_path, [anchored], "anchored.yaml"), root=ROOT)
    assert error.value.code == "SCHEMA_INVALID"

    without_note = {**diagram_block("process"), "note": ""}
    with pytest.raises(BookifyError) as error:
        model.load(write_manuscript(tmp_path, [without_note], "no-note.yaml"), root=ROOT)
    assert error.value.code == "SCHEMA_INVALID"


def test_synthetic_wording_reaches_the_pdf_and_build_warnings(tmp_path: Path) -> None:
    import subprocess

    from bookify.publish import typst_driver

    blocks = [
        {
            **chart_block("grouped_bar"),
            "id": "b-synthetic-chart",
            "caption": "A synthetic chart for provenance review.",
            "chart": {
                **VALID_CHARTS["grouped_bar"],
                "verification": "synthetic",
                "notes": SYNTHETIC,
            },
        },
        {
            **diagram_block("process"),
            "id": "b-synthetic-diagram",
            "caption": "A diagram for provenance review.",
        },
    ]
    blocks[0]["chart"].pop("source", None)
    work = ROOT / ".cache" / "contracts-provenance"
    work.mkdir(parents=True, exist_ok=True)
    manuscript_path = work / "manuscript.yaml"
    manuscript_path.write_text(
        yaml.safe_dump(manuscript(blocks), sort_keys=False, allow_unicode=True)
    )

    result = typst_driver.build(manuscript_path, work / "provenance.pdf", work / "build", offline=True)
    text = subprocess.run(
        ["pdftotext", "-layout", str(result.pdf), "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    normalised = " ".join(text.split())

    assert "Synthetic data." in normalised
    assert "Illustrative diagram." in normalised
    warnings = " ".join(result.report["warnings"])
    assert "b-synthetic-chart" in warnings
    assert "b-synthetic-diagram" in warnings
    assert "approximate or reconstructed" not in warnings
    assert any(
        "b-synthetic-chart" in warning and "synthetic data" in warning
        for warning in result.report["warnings"]
    )
    assert any(
        "b-synthetic-diagram" in warning and "illustrative diagram" in warning
        for warning in result.report["warnings"]
    )


# --- Task 27: coverage for every new chart/diagram label -----------------------

EMOJI = "\U0001F9EA"


def _coverage_case_chart_category() -> list[dict]:
    block = chart_block("bar")
    block["chart"]["categories"][0] += f" {EMOJI}"
    return [block]


def _coverage_case_chart_series_label() -> list[dict]:
    block = chart_block("bar")
    block["chart"]["series"][0]["label"] += f" {EMOJI}"
    return [block]


def _coverage_case_chart_notes() -> list[dict]:
    block = chart_block("bar")
    block["chart"]["notes"] += f" {EMOJI}"
    return [block]


def _coverage_case_chart_axis_unit() -> list[dict]:
    block = chart_block("bar")
    block["chart"]["axis"] = {"unit": f"index {EMOJI}"}
    return [block]


def _coverage_case_diagram_edge_label() -> list[dict]:
    block = diagram_block("process")
    block["diagram"]["edges"][0]["label"] = f"yes {EMOJI}"
    return [block]


def _coverage_case_diagram_event_label() -> list[dict]:
    block = diagram_block("timeline")
    block["diagram"]["events"][0]["label"] += f" {EMOJI}"
    return [block]


def _coverage_case_diagram_event_sub() -> list[dict]:
    block = diagram_block("timeline")
    block["diagram"]["events"][0]["sub"] += f" {EMOJI}"
    return [block]


def _coverage_case_diagram_matrix_row() -> list[dict]:
    block = diagram_block("matrix")
    block["diagram"]["rows"][0] += f" {EMOJI}"
    return [block]


def _coverage_case_diagram_matrix_column() -> list[dict]:
    block = diagram_block("matrix")
    block["diagram"]["columns"][0] += f" {EMOJI}"
    return [block]


def _coverage_case_diagram_matrix_cell() -> list[dict]:
    block = diagram_block("matrix")
    block["diagram"]["cells"][0][0] += f" {EMOJI}"
    return [block]


def _coverage_case_diagram_venn_set() -> list[dict]:
    block = diagram_block("venn")
    block["diagram"]["sets"][0]["label"] += f" {EMOJI}"
    return [block]


def _coverage_case_diagram_venn_overlap() -> list[dict]:
    block = diagram_block("venn")
    block["diagram"]["overlaps"][0]["label"] += f" {EMOJI}"
    return [block]


def _coverage_case_diagram_swimlane_lane() -> list[dict]:
    block = diagram_block("swimlane")
    block["diagram"]["lanes"][0]["label"] += f" {EMOJI}"
    return [block]


def _coverage_case_diagram_swimlane_stage() -> list[dict]:
    block = diagram_block("swimlane")
    block["diagram"]["stages"][0]["label"] += f" {EMOJI}"
    return [block]


COVERAGE_CASES = (
    ("chart-category", _coverage_case_chart_category),
    ("chart-series-label", _coverage_case_chart_series_label),
    ("chart-notes", _coverage_case_chart_notes),
    ("chart-axis-unit", _coverage_case_chart_axis_unit),
    ("diagram-edge-label", _coverage_case_diagram_edge_label),
    ("diagram-event-label", _coverage_case_diagram_event_label),
    ("diagram-event-sub", _coverage_case_diagram_event_sub),
    ("diagram-matrix-row", _coverage_case_diagram_matrix_row),
    ("diagram-matrix-column", _coverage_case_diagram_matrix_column),
    ("diagram-matrix-cell", _coverage_case_diagram_matrix_cell),
    ("diagram-venn-set", _coverage_case_diagram_venn_set),
    ("diagram-venn-overlap", _coverage_case_diagram_venn_overlap),
    ("diagram-swimlane-lane", _coverage_case_diagram_swimlane_lane),
    ("diagram-swimlane-stage", _coverage_case_diagram_swimlane_stage),
)


@pytest.mark.parametrize("name, factory", COVERAGE_CASES, ids=[name for name, _ in COVERAGE_CASES])
def test_coverage_collects_every_new_chart_and_diagram_label(tmp_path: Path, name: str, factory) -> None:
    from bookify.design import coverage

    loaded = model.load(write_manuscript(tmp_path, factory()), root=ROOT)
    result = coverage.check(loaded, ROOT)

    assert (EMOJI, "U+1F9EA") in result.missing, f"{name}: {result.missing}"


def test_chart_strings_use_only_the_latin_vietnamese_chain(tmp_path: Path) -> None:
    from bookify.design import coverage

    loaded = model.load(write_manuscript(tmp_path, [chart_block("bar")]), root=ROOT)
    segments = list(coverage._segments(loaded))
    chart_strings = {"Q1", "Change", SYNTHETIC}

    tags = {tag for text, tag in segments if text in chart_strings}
    assert tags == {"latin"}


def test_japanese_diagram_text_still_uses_the_text_chain(tmp_path: Path) -> None:
    from bookify.design import coverage

    block = diagram_block("process")
    block["diagram"]["nodes"][0]["label"] = "観察"
    block["diagram"]["nodes"][0]["sub"] = "信号"
    loaded = model.load(write_manuscript(tmp_path, [block]), root=ROOT)

    result = coverage.check(loaded, ROOT)

    assert result.ok
    assert result.japanese >= 4


def test_japanese_chart_label_is_glyph_missing_before_coverage(tmp_path: Path) -> None:
    block = chart_block("bar")
    block["chart"]["categories"][0] = "四半期"

    with pytest.raises(BookifyError) as error:
        model.load(write_manuscript(tmp_path, [block]), root=ROOT)

    assert error.value.code == "GLYPH_MISSING"


# --- Integration: waterfall plotted geometry and the Task 36 label gate -------

def test_waterfall_axis_bounds_apply_to_the_cumulative_extent() -> None:
    block = _chart("waterfall", axis={"unit": "index", "min": 0, "max": 100})
    assert checks.validate_chart(block)["kind"] == "waterfall"

    too_high = _chart("waterfall", axis={"unit": "index", "min": 0, "max": 50})
    with pytest.raises(BookifyError) as error:
        checks.validate_chart(too_high)
    assert error.value.code == "SCHEMA_INVALID"
    assert "outside axis" in error.value.message, error.value.message

    too_low = _chart("waterfall", axis={"unit": "index", "min": 10})
    with pytest.raises(BookifyError) as error:
        checks.validate_chart(too_low)
    assert error.value.code == "SCHEMA_INVALID"
    assert "outside axis" in error.value.message


def test_waterfall_total_mismatch_still_fails_beside_the_new_axis_rule() -> None:
    block = _chart("waterfall", values=[[40], [12], [-7], [50]], axis={"unit": "index", "min": 0})

    with pytest.raises(BookifyError) as error:
        checks.validate_chart(block)

    assert error.value.code == "SCHEMA_INVALID"
    assert "running sum" in error.value.message


@pytest.mark.parametrize("kind", ["stacked_bar", "area"])
def test_declared_axis_must_cover_the_plotted_stack(kind: str) -> None:
    accepted = _chart(
        kind,
        categories=["A", "B"],
        values=[[20, 22], [20, 22]],
        axis={"min": 0, "max": 42},
    )
    assert checks.validate_chart(accepted)["kind"] == kind

    clipped = _chart(
        kind,
        categories=["A", "B"],
        values=[[20, 22], [20, 22]],
        axis={"min": 0, "max": 41},
    )
    with pytest.raises(BookifyError) as error:
        checks.validate_chart(clipped)

    assert error.value.code == "SCHEMA_INVALID"
    assert "outside axis" in error.value.message, error.value.message


def test_label_fit_accepts_a_label_that_fits_at_the_start_size() -> None:
    checks.validate_diagram_label("Observe", 100.0, 40.0, locator="test.label")


def test_label_fit_accepts_a_label_after_a_step_down() -> None:
    block = _diagram("process")
    block["diagram"]["nodes"][0]["label"] = "Read the setting against the whole room again"

    assert checks.validate_diagram(block, root=ROOT)


def test_label_fit_rejects_an_impossible_unbreakable_label() -> None:
    label = "x" * 200
    block = _diagram("process")
    block["diagram"]["nodes"][0]["label"] = label

    with pytest.raises(BookifyError) as error:
        checks.validate_diagram(block, root=ROOT)

    assert error.value.code == "SCHEMA_INVALID"
    assert label in error.value.message
    assert "5.5pt floor" in error.value.message


def test_label_fit_splits_cjk_labels_per_codepoint() -> None:
    block = _diagram("process")
    block["diagram"]["nodes"] = [
        {"id": f"n-{index}", "label": f"Node {index}"} for index in range(6)
    ]
    block["diagram"]["nodes"][0]["label"] = "観察信号設定読取記録応答判断記録"
    block["diagram"]["edges"] = [{"from": "n-0", "to": "n-1"}]
    block["diagram"].pop("groups", None)

    assert checks.validate_diagram(block, root=ROOT)


def test_fit_gate_is_skipped_without_local_fonts(tmp_path: Path) -> None:
    checks.validate_diagram_label("x" * 200, 10.0, 10.0, locator="test.label", root=tmp_path)


def test_impossible_diagram_label_fails_at_the_model_boundary(tmp_path: Path) -> None:
    label = "unbreakable" * 20
    block = _diagram("network")
    block["diagram"]["nodes"][0]["label"] = label

    with pytest.raises(BookifyError) as error:
        model.load(write_manuscript(tmp_path, [block]), root=ROOT)

    assert error.value.code == "SCHEMA_INVALID"
    assert label in error.value.message


# --- Integration corrections requested by the charts owner --------------------

def test_four_series_palette_has_one_home() -> None:
    from bookify.design import tokens

    assert len(presets.SERIES_COLOURS) == 4
    assert len(set(presets.SERIES_COLOURS)) == 4
    assert presets.SERIES_COLOURS == (
        tokens.GREY_3_HEX,
        tokens.ACCENT_HEX,
        tokens.GREY_1_HEX,
        tokens.ACCENT_TINT_3_HEX,
    ), "the fourth series colour is the restrained accent tint, not a new hue"


def test_four_series_chart_uses_the_registry_palette(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from bookify.figures import charts

    sentinel = "#123456"
    monkeypatch.setattr(
        presets,
        "SERIES_COLOURS",
        (presets.SERIES_COLOURS[0], presets.SERIES_COLOURS[1], presets.SERIES_COLOURS[2], sentinel),
    )
    block = _chart(
        "grouped_bar",
        categories=["A", "B"],
        series=[{"id": f"s-{index}", "label": f"S{index}"} for index in range(4)],
        values=[[1, 2, 3, 4], [4, 3, 2, 1]],
        verification="synthetic",
        notes=SYNTHETIC,
        source=None,
    )

    rendered = charts.render(block, ROOT, tmp_path)

    assert sentinel in rendered.path.read_text().lower(), (
        "the fourth series must come from presets.SERIES_COLOURS, not a renderer fallback"
    )


def test_error_bar_null_error_is_only_the_documented_gap() -> None:
    block = _chart(
        "error_bar",
        values=[[None], [6]],
        errors=[[None], [0.8]],
        notes="Q1 was not reported; its error is a null gap too.",
    )

    assert checks.validate_chart(block)["kind"] == "error_bar"


def test_error_bar_error_without_a_value_is_rejected(tmp_path: Path) -> None:
    block = _chart(
        "error_bar",
        values=[[None], [6]],
        errors=[[0.5], [0.8]],
        notes="Q1 was not reported.",
    )

    with pytest.raises(BookifyError) as error:
        checks.validate_chart(block)
    assert error.value.code == "SCHEMA_INVALID"
    assert "error needs a value" in error.value.message

    with pytest.raises(BookifyError) as boundary_error:
        model.load(write_manuscript(tmp_path, [block]), root=ROOT)
    assert boundary_error.value.code == "SCHEMA_INVALID"
