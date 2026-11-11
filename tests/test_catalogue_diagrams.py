"""Tasks 33-36: CeTZ tokens, diagram layouts, serialisation and label fitting.

Worker 3 owns this file. It is kept separate from the shared ``test_design.py``
and ``test_figures.py`` so parallel catalogue work cannot collide.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from bookify.design import lint, tokens
from bookify.figures import presets

ROOT = Path(__file__).resolve().parents[1]


def test_linter_scans_cetz_sources(tmp_path: Path) -> None:
    (tmp_path / "typst" / "cetz").mkdir(parents=True)
    (tmp_path / "typst" / "blocks.typ").write_text("#let preset-paragraph(body) = body\n")
    (tmp_path / "typst" / "cetz" / "diagram.typ").write_text(
        "#let label = text(size: 8pt)[x]\n"
    )

    issues = lint.lint(tmp_path)

    assert [issue.path.name for issue in issues] == ["diagram.typ"]
    assert "point size" in issues[0].message


def test_repository_cetz_sources_have_no_visual_literals() -> None:
    issues = lint.lint(ROOT)

    assert issues == [], "\n".join(f"{i.path.name}:{i.line} {i.message}" for i in issues)


def test_theme_defines_the_named_diagram_tokens() -> None:
    theme = (ROOT / "typst" / "theme.typ").read_text()
    block = theme.split("  diagram: (", 1)[1].split("  ),", 1)[0]

    for name, value in tokens.DIAGRAM_TOKENS.items():
        assert re.search(rf"\b{re.escape(name)}:", block), f"theme is missing diagram.{name}"
        assert re.search(rf"^\s*{re.escape(name)}: {re.escape(value)},$", block, re.MULTILINE), (
            f"diagram.{name} must stay {value} so process/model geometry is unchanged"
        )


def test_fit_render_and_production_share_one_diagram_width(tmp_path: Path) -> None:
    from bookify.figures import checks, diagrams

    theme = (ROOT / "typst" / "theme.typ").read_text()
    match = re.search(r"figure_width:\s*([0-9.]+)pt", theme)
    assert match is not None
    assert float(match.group(1)) == presets.DIAGRAM_WIDTH_PT
    assert checks.DIAGRAM_TOTAL_CM == pytest.approx(presets.DIAGRAM_WIDTH_PT / checks.PT_PER_CM)

    block = {
        "id": "b-width",
        "type": "diagram",
        "diagram": {
            "preset": "process",
            "nodes": [{"id": "n-a", "label": "Alpha"}, {"id": "n-b", "label": "Beta"}],
            "edges": [{"from": "n-a", "to": "n-b"}],
            "groups": [],
        },
    }
    rendered = diagrams.render(block, tmp_path)

    assert rendered.snippet.endswith(f", {presets.DIAGRAM_WIDTH_PT}pt)")


def _diagram_source(preset: str) -> str:
    return (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/cetz/diagram.typ": diagram\n'
        "#show: book_base\n"
        '#set page(paper: "a4", margin: 40pt)\n'
        "#diagram(("
        f'preset: "{preset}", '
        'nodes: ((id: "a", label: "A"), (id: "b", label: "B")), '
        'edges: ((from: "a", to: "b", kind: "arrow"),), '
        "groups: ()"
        f"), {presets.DIAGRAM_WIDTH_PT}pt)\n"
    )


def test_unknown_preset_panics_instead_of_falling_back() -> None:
    from helpers import compile_typ

    with pytest.raises(subprocess.CalledProcessError) as error:
        compile_typ(_diagram_source("mystery"), "worker3-unknown-preset")

    assert "unknown diagram preset" in (error.value.stderr or "")


def _compile_spec(spec: str, name: str) -> tuple[Path, str]:
    from helpers import compile_typ

    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/cetz/diagram.typ": diagram\n'
        "#show: book_base\n"
        '#set page(paper: "a4", margin: 40pt)\n'
        f"#diagram({spec}, {presets.DIAGRAM_WIDTH_PT}pt)\n"
    )
    pdf = compile_typ(source, name)
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    return pdf, text


def test_cycle_layout_renders_every_label() -> None:
    spec = (
        "(preset: \"cycle\", "
        "nodes: ((id: \"n-plan\", label: \"Plan\"), (id: \"n-do\", label: \"Do\"), "
        "(id: \"n-check\", label: \"Check\"), (id: \"n-act\", label: \"Act\")), "
        "edges: ((from: \"n-plan\", to: \"n-do\", kind: \"arrow\"), "
        "(from: \"n-do\", to: \"n-check\", kind: \"arrow\"), "
        "(from: \"n-check\", to: \"n-act\", kind: \"arrow\"), "
        "(from: \"n-act\", to: \"n-plan\", kind: \"arrow\")), "
        "groups: ())"
    )

    _, text = _compile_spec(spec, "worker3-cycle")

    for label in ("Plan", "Do", "Check", "Act"):
        assert label in text


def test_hierarchy_layout_renders_every_label() -> None:
    spec = (
        "(preset: \"hierarchy\", "
        "nodes: ((id: \"n-root\", label: \"Root\"), (id: \"n-a\", label: \"Alpha\"), "
        "(id: \"n-b\", label: \"Beta\"), (id: \"n-a1\", label: \"Leaf one\"), "
        "(id: \"n-a2\", label: \"Leaf two\"), (id: \"n-b1\", label: \"Leaf three\")), "
        "edges: ((from: \"n-root\", to: \"n-a\", kind: \"arrow\"), "
        "(from: \"n-root\", to: \"n-b\", kind: \"arrow\"), "
        "(from: \"n-a\", to: \"n-a1\", kind: \"arrow\"), "
        "(from: \"n-a\", to: \"n-a2\", kind: \"arrow\"), "
        "(from: \"n-b\", to: \"n-b1\", kind: \"arrow\")), "
        "groups: ())"
    )

    _, text = _compile_spec(spec, "worker3-hierarchy")

    for label in ("Root", "Alpha", "Beta", "Leaf one", "Leaf two", "Leaf three"):
        assert label in text


def test_decision_tree_layout_renders_labels_and_branch_conditions() -> None:
    spec = (
        "(preset: \"decision_tree\", "
        "nodes: ((id: \"n-q\", label: \"Signal seen?\"), (id: \"n-y\", label: \"Read the setting\"), "
        "(id: \"n-n\", label: \"Record the gap\")), "
        "edges: ((from: \"n-q\", to: \"n-y\", kind: \"arrow\", label: \"yes\"), "
        "(from: \"n-q\", to: \"n-n\", kind: \"arrow\", label: \"no\")), "
        "groups: ())"
    )

    _, text = _compile_spec(spec, "worker3-decision-tree")

    for label in ("Signal seen?", "Read the setting", "Record the gap", "yes", "no"):
        assert label in text


def test_network_layout_renders_every_label() -> None:
    spec = (
        "(preset: \"network\", "
        "nodes: ((id: \"n-a\", label: \"Alpha\"), (id: \"n-b\", label: \"Beta\"), "
        "(id: \"n-c\", label: \"Gamma\"), (id: \"n-d\", label: \"Delta\"), "
        "(id: \"n-e\", label: \"Epsilon\")), "
        "edges: ((from: \"n-a\", to: \"n-c\", kind: \"arrow\"), "
        "(from: \"n-b\", to: \"n-d\", kind: \"arrow\"), "
        "(from: \"n-c\", to: \"n-e\", kind: \"arrow\"), "
        "(from: \"n-d\", to: \"n-a\", kind: \"arrow\"), "
        "(from: \"n-e\", to: \"n-b\", kind: \"arrow\")), "
        "groups: ())"
    )

    _, text = _compile_spec(spec, "worker3-network")

    for label in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon"):
        assert label in text


def test_timeline_layout_renders_events_above_and_below() -> None:
    spec = (
        "(preset: \"timeline\", "
        "events: ((id: \"ev-one\", label: \"First signal\", sub: \"observation\", when: \"Step 1\"), "
        "(id: \"ev-two\", label: \"Reading\", when: \"Step 2\"), "
        "(id: \"ev-three\", label: \"Response\", sub: \"action\", when: \"Step 3\")), "
        "groups: ())"
    )

    _, text = _compile_spec(spec, "worker3-timeline")

    for label in ("First signal", "observation", "Reading", "Response", "action", "Step 1", "Step 2", "Step 3"):
        assert label in text


def test_matrix_layout_renders_headers_and_every_cell() -> None:
    spec = (
        "(preset: \"matrix\", "
        "rows: (\"Signal\", \"Setting\"), "
        "columns: (\"Question\", \"Failure mode\"), "
        "cells: ((\"What happened?\", \"Reading the gesture alone\"), "
        "(\"What does it mean here?\", \"Assuming your own default\")), "
        "groups: ())"
    )

    _, text = _compile_spec(spec, "worker3-matrix")

    for label in (
        "Signal", "Setting", "Question", "Failure mode",
        "What happened?", "Reading the gesture alone",
        "What does it mean here?", "Assuming your own default",
    ):
        assert label in text


def test_venn_layout_renders_sets_and_the_shared_region() -> None:
    spec = (
        "(preset: \"venn\", "
        "sets: ((id: \"set-a\", label: \"Observed\"), (id: \"set-b\", label: \"Inferred\")), "
        "overlaps: ((id: \"ov-both\", label: \"Shared reading\", sets: (\"set-a\", \"set-b\")),), "
        "groups: ())"
    )

    _, text = _compile_spec(spec, "worker3-venn")

    for label in ("Observed", "Inferred", "Shared reading"):
        assert label in text


def test_swimlane_layout_renders_lanes_stages_and_nodes() -> None:
    spec = (
        "(preset: \"swimlane\", "
        "lanes: ((id: \"lane-reader\", label: \"Reader\"), (id: \"lane-source\", label: \"Source\")), "
        "stages: ((id: \"stage-one\", label: \"Signal\"), (id: \"stage-two\", label: \"Setting\")), "
        "nodes: ((id: \"n-observe\", label: \"Observe\", lane: \"lane-reader\", stage: \"stage-one\"), "
        "(id: \"n-record\", label: \"Record\", lane: \"lane-source\", stage: \"stage-two\")), "
        "groups: ())"
    )

    _, text = _compile_spec(spec, "worker3-swimlane")

    for label in ("Reader", "Source", "Signal", "Setting", "Observe", "Record"):
        assert label in text


def _fit_probe(label: str, width: str, height: str) -> str:
    from helpers import compile_typ

    # Build a valid Typst string literal without relying on Python repr quoting.
    escaped = label.replace("\\", "\\\\").replace('"', '\\"')
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/cetz/layouts.typ": fit-size\n'
        "#show: book_base\n"
        f'#context {{ repr(fit-size("{escaped}", {width}, {height})) }}\n'
    )
    pdf = compile_typ(source, "worker3-fit-probe")
    return subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout.strip()


def test_label_fit_shrinks_a_long_label_to_the_step_grid() -> None:
    # At 8pt this label is wider than the available 60pt box; it must step down.
    fitted = _fit_probe("A label that is too wide for a small box", "70pt", "30pt")

    assert fitted.endswith("pt")
    size = float(fitted.removesuffix("pt"))
    assert 5.5 <= size < 8
    assert (8 - size) % 0.5 == 0, f"fitting must move in 0.5pt steps, got {size}"


def test_label_fit_panics_on_an_impossible_label() -> None:
    from helpers import compile_typ

    label = "Unbreakable" * 20
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/cetz/layouts.typ": fit-size\n'
        "#show: book_base\n"
        f'#context {{ fit-size("{label}", 40pt, 12pt) }}\n'
    )

    with pytest.raises(subprocess.CalledProcessError) as error:
        compile_typ(source, "worker3-fit-impossible")

    assert "does not fit at the 5.5pt floor" in (error.value.stderr or "")
    assert "Unbreakable" in (error.value.stderr or "")


def test_long_node_label_wraps_and_stays_extractable() -> None:
    spec = (
        "(preset: \"process\", "
        "nodes: ((id: \"n-a\", label: \"A deliberately long label for a box\"), "
        "(id: \"n-b\", label: \"Short\")), "
        "edges: ((from: \"n-a\", to: \"n-b\", kind: \"arrow\"),), "
        "groups: ())"
    )

    _, text = _compile_spec(spec, "worker3-long-label")

    assert "A deliberately long label for a box" in " ".join(text.split())


GRAPH_CASES: dict[str, tuple[list[tuple[str, str]], list[tuple[str, str, str | None]], list[str]]] = {
    "process": (
        [("n-a", "Alpha"), ("n-b", "Beta")],
        [("n-a", "n-b", None)],
        ["Alpha", "Beta"],
    ),
    "model": (
        [("n-a", "Alpha"), ("n-b", "Beta")],
        [("n-a", "n-b", None)],
        ["Alpha", "Beta"],
    ),
    "cycle": (
        [("n-a", "Plan"), ("n-b", "Do"), ("n-c", "Check")],
        [("n-a", "n-b", None), ("n-b", "n-c", None), ("n-c", "n-a", None)],
        ["Plan", "Do", "Check"],
    ),
    "hierarchy": (
        [("n-a", "Root"), ("n-b", "Child")],
        [("n-a", "n-b", None)],
        ["Root", "Child"],
    ),
    "decision_tree": (
        [("n-q", "Question"), ("n-y", "Yes path"), ("n-n", "No path")],
        [("n-q", "n-y", "yes"), ("n-q", "n-n", "no")],
        ["Question", "Yes path", "No path", "yes", "no"],
    ),
    "network": (
        [("n-a", "Alpha"), ("n-b", "Beta"), ("n-c", "Gamma")],
        [("n-a", "n-b", None), ("n-b", "n-c", None)],
        ["Alpha", "Beta", "Gamma"],
    ),
}


def _graph_spec(preset: str, kind: str | None) -> str:
    nodes, edges, _labels = GRAPH_CASES[preset]
    node_items = [f'(id: "{node_id}", label: "{label}")' for node_id, label in nodes]
    node_body = ", ".join(node_items) + ("," if len(node_items) == 1 else "")
    edge_parts = []
    for source, target, edge_label in edges:
        fields = [f'from: "{source}"', f'to: "{target}"']
        if edge_label:
            fields.append(f'label: "{edge_label}"')
        if kind is not None:
            fields.append(f'kind: "{kind}"')
        edge_parts.append("(" + ", ".join(fields) + ")")
    edge_body = ", ".join(edge_parts) + ("," if len(edge_parts) == 1 else "")
    groups = "()" if preset in {"process", "model"} else ""
    suffix = f", groups: {groups}" if groups else ""
    return f'(preset: "{preset}", nodes: ({node_body}), edges: ({edge_body}){suffix})'


def _pixels(pdf: Path, name: str) -> Image.Image:
    prefix = ROOT / ".cache" / "verify-snippets" / name
    subprocess.run(["pdftoppm", "-png", "-r", "150", "-singlefile", str(pdf), str(prefix)], check=True)
    return Image.open(f"{prefix}.png").convert("L")


@pytest.mark.parametrize("preset", list(GRAPH_CASES))
def test_omitted_edge_kind_defaults_to_arrow(preset: str) -> None:
    omitted_pdf, omitted_text = _compile_spec(_graph_spec(preset, None), f"worker3-omit-{preset}")
    arrow_pdf, arrow_text = _compile_spec(_graph_spec(preset, "arrow"), f"worker3-arrow-{preset}")

    assert omitted_text == arrow_text
    difference = ImageChops.difference(
        _pixels(omitted_pdf, f"worker3-omit-{preset}"),
        _pixels(arrow_pdf, f"worker3-arrow-{preset}"),
    )
    assert difference.getbbox() is None, "an omitted kind must render exactly like kind: arrow"
    for label in GRAPH_CASES[preset][2]:
        assert label in omitted_text


def test_an_explicit_line_kind_is_still_a_line() -> None:
    omitted_pdf, _ = _compile_spec(_graph_spec("cycle", None), "worker3-line-omitted")
    line_pdf, _ = _compile_spec(_graph_spec("cycle", "line"), "worker3-line-explicit")

    difference = ImageChops.difference(
        _pixels(omitted_pdf, "worker3-line-omitted"),
        _pixels(line_pdf, "worker3-line-explicit"),
    )
    assert difference.getbbox() is not None, "kind: line must not be rendered as an arrow"


def test_an_impossible_diagram_label_is_schema_invalid(tmp_path: Path) -> None:
    from bookify.errors import BookifyError
    from bookify.figures import diagrams

    label = "Unbreakable" * 20
    block = {
        "id": "b-impossible-label",
        "type": "diagram",
        "diagram": {
            "preset": "process",
            "nodes": [{"id": "n-a", "label": label}, {"id": "n-b", "label": "Short"}],
            "edges": [{"from": "n-a", "to": "n-b"}],
            "groups": [],
        },
    }

    with pytest.raises(BookifyError) as error:
        diagrams.render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"
    assert "does not fit at the 5.5pt floor" in error.value.message
    assert "Unbreakable" in error.value.message


def test_impossible_diagram_label_blocks_manuscript_load(tmp_path: Path) -> None:
    import yaml

    from bookify.errors import BookifyError
    from bookify.manuscript import model

    data = yaml.safe_load((ROOT / "content" / "specimen.yaml").read_text())
    block = next(
        block
        for section in data["sections"]
        for block in section["blocks"]
        if block["type"] == "diagram"
    )
    label = "Unbreakable" * 20
    block["diagram"]["nodes"][0]["label"] = label
    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    with pytest.raises(BookifyError) as error:
        model.load(target, root=ROOT)

    assert error.value.code == "SCHEMA_INVALID"
    assert "does not fit at the 5.5pt floor" in error.value.message
    assert "Unbreakable" in error.value.message


def test_swimlane_nodes_stay_inside_the_last_lane() -> None:
    spec = (
        "(preset: \"swimlane\", "
        "lanes: ((id: \"l-a\", label: \"Lane A\"), (id: \"l-b\", label: \"Lane B\")), "
        "stages: ((id: \"s-a\", label: \"Stage A\"), (id: \"s-b\", label: \"Stage B\")), "
        "nodes: ((id: \"n-first\", label: \"First\", lane: \"l-a\", stage: \"s-a\"), "
        "(id: \"n-last\", label: \"Last cell\", lane: \"l-b\", stage: \"s-b\")), "
        "groups: ())"
    )
    pdf, _ = _compile_spec(spec, "worker3-swimlane-containment")

    image = _pixels(pdf, "worker3-swimlane-containment")
    width, height = image.size
    pixels = image.load()
    grid_rows = [
        y for y in range(height)
        if sum(1 for x in range(width) if pixels[x, y] < 128) > width * 0.45
    ]
    assert len(grid_rows) >= 4, "the swimlane grid must have a header and one line per lane"
    top, bottom = min(grid_rows), max(grid_rows)

    bbox = subprocess.run(
        ["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    words = re.findall(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]+)</word>',
        bbox,
    )
    label_boxes = [(float(y0), float(y1)) for _x0, y0, _x1, y1, text in words if text in {"Last", "cell"}]
    assert len(label_boxes) == 2, f"expected the two-word node label, found {label_boxes}"
    ratio = 150 / 72
    label_top = min(y0 for y0, _y1 in label_boxes) * ratio
    label_bottom = max(y1 for _y0, y1 in label_boxes) * ratio

    assert label_top > top, "the last-lane node begins above the grid"
    assert label_bottom < bottom, "the last-lane node falls outside the grid's bottom border"


def _payload_specs() -> dict[str, tuple[dict, list[str]]]:
    """One contract-shaped payload per preset and the labels it must print."""
    return {
        "process": (
            {
                "preset": "process",
                "nodes": [{"id": "n-a", "label": "Alpha"}, {"id": "n-b", "label": "Beta"}],
                "edges": [{"from": "n-a", "to": "n-b"}],
                "groups": [],
            },
            ["Alpha", "Beta"],
        ),
        "model": (
            {
                "preset": "model",
                "nodes": [{"id": "n-a", "label": "Alpha"}, {"id": "n-b", "label": "Beta"}],
                "edges": [{"from": "n-a", "to": "n-b"}],
                "groups": [],
            },
            ["Alpha", "Beta"],
        ),
        "cycle": (
            {
                "preset": "cycle",
                "nodes": [{"id": "n-a", "label": "Plan"}, {"id": "n-b", "label": "Do"}, {"id": "n-c", "label": "Check"}],
                "edges": [
                    {"from": "n-a", "to": "n-b"},
                    {"from": "n-b", "to": "n-c"},
                    {"from": "n-c", "to": "n-a"},
                ],
            },
            ["Plan", "Do", "Check"],
        ),
        "hierarchy": (
            {
                "preset": "hierarchy",
                "nodes": [{"id": "n-a", "label": "Root"}, {"id": "n-b", "label": "Child"}],
                "edges": [{"from": "n-a", "to": "n-b"}],
            },
            ["Root", "Child"],
        ),
        "decision_tree": (
            {
                "preset": "decision_tree",
                "nodes": [
                    {"id": "n-q", "label": "Signal seen?"},
                    {"id": "n-y", "label": "Read the setting"},
                    {"id": "n-n", "label": "Record the gap"},
                ],
                "edges": [
                    {"from": "n-q", "to": "n-y", "label": "yes"},
                    {"from": "n-q", "to": "n-n", "label": "no"},
                ],
            },
            ["Signal seen?", "Read the setting", "Record the gap", "yes", "no"],
        ),
        "network": (
            {
                "preset": "network",
                "nodes": [
                    {"id": "n-a", "label": "Alpha"},
                    {"id": "n-b", "label": "Beta"},
                    {"id": "n-c", "label": "Gamma"},
                ],
                "edges": [{"from": "n-a", "to": "n-c"}, {"from": "n-b", "to": "n-a"}],
            },
            ["Alpha", "Beta", "Gamma"],
        ),
        "timeline": (
            {
                "preset": "timeline",
                "events": [
                    {"id": "ev-a", "label": "First signal", "sub": "observation", "when": "Step 1"},
                    {"id": "ev-b", "label": "Reading", "when": "Step 2"},
                ],
            },
            ["First signal", "observation", "Reading", "Step 1", "Step 2"],
        ),
        "matrix": (
            {
                "preset": "matrix",
                "rows": ["Signal", "Setting"],
                "columns": ["Question", "Failure mode"],
                "cells": [["What happened?", "Read alone"], ["What does it mean?", "Assume a default"]],
            },
            ["Signal", "Setting", "Question", "Failure mode", "What happened?", "Assume a default"],
        ),
        "venn": (
            {
                "preset": "venn",
                "sets": [{"id": "set-a", "label": "Observed"}, {"id": "set-b", "label": "Inferred"}],
                "overlaps": [{"id": "ov-both", "label": "Shared reading", "sets": ["set-a", "set-b"]}],
            },
            ["Observed", "Inferred", "Shared reading"],
        ),
        "swimlane": (
            {
                "preset": "swimlane",
                "lanes": [{"id": "lane-r", "label": "Reader"}, {"id": "lane-s", "label": "Source"}],
                "stages": [{"id": "st-one", "label": "Signal"}, {"id": "st-two", "label": "Setting"}],
                "nodes": [
                    {"id": "n-a", "label": "Observe", "lane": "lane-r", "stage": "st-one"},
                    {"id": "n-b", "label": "Record", "lane": "lane-s", "stage": "st-two"},
                ],
            },
            ["Reader", "Source", "Signal", "Setting", "Observe", "Record"],
        ),
    }


@pytest.mark.parametrize("preset", list(_payload_specs()))
def test_diagrams_render_serialises_validates_and_compiles(preset: str, tmp_path: Path) -> None:
    from bookify.figures import diagrams
    from helpers import compile_typ

    spec, labels = _payload_specs()[preset]
    block = {"id": f"b-{preset}", "type": "diagram", "diagram": spec}

    first = diagrams.render(block, tmp_path)
    second = diagrams.render(block, tmp_path)

    assert first.sha256 == second.sha256
    assert f'preset: "{preset}"' in first.snippet
    for label in labels:
        assert label in first.snippet

    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/cetz/diagram.typ": diagram\n'
        "#show: book_base\n"
        '#set page(paper: "a4", margin: 40pt)\n'
        f"{first.snippet}\n"
    )
    pdf = compile_typ(source, f"worker3-serialised-{preset}")
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    joined = " ".join(text.split())
    for label in labels:
        assert label in joined
