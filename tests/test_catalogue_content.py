"""Content contract for the visual catalogue (Tasks 39–40).

These tests read and normalize the stored manuscript only. They deliberately do
not render charts or diagrams: the render acceptance belongs to Task 43 once the
figure renderers land. The PDF-level inventory, caption and page checks belong to
the verification owner (Tasks 41/43).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from bookify.manuscript import model
from bookify.publish import normalize

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "content" / "catalogue.yaml"

SECTION_TITLES = [
    "About this catalogue",
    "Charts: bars",
    "Charts: lines",
    "Charts: points",
    "Charts: distributions",
    "Charts: matrices",
    "Charts: parts",
    "Diagrams: flow",
    "Diagrams: structure",
    "Diagrams: relations",
    "Illustrations",
    "Coverage",
]

CHART_SEQUENCE = [
    "bar",
    "grouped_bar",
    "stacked_bar",
    "line",
    "area",
    "scatter",
    "bubble",
    "histogram",
    "box",
    "violin",
    "error_bar",
    "heatmap",
    "radar",
    "pie",
    "pie",
    "waterfall",
]

DIAGRAM_SEQUENCE = [
    "process",
    "cycle",
    "timeline",
    "hierarchy",
    "decision_tree",
    "model",
    "network",
    "matrix",
    "venn",
    "swimlane",
]

ILLUSTRATION_SEQUENCE = ["photo-1", "hist-1", "art-1", "rec-1"]

COVERAGE_ROWS = [
    ["Bar", "bar", "Figure 1"],
    ["Grouped bar", "grouped_bar", "Figure 2"],
    ["Stacked bar", "stacked_bar", "Figure 3"],
    ["Line", "line", "Figure 4"],
    ["Area", "area", "Figure 5"],
    ["Scatter", "scatter", "Figure 6"],
    ["Bubble", "bubble", "Figure 7"],
    ["Histogram", "histogram", "Figure 8"],
    ["Box plot", "box", "Figure 9"],
    ["Violin", "violin", "Figure 10"],
    ["Error bar", "error_bar", "Figure 11"],
    ["Heat map", "heatmap", "Figure 12"],
    ["Radar", "radar", "Figure 13"],
    ["Pie and donut", "pie", "Figures 14–15"],
    ["Waterfall", "waterfall", "Figure 16"],
    ["Process", "process", "Figure 17"],
    ["Cycle", "cycle", "Figure 18"],
    ["Timeline", "timeline", "Figure 19"],
    ["Hierarchy", "hierarchy", "Figure 20"],
    ["Decision tree", "decision_tree", "Figure 21"],
    ["Layered model", "model", "Figure 22"],
    ["Network", "network", "Figure 23"],
    ["Matrix", "matrix", "Figure 24"],
    ["Venn", "venn", "Figure 25"],
    ["Swimlane", "swimlane", "Figure 26"],
    ["Photograph", "contemporary_photograph", "Photograph 1"],
    ["Historical image", "contemporary_photograph or later_depiction", "Photograph 2"],
    ["Editorial artwork", "conceptual_artwork", "Photograph 3"],
    ["Conceptual reconstruction", "reconstruction", "Photograph 4"],
]

CJK = re.compile(r"[\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]")


@pytest.fixture(scope="module")
def manuscript() -> model.Manuscript:
    return model.load(CATALOGUE)


@pytest.fixture(scope="module")
def document(manuscript: model.Manuscript) -> normalize.Document:
    figure_paths = {
        block["id"]: "unused.svg"
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    }
    return normalize.build(manuscript, figure_paths)


def _blocks(manuscript: model.Manuscript):
    for section in manuscript.sections:
        yield from section["blocks"]


def _typed(manuscript: model.Manuscript, kind: str) -> list[dict]:
    return [block for block in _blocks(manuscript) if block["type"] == kind]


def _normalized_blocks(document: normalize.Document) -> list[dict]:
    return [block for section in document.data["sections"] for block in section["blocks"]]


def _normalized_block(document: normalize.Document, block_id: str) -> dict:
    return next(block for block in _normalized_blocks(document) if block["id"] == block_id)


def test_top_level_identity(manuscript: model.Manuscript) -> None:
    assert manuscript.id == "visual-catalogue"
    assert manuscript.revision == 2
    assert manuscript.data["schemaVersion"] == "1.0"
    assert manuscript.data["metadata"]["languages"] == ["en", "vi", "ja"]


def test_twelve_sections_in_order_with_one_line_titles(manuscript: model.Manuscript) -> None:
    assert [section["title"] for section in manuscript.sections] == SECTION_TITLES
    for section in manuscript.sections:
        assert "\n" not in section["title"]
        assert len(section["title"]) <= 24, section["title"]


def test_exact_visual_block_counts(manuscript: model.Manuscript) -> None:
    charts = _typed(manuscript, "chart")
    diagrams = _typed(manuscript, "diagram")
    illustrations = _typed(manuscript, "illustration")

    assert len(charts) == 16
    assert len(diagrams) == 10
    assert len(illustrations) == 4
    assert len(_typed(manuscript, "table")) == 1
    assert len(_typed(manuscript, "equation")) == 0
    assert len(list(_blocks(manuscript))) == 42  # 39 + three explicit companions


def test_chart_inventory_and_pie_donut_variants(manuscript: model.Manuscript) -> None:
    charts = _typed(manuscript, "chart")
    assert [block["chart"]["kind"] for block in charts] == CHART_SEQUENCE
    pies = [block for block in charts if block["chart"]["kind"] == "pie"]
    assert len(pies) == 2
    holes = [block["chart"]["hole"] for block in pies]
    assert holes[0] == 0
    assert 0 < holes[1] <= 0.7


def test_diagram_inventory(manuscript: model.Manuscript) -> None:
    diagrams = _typed(manuscript, "diagram")
    assert [block["diagram"]["preset"] for block in diagrams] == DIAGRAM_SEQUENCE


def test_model_caption_does_not_claim_absent_layer_boundaries(manuscript: model.Manuscript) -> None:
    model_block = next(block for block in _typed(manuscript, "diagram") if block["id"] == "b-diagram-model")
    assert "groups" not in model_block["diagram"]
    assert "boundar" not in model_block["caption"].lower()


def test_illustration_inventory(manuscript: model.Manuscript) -> None:
    illustrations = _typed(manuscript, "illustration")
    assert [block["illustrationId"] for block in illustrations] == ILLUSTRATION_SEQUENCE


def test_numbering_is_document_order(document: normalize.Document) -> None:
    labels = {
        block["id"]: block["label"]
        for block in _normalized_blocks(document)
        if block["type"] in {"chart", "diagram", "illustration"}
    }
    figures = [labels[block["id"]] for block in _normalized_blocks(document) if block["type"] in {"chart", "diagram"}]
    photographs = [labels[block["id"]] for block in _normalized_blocks(document) if block["type"] == "illustration"]

    assert figures == [f"Figure {number}" for number in range(1, 27)]
    assert photographs == [f"Photograph {number}" for number in range(1, 5)]
    assert labels["b-chart-pie"] == "Figure 14"
    assert labels["b-chart-donut"] == "Figure 15"
    assert labels["b-diagram-process"] == "Figure 17"
    assert labels["b-diagram-swimlane"] == "Figure 26"


def test_synthetic_chart_provenance(manuscript: model.Manuscript) -> None:
    for block in _typed(manuscript, "chart"):
        chart = block["chart"]
        assert chart["verification"] == "synthetic", block["id"]
        assert "source" not in chart, block["id"]
        assert "sourceAnchors" not in block, block["id"]
        assert chart.get("notes", "").strip(), block["id"]


def test_illustrative_diagram_provenance(manuscript: model.Manuscript) -> None:
    for block in _typed(manuscript, "diagram"):
        assert block["diagram"].get("synthetic") is True, block["id"]
        assert "sourceAnchors" not in block, block["id"]
        assert block.get("note", "").strip(), block["id"]


def test_chart_text_is_latin_vietnamese_only(manuscript: model.Manuscript) -> None:
    for block in _typed(manuscript, "chart"):
        chart = block["chart"]
        strings = list(chart.get("categories", []))
        strings.extend(series["label"] for series in chart["series"])
        for axis_name in ("axis", "xAxis"):
            unit = chart.get(axis_name, {}).get("unit")
            if unit:
                strings.append(unit)
        if chart.get("notes"):
            strings.append(chart["notes"])
        for text in strings:
            assert not CJK.search(text), f"{block['id']}: {text}"


def test_multilingual_content_is_present(manuscript: model.Manuscript, document: normalize.Document) -> None:
    all_text = "\n".join(
        block.get("text", "") for block in _blocks(manuscript) if block["type"] == "paragraph"
    )
    assert "Đây là" in all_text
    assert "このカタログ" in all_text

    chart_strings = []
    for block in _typed(manuscript, "chart"):
        chart = block["chart"]
        chart_strings.extend(chart.get("categories", []))
        chart_strings.extend(series["label"] for series in chart["series"])
    assert any("ượ" in text or "ứ" in text or "ộ" in text for text in chart_strings)

    diagram_strings = []
    for block in _typed(manuscript, "diagram"):
        diagram_strings.extend(node["label"] for node in block["diagram"].get("nodes", []))
        diagram_strings.extend(event["label"] for event in block["diagram"].get("events", []))
    assert any(CJK.search(text) for text in diagram_strings)

    captions = [block["caption"] for block in _normalized_blocks(document) if block["type"] in {"chart", "diagram"}]
    assert any("Synthetic data." in caption for caption in captions)
    assert any("Illustrative diagram." in caption for caption in captions)


def test_caption_shape_proxy_for_each_figure_group(document: normalize.Document) -> None:
    """Text-length proxy only; rendered line counts are proved by Task 43."""
    groups = {"chart": [], "diagram": [], "illustration": []}
    for block in _normalized_blocks(document):
        if block["type"] in groups:
            groups[block["type"]].append(block["caption"])
    for kind, captions in groups.items():
        assert any(len(caption) <= 90 for caption in captions), f"{kind} has no short candidate"
        assert any(len(caption) >= 120 for caption in captions), f"{kind} has no wrapped candidate"


def test_chart_and_diagram_caption_suffixes(document: normalize.Document) -> None:
    for block in _normalized_blocks(document):
        if block["type"] == "chart":
            assert block["caption"].endswith("Synthetic data."), block["id"]
        elif block["type"] == "diagram":
            assert block["caption"].endswith("Illustrative diagram."), block["id"]


def test_illustration_class_wording(document: normalize.Document) -> None:
    editorial = _normalized_block(document, "b-illustration-editorial")["caption"]
    reconstruction = _normalized_block(document, "b-illustration-reconstruction")["caption"]
    historical = _normalized_block(document, "b-illustration-historical")["caption"]
    photograph = _normalized_block(document, "b-illustration-photo")["caption"]

    assert "Original artwork" in editorial
    assert "Conceptual reconstruction" in reconstruction
    assert "no original" in reconstruction.lower()
    assert "MacArthur" in historical and "Hirohito" in historical
    assert photograph == "Photograph 1. A welcome ceremony in Tokyo, 2014."


def test_coverage_table_is_exact(manuscript: model.Manuscript) -> None:
    table = _typed(manuscript, "table")[0]
    assert table["id"] == "b-coverage-table"
    assert table["header"] == ["Family", "Kind or preset", "Figure"]
    assert table["rows"] == COVERAGE_ROWS
    assert len(table["rows"]) == 29
    assert len({row[0] for row in table["rows"]}) == 29


def test_coverage_references_resolve(document: normalize.Document) -> None:
    table = next(block for block in _normalized_blocks(document) if block["id"] == "b-coverage-table")
    labels = set(document.labels.values())
    for family, _kind, reference in table["rows"]:
        if reference.startswith("Figures "):
            first, last = reference.removeprefix("Figures ").split("–")
            assert f"Figure {first}" in labels, family
            assert f"Figure {last}" in labels, family
        else:
            assert reference in labels, family


def test_crossrefs_resolve_to_a_chart_diagram_and_photograph(document: normalize.Document) -> None:
    scope = _normalized_block(document, "b-about-scope")["text"]
    assert "Figure 1" in scope
    assert "Figure 17" in scope
    assert "Photograph 1" in scope