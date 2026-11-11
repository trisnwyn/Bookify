"""Diagram geometry to Typst/CeTZ source. The output is a pure function of the spec."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from bookify.figures import checks, presets


@dataclass(frozen=True)
class DiagramRender:
    block_id: str
    path: Path
    sha256: str
    snippet: str


def _string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _array(items: list[str]) -> str:
    """Typst distinguishes a one-item array from a parenthesised value."""
    if not items:
        return "()"
    body = ", ".join(items)
    if len(items) == 1:
        body += ","
    return f"({body})"


def _field(name: str, value: str) -> str:
    return f"{name}: {value}"


def _node(node: dict) -> str:
    parts = [f"id: {_string(node['id'])}", f"label: {_string(node['label'])}"]
    if node.get("sub"):
        parts.append(f"sub: {_string(node['sub'])}")
    for key in ("lane", "stage"):
        if node.get(key):
            parts.append(f"{key}: {_string(node[key])}")
    return "(" + ", ".join(parts) + ")"


def _edge(edge: dict) -> str:
    parts = [
        f"from: {_string(edge['from'])}",
        f"to: {_string(edge['to'])}",
        f"kind: {_string(edge.get('kind', 'arrow'))}",
    ]
    if edge.get("label"):
        parts.append(f"label: {_string(edge['label'])}")
    return "(" + ", ".join(parts) + ")"


def _group(group: dict) -> str:
    return "(" + ", ".join(
        [
            f"id: {_string(group['id'])}",
            f"label: {_string(group['label'])}",
            "nodes: " + _array([_string(node) for node in group["nodes"]]),
        ]
    ) + ")"


def _event(event: dict) -> str:
    parts = [f"id: {_string(event['id'])}", f"label: {_string(event['label'])}"]
    if event.get("sub"):
        parts.append(f"sub: {_string(event['sub'])}")
    parts.append(f"when: {_string(event['when'])}")
    return "(" + ", ".join(parts) + ")"


def _row(column: str) -> str:
    return _string(column)


def _cell_row(row: list[str]) -> str:
    return _array([_string(cell) for cell in row])


def _set(item: dict) -> str:
    return "(" + ", ".join([f"id: {_string(item['id'])}", f"label: {_string(item['label'])}"]) + ")"


def _overlap(region: dict) -> str:
    return "(" + ", ".join(
        [
            f"id: {_string(region['id'])}",
            f"label: {_string(region['label'])}",
            "sets: " + _array([_string(member) for member in region["sets"]]),
        ]
    ) + ")"


def _lane(item: dict) -> str:
    return "(" + ", ".join([f"id: {_string(item['id'])}", f"label: {_string(item['label'])}"]) + ")"


GRAPH_PAYLOADS = {"process", "model", "cycle", "hierarchy", "decision_tree", "network"}


def _payload(diagram: dict) -> list[str]:
    preset = diagram["preset"]
    parts: list[str] = []
    if preset in GRAPH_PAYLOADS:
        parts.append("nodes: " + _array([_node(node) for node in diagram["nodes"]]))
        parts.append("edges: " + _array([_edge(edge) for edge in diagram["edges"]]))
        if preset in {"process", "model"}:
            parts.append("groups: " + _array([_group(group) for group in diagram.get("groups", [])]))
    elif preset == "timeline":
        parts.append("events: " + _array([_event(event) for event in diagram["events"]]))
    elif preset == "matrix":
        parts.append("rows: " + _array([_row(row) for row in diagram["rows"]]))
        parts.append("columns: " + _array([_row(column) for column in diagram["columns"]]))
        parts.append("cells: " + _array([_cell_row(row) for row in diagram["cells"]]))
    elif preset == "venn":
        parts.append("sets: " + _array([_set(item) for item in diagram["sets"]]))
        if diagram.get("overlaps"):
            parts.append("overlaps: " + _array([_overlap(region) for region in diagram["overlaps"]]))
    elif preset == "swimlane":
        parts.append("lanes: " + _array([_lane(item) for item in diagram["lanes"]]))
        parts.append("stages: " + _array([_lane(item) for item in diagram["stages"]]))
        parts.append("nodes: " + _array([_node(node) for node in diagram["nodes"]]))
    else:  # pragma: no cover - checks.validate_diagram rejects unknown presets first
        raise AssertionError(f"unhandled diagram preset: {preset}")
    return parts


def render(block: dict, out_dir: Path) -> DiagramRender:
    diagram = checks.validate_diagram(block)
    spec = ", ".join([_field("preset", _string(diagram["preset"])), *_payload(diagram)])
    snippet = f"#diagram(({spec}), {presets.DIAGRAM_WIDTH_PT}pt)"

    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(snippet.encode()).hexdigest()[:12]
    target = out_dir / f"diagram-{block['id']}-{digest}.typ"
    target.write_text(
        '#import "/typst/cetz/diagram.typ": diagram\n' + snippet + "\n"
    )
    return DiagramRender(
        block_id=block["id"],
        path=target,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        snippet=snippet,
    )
