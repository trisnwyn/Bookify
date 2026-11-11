"""One validation boundary for chart and diagram payloads.

Shape rules that JSON Schema can express live in the schema; the rules here are
the ones it cannot: matrix completeness, ranges, caps, order, tree/cycle
structure, null rules, axis bounds, payload exclusivity and the chart font
chain. `manuscript.model`, the renderers and the tests all call this module, so
a rule is never implemented twice and an unknown kind or preset is always
`SCHEMA_INVALID`, never a fallback.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import yaml
from fontTools.ttLib import TTCollection, TTFont

from bookify.errors import BookifyError
from bookify.figures import presets

CHART_KINDS: tuple[str, ...] = tuple(presets.CHART_PRESETS)
DIAGRAM_PRESETS: tuple[str, ...] = tuple(presets.DIAGRAM_PRESETS)

# Scripts Typst renders through the CJK chain but Matplotlib cannot: a chart
# string must stay inside the Spectral (Latin/Vietnamese) chain.
CJK_RANGES: tuple[tuple[int, int], ...] = (
    (0x3000, 0x303F),  # CJK punctuation
    (0x3040, 0x309F),  # Hiragana
    (0x30A0, 0x30FF),  # Katakana
    (0x3400, 0x4DBF),  # CJK extension A
    (0x4E00, 0x9FFF),  # CJK unified ideographs
    (0xFF00, 0xFFEF),  # halfwidth forms
)

# Label-fit geometry, pinned to the implemented CeTZ layouts (Tasks 33-36).
# Typst remains the authoritative fitter and still panics; this gate exists so
# an impossible label fails as SCHEMA_INVALID before compilation.
FIT_PAD_PT = 3.0
FIT_FIRST_LINE_EM = 0.66
FIT_LINE_ADVANCE_EM = 2.175
FIT_WIDTH_TOLERANCE = 0.95
PT_PER_CM = 28.3465
# One width source: the theme's production figure width (typst/theme.typ).
DIAGRAM_TOTAL_CM = presets.DIAGRAM_WIDTH_PT / PT_PER_CM

CHART_PAYLOADS: dict[str, tuple[str, ...]] = {
    "grouped_bar": ("categories", "values"),
    "bar": ("categories", "values"),
    "stacked_bar": ("categories", "values"),
    "line": ("categories", "values"),
    "area": ("categories", "values"),
    "scatter": ("points", "xAxis"),
    "bubble": ("points", "xAxis"),
    "histogram": ("bins", "counts"),
    "box": ("categories", "stats"),
    "violin": ("categories", "samples", "notes"),
    "heatmap": ("categories", "values"),
    "pie": ("categories", "values", "hole"),
    "waterfall": ("categories", "values", "totals"),
    "radar": ("categories", "values"),
    "error_bar": ("categories", "values", "errors"),
}
CHART_COMMON = ("kind", "series", "verification", "source", "notes", "axis")
NULL_KINDS = frozenset({"grouped_bar", "bar", "stacked_bar", "line", "area", "error_bar"})
NON_NEGATIVE_KINDS = frozenset({"stacked_bar", "area", "radar"})
VERIFICATIONS = frozenset({"verified", "inferred", "synthetic"})

GRAPH_PRESETS = frozenset({"process", "model", "cycle", "hierarchy", "decision_tree", "network"})
DIAGRAM_PAYLOADS: dict[str, tuple[str, ...]] = {
    "process": ("nodes", "edges", "groups"),
    "model": ("nodes", "edges", "groups"),
    "cycle": ("nodes", "edges"),
    "hierarchy": ("nodes", "edges"),
    "decision_tree": ("nodes", "edges"),
    "network": ("nodes", "edges"),
    "timeline": ("events",),
    "matrix": ("rows", "columns", "cells"),
    "venn": ("sets", "overlaps"),
    "swimlane": ("lanes", "stages", "nodes"),
}


def is_cjk(character: str) -> bool:
    codepoint = ord(character)
    return any(low <= codepoint <= high for low, high in CJK_RANGES)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=None)
def _face_metrics(path: str) -> tuple[int, dict[int, str], Any]:
    source = Path(path)
    if source.suffix.lower() == ".ttc":
        font = TTCollection(str(source)).fonts[0]
    else:
        font = TTFont(str(source))
    return font["head"].unitsPerEm, font.getBestCmap() or {}, font["hmtx"]


@lru_cache(maxsize=None)
def _fit_chain(root: str) -> tuple[str, ...] | None:
    """The vendored latin-vietnamese + japanese chain, or None when unavailable."""
    manifest_path = Path(root) / "assets" / "fonts" / "fonts.yaml"
    if not manifest_path.is_file():
        return None
    try:
        manifest = yaml.safe_load(manifest_path.read_text())
    except yaml.YAMLError:
        return None
    if not isinstance(manifest, dict):
        return None
    families = {family["family"]: family for family in manifest.get("families", [])}
    paths: list[str] = []
    for script in ("latin-vietnamese", "japanese"):
        for name in manifest.get("scripts", {}).get(script, {}).get("chain", []):
            for entry in families.get(name, {}).get("files", []):
                candidate = Path(root) / entry["path"]
                if candidate.is_file():
                    paths.append(str(candidate))
    return tuple(paths) or None


@lru_cache(maxsize=None)
def _advance(character: str, size: float, chain: tuple[str, ...]) -> float:
    for path in chain:
        units_per_em, cmap, hmtx = _face_metrics(path)
        glyph = cmap.get(ord(character))
        if glyph is None:
            continue
        return (hmtx[glyph][0] / units_per_em) * size
    # A glyph outside the local chain is a coverage error elsewhere; measuring it
    # as half an em keeps this gate from rejecting what Typst may still render.
    return 0.5 * size


def _text_width(text: str, size: float, chain: tuple[str, ...]) -> float:
    return sum(_advance(character, size, chain) for character in text)


def _label_units(label: str) -> list[tuple[str, bool]]:
    """Break opportunities matching the CeTZ fitter: spaces, CJK per codepoint."""
    units: list[tuple[str, bool]] = []
    for word_index, word in enumerate(label.split()):
        pieces: list[str] = []
        current = ""
        for character in word:
            if is_cjk(character):
                if current:
                    pieces.append(current)
                    current = ""
                pieces.append(character)
            else:
                current += character
        if current:
            pieces.append(current)
        for index, piece in enumerate(pieces):
            units.append((piece, word_index > 0 and index == 0))
    return units


def _label_fits(label: str, width_pt: float, height_pt: float, size: float, chain: tuple[str, ...]) -> bool:
    inner_width = width_pt - 2 * FIT_PAD_PT
    inner_height = height_pt - 2 * FIT_PAD_PT
    if inner_width <= 0 or inner_height <= 0:
        return False
    units = _label_units(label)
    if not units:
        return True
    # Typst sets weight 600 for most diagram labels; these metrics use the
    # Regular face, so a small tolerance keeps this gate from rejecting a label
    # Typst still fits.
    limit = inner_width / FIT_WIDTH_TOLERANCE
    for unit, _space in units:
        if _text_width(unit, size, chain) > limit:
            return False
    space = _text_width(" ", size, chain)
    lines = 1
    line = 0.0
    for unit, spaced in units:
        unit_width = _text_width(unit, size, chain)
        addition = (space if spaced and line > 0 else 0.0) + unit_width
        if line > 0 and line + addition > limit:
            lines += 1
            line = unit_width
        else:
            line += addition
    estimated_height = FIT_FIRST_LINE_EM * size + (lines - 1) * FIT_LINE_ADVANCE_EM * size
    return estimated_height <= inner_height


def validate_diagram_label(
    label: str,
    width_pt: float,
    height_pt: float,
    *,
    start_pt: float = 8.0,
    floor_pt: float = 5.5,
    step_pt: float = 0.5,
    locator: str,
    root: Path | None = None,
    _chain: tuple[str, ...] | None = None,
) -> None:
    """Raise SCHEMA_INVALID when a label cannot fit at the floor, as CeTZ decides.

    Font metrics come from the vendored chain. When the chain is unavailable this
    gate is skipped rather than guessing; Typst's own fitter still panics.
    """
    chain = _chain or _fit_chain(str(root or _project_root()))
    if chain is None:
        return
    size = start_pt
    while size >= floor_pt - 1e-9:
        if _label_fits(label, width_pt, height_pt, size, chain):
            return
        size = round(size - step_pt, 6)
    raise BookifyError(
        "SCHEMA_INVALID",
        f"diagram label does not fit at the {floor_pt:g}pt floor: {label!r}",
        locator,
    )


def _cm(value: float) -> float:
    return value * PT_PER_CM


def _check_label(label: str, width_pt: float, height_pt: float, start_pt: float, locator: str, chain: tuple[str, ...]) -> None:
    validate_diagram_label(
        label, width_pt, height_pt,
        start_pt=start_pt, locator=locator, _chain=chain,
    )


def _fit_diagram(preset_name: str, diagram: dict[str, Any], locator: str, root: Path | None) -> None:
    """Apply the same per-role boxes the CeTZ layouts use (Tasks 33-36)."""
    chain = _fit_chain(str(root or _project_root()))
    if chain is None:
        return
    nodes = diagram.get("nodes", [])

    if preset_name in {"process", "model"}:
        total = DIAGRAM_TOTAL_CM
        count = len(nodes)
        if preset_name == "model":
            box_w = total * 0.8
        else:
            box_w = (total - 0.55 * (count - 1)) / count
        width_pt, height_pt = _cm(box_w), _cm(1.05)
        for index, node in enumerate(nodes):
            split = 0.55 if node.get("sub") else 1.0
            _check_label(node["label"], width_pt, height_pt * split, 8.0, f"{locator}.nodes[{index}].label", chain)
            if node.get("sub"):
                _check_label(node["sub"], width_pt, height_pt * 0.55, 6.6, f"{locator}.nodes[{index}].sub", chain)
        return

    if preset_name in {"cycle", "hierarchy", "decision_tree", "network"}:
        width_pt, height_pt = _cm(2.55), _cm(0.95)
        for index, node in enumerate(nodes):
            split = 0.55 if node.get("sub") else 1.0
            _check_label(node["label"], width_pt, height_pt * split, 8.0, f"{locator}.nodes[{index}].label", chain)
            if node.get("sub"):
                _check_label(node["sub"], width_pt, height_pt * 0.55, 6.6, f"{locator}.nodes[{index}].sub", chain)
        if preset_name == "decision_tree":
            for index, edge in enumerate(diagram.get("edges", [])):
                if edge.get("label"):
                    _check_label(edge["label"], _cm(2.2), _cm(0.7), 6.4, f"{locator}.edges[{index}].label", chain)
        return

    if preset_name == "timeline":
        events = diagram.get("events", [])
        count = len(events)
        spacing = (DIAGRAM_TOTAL_CM - 1.5) / (count - 1) if count > 1 else 0.0
        slot = spacing - 0.2 if spacing > 0.4 else DIAGRAM_TOTAL_CM - 1.5
        for index, event in enumerate(events):
            _check_label(event["when"], _cm(slot), _cm(0.6), 6.4, f"{locator}.events[{index}].when", chain)
            _check_label(event["label"], _cm(slot), _cm(0.75), 8.0, f"{locator}.events[{index}].label", chain)
            if event.get("sub"):
                _check_label(event["sub"], _cm(slot), _cm(0.6), 6.6, f"{locator}.events[{index}].sub", chain)
        return

    if preset_name == "matrix":
        columns = diagram.get("columns", [])
        cell_w = (DIAGRAM_TOTAL_CM - 2.5) / len(columns)
        for index, column in enumerate(columns):
            _check_label(column, _cm(cell_w), _cm(0.8), 6.4, f"{locator}.columns[{index}]", chain)
        for index, row in enumerate(diagram.get("rows", [])):
            _check_label(row, _cm(2.5), _cm(1.05), 6.4, f"{locator}.rows[{index}]", chain)
        for row_index, row in enumerate(diagram.get("cells", [])):
            for column_index, cell in enumerate(row):
                _check_label(
                    cell, _cm(cell_w), _cm(1.05), 6.4,
                    f"{locator}.cells[{row_index}][{column_index}]", chain,
                )
        return

    if preset_name == "venn":
        sets = diagram.get("sets", [])
        set_w = 2.4 if len(sets) == 2 else 3.0
        for index, item in enumerate(sets):
            _check_label(item["label"], _cm(set_w), _cm(0.55), 6.4, f"{locator}.sets[{index}].label", chain)
        for index, region in enumerate(diagram.get("overlaps", [])):
            _check_label(region["label"], _cm(1.8), _cm(0.55), 6.4, f"{locator}.overlaps[{index}].label", chain)
        return

    if preset_name == "swimlane":
        stages = diagram.get("stages", [])
        cell_w = (DIAGRAM_TOTAL_CM - 2.3) / len(stages)
        for index, stage in enumerate(stages):
            _check_label(stage["label"], _cm(cell_w), _cm(0.8), 6.4, f"{locator}.stages[{index}].label", chain)
        for index, lane in enumerate(diagram.get("lanes", [])):
            _check_label(lane["label"], _cm(2.3), _cm(1.0), 6.4, f"{locator}.lanes[{index}].label", chain)
        for index, node in enumerate(nodes):
            _check_label(node["label"], _cm(cell_w), _cm(1.0), 8.0, f"{locator}.nodes[{index}].label", chain)



def _require(condition: bool, message: str, locator: str, code: str = "SCHEMA_INVALID") -> None:
    if not condition:
        raise BookifyError(code, message, locator)


def _text(value: Any, locator: str) -> str:
    _require(isinstance(value, str) and value.strip() != "", "expected a non-empty string", locator)
    return value


def _chart_text(value: Any, locator: str) -> str:
    text = _text(value, locator)
    for character in text:
        if is_cjk(character):
            raise BookifyError(
                "GLYPH_MISSING",
                f"chart text must stay in the Latin/Vietnamese chain: {character!r}",
                locator,
            )
    return text


def _number(value: Any, locator: str) -> float:
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
        f"non-finite chart value: {value!r}",
        locator,
    )
    return float(value)


def _mapping(value: Any, locator: str) -> dict[str, Any]:
    _require(isinstance(value, dict), "expected an object", locator)
    return value


def _series(chart: dict, preset: presets.ChartPreset, locator: str) -> list[dict]:
    series = chart.get("series")
    _require(isinstance(series, list), "chart needs a series list", f"{locator}.series")
    _require(
        preset.min_series <= len(series) <= preset.max_series,
        f"{preset.kind} needs {preset.min_series}-{preset.max_series} series, got {len(series)}",
        f"{locator}.series",
    )
    seen: set[str] = set()
    for index, item in enumerate(series):
        item = _mapping(item, f"{locator}.series[{index}]")
        series_id = _text(item.get("id"), f"{locator}.series[{index}].id")
        _require(series_id not in seen, f"duplicate series id: {series_id}", f"{locator}.series")
        seen.add(series_id)
        _chart_text(item.get("label"), f"{locator}.series[{index}].label")
    return series


def _categories(chart: dict, preset: presets.ChartPreset, locator: str, *, required: bool = True) -> list[str]:
    categories = chart.get("categories")
    if categories is None and not required:
        return []
    _require(isinstance(categories, list), "chart needs a categories list", f"{locator}.categories")
    if preset.min_categories is not None:
        _require(
            len(categories) >= preset.min_categories,
            f"{preset.kind} needs at least {preset.min_categories} categories, got {len(categories)}",
            f"{locator}.categories",
        )
    if preset.max_categories is not None:
        _require(
            len(categories) <= preset.max_categories,
            f"{preset.kind} needs at most {preset.max_categories} categories, got {len(categories)}",
            f"{locator}.categories",
        )
    for index, category in enumerate(categories):
        _chart_text(category, f"{locator}.categories[{index}]")
    return categories


def _values(
    chart: dict,
    categories: list[str],
    series: list[dict],
    locator: str,
    *,
    allow_null: bool,
) -> list[list[float | None]]:
    values = chart.get("values")
    _require(isinstance(values, list), "chart needs a values matrix", f"{locator}.values")
    _require(
        len(values) == len(categories),
        "one value row per category",
        f"{locator}.values",
    )
    for row_index, row in enumerate(values):
        _require(isinstance(row, list), "each value row must be a list", f"{locator}.values[{row_index}]")
        _require(
            len(row) == len(series),
            "one value per series",
            f"{locator}.values[{row_index}]",
        )
        for column, value in enumerate(row):
            if value is None:
                _require(
                    allow_null,
                    f"{chart['kind']} does not allow a null value",
                    f"{locator}.values[{row_index}][{column}]",
                )
                continue
            _number(value, f"{locator}.values[{row_index}][{column}]")
    return values


def _axis(chart: dict, key: str, locator: str) -> dict[str, Any] | None:
    axis = chart.get(key)
    if axis is None:
        return None
    axis = _mapping(axis, f"{locator}.{key}")
    if "unit" in axis:
        _chart_text(axis["unit"], f"{locator}.{key}.unit")
    for bound in ("min", "max"):
        if bound in axis:
            _number(axis[bound], f"{locator}.{key}.{bound}")
    if "min" in axis and "max" in axis:
        _require(
            axis["min"] < axis["max"],
            "axis min must be below max",
            f"{locator}.{key}",
        )
    return axis


def _within(values: Iterable[float], axis: dict[str, Any] | None, locator: str) -> None:
    if axis is None:
        return
    lower, upper = axis.get("min"), axis.get("max")
    for value in values:
        if lower is not None:
            _require(value >= lower, f"value {value} outside axis below the declared min", locator)
        if upper is not None:
            _require(value <= upper, f"value {value} outside axis above the declared max", locator)


def _source(chart: dict, locator: str) -> None:
    source = chart.get("source")
    _require(isinstance(source, dict), "a non-synthetic chart needs a source", f"{locator}.source")
    _text(source.get("sourceId"), f"{locator}.source.sourceId")
    page = source.get("page")
    _require(
        isinstance(page, int) and not isinstance(page, bool) and page >= 1,
        "source page must be a positive integer",
        f"{locator}.source.page",
    )


def _nulls(values: list[list[float | None]]) -> bool:
    return any(value is None for row in values for value in row)


def plotted_extent(kind: str, values: list[list[float | None]]) -> list[float]:
    """The vertical extent the renderer actually plots for a cumulative chart.

    Stacked bars and areas are drawn from zero to the stack top. Validating the
    raw values alone lets a declared axis clip the plotted top, so the boundary
    and the renderer both measure this shared extent. An area row with a gap is
    not filled, so it contributes no top.
    """
    if kind == "stacked_bar":
        tops = [sum(float(value) for value in row if value is not None) for row in values]
        return [0.0, *tops]
    if kind == "area":
        columns = len(values[0]) if values else 0
        tops = [
            sum(float(value) for value in row)
            for row in values
            if columns and all(value is not None for value in row)
        ]
        return [0.0, *tops]
    raise ValueError(f"no cumulative extent for {kind!r}")


def _points(chart: dict, series: list[dict], locator: str) -> dict[str, Any]:
    points = chart.get("points")
    _require(isinstance(points, list), "chart needs a points matrix", f"{locator}.points")
    _require(len(points) == len(series), "one point row per series", f"{locator}.points")
    kind = chart["kind"]
    for series_index, row in enumerate(points):
        _require(isinstance(row, list), "each point row must be a list", f"{locator}.points[{series_index}]")
        _require(
            3 <= len(row) <= 40,
            "each series needs 3-40 points",
            f"{locator}.points[{series_index}]",
        )
        for point_index, point in enumerate(row):
            point_locator = f"{locator}.points[{series_index}][{point_index}]"
            _require(isinstance(point, list), "each point must be a list", point_locator)
            expected = 3 if kind == "bubble" else 2
            _require(
                len(point) == expected,
                f"a {kind} point needs {expected} numbers",
                point_locator,
            )
            for component, value in enumerate(point):
                _number(value, f"{point_locator}[{component}]")
            if kind == "bubble":
                _require(point[2] > 0, "bubble size must be positive", point_locator)
    return {
        "x": [point[0] for row in points for point in row],
        "y": [point[1] for row in points for point in row],
    }


def _histogram(chart: dict, series: list[dict], locator: str) -> list[float]:
    bins = chart.get("bins")
    _require(isinstance(bins, list) and len(bins) >= 2, "a histogram needs at least two bins", f"{locator}.bins")
    for index, edge in enumerate(bins):
        _number(edge, f"{locator}.bins[{index}]")
        if index:
            _require(bins[index - 1] < edge, "bin edges must strictly increase", f"{locator}.bins[{index}]")
    counts = chart.get("counts")
    _require(isinstance(counts, list), "a histogram needs stored counts", f"{locator}.counts")
    _require(
        len(bins) == len(counts) + 1,
        "len(bins) must equal len(counts) + 1",
        f"{locator}.counts",
    )
    for bin_index, row in enumerate(counts):
        _require(isinstance(row, list), "each count row must be a list", f"{locator}.counts[{bin_index}]")
        _require(len(row) == len(series), "one count per series", f"{locator}.counts[{bin_index}]")
        for column, count in enumerate(row):
            _require(
                isinstance(count, int) and not isinstance(count, bool) and count >= 0,
                f"counts must be non-negative integers: {count!r}",
                f"{locator}.counts[{bin_index}][{column}]",
            )
    return [float(count) for row in counts for count in row]


def _stats(chart: dict, categories: list[str], series: list[dict], locator: str) -> list[float]:
    stats = chart.get("stats")
    _require(isinstance(stats, list), "a box chart needs stored statistics", f"{locator}.stats")
    _require(len(stats) == len(categories), "one statistics row per category", f"{locator}.stats")
    collected: list[float] = []
    for category_index, row in enumerate(stats):
        _require(isinstance(row, list), "each statistics row must be a list", f"{locator}.stats[{category_index}]")
        _require(len(row) == len(series), "one five-number summary per series", f"{locator}.stats[{category_index}]")
        for column, summary in enumerate(row):
            cell = f"{locator}.stats[{category_index}][{column}]"
            _require(isinstance(summary, list) and len(summary) == 5, "a summary is five numbers", cell)
            numbers = [_number(value, f"{cell}[{index}]") for index, value in enumerate(summary)]
            _require(
                numbers == sorted(numbers),
                "a five-number summary must satisfy min <= q1 <= median <= q3 <= max",
                cell,
            )
            collected.extend(numbers)
    return collected


def _samples(chart: dict, categories: list[str], series: list[dict], locator: str) -> list[float]:
    samples = chart.get("samples")
    _require(isinstance(samples, list), "a violin chart needs stored samples", f"{locator}.samples")
    _require(len(samples) == len(categories), "one sample row per category", f"{locator}.samples")
    collected: list[float] = []
    for category_index, row in enumerate(samples):
        _require(isinstance(row, list), "each sample row must be a list", f"{locator}.samples[{category_index}]")
        _require(len(row) == len(series), "one sample group per series", f"{locator}.samples[{category_index}]")
        for column, group in enumerate(row):
            cell = f"{locator}.samples[{category_index}][{column}]"
            _require(isinstance(group, list) and len(group) >= 5, "a violin group needs at least 5 samples", cell)
            numbers = [_number(value, f"{cell}[{index}]") for index, value in enumerate(group)]
            collected.extend(numbers)
    return collected


def validate_chart(block: dict) -> dict:
    """Validate a chart block and return the chart mapping; never a fallback."""
    chart = _mapping(block.get("chart"), f"{block.get('id', 'block')}.chart")
    locator = f"{block.get('id', 'block')}.chart"
    kind = chart.get("kind")
    _require(kind in presets.CHART_PRESETS, f"unknown chart kind: {kind!r}", f"{locator}.kind")
    preset = presets.CHART_PRESETS[kind]

    allowed = set(CHART_COMMON) | set(CHART_PAYLOADS[kind])
    for key in chart:
        _require(
            key in allowed,
            f"chart payload key not allowed for {kind}: {key}",
            f"{locator}.{key}",
        )
    for key in CHART_PAYLOADS[kind]:
        _require(key in chart, f"{kind} needs {key}", f"{locator}.{key}")

    verification = chart.get("verification")
    _require(verification in VERIFICATIONS, f"unsupported verification: {verification!r}", f"{locator}.verification")
    if verification == "synthetic":
        _require("source" not in chart, "a synthetic chart must not claim a source", f"{locator}.source")
        _require(
            not block.get("sourceAnchors"),
            "a synthetic chart must not carry sourceAnchors",
            f"{locator}.sourceAnchors",
        )
        _text(chart.get("notes"), f"{locator}.notes")
    else:
        _source(chart, locator)

    series = _series(chart, preset, locator)
    if "notes" in chart:
        _chart_text(chart["notes"], f"{locator}.notes")

    if kind in {"scatter", "bubble"}:
        coordinates = _points(chart, series, locator)
        x_axis = _axis(chart, "xAxis", locator)
        y_axis = _axis(chart, "axis", locator)
        _within(coordinates["x"], x_axis, f"{locator}.xAxis")
        _within(coordinates["y"], y_axis, f"{locator}.axis")
        return dict(chart)

    if kind == "histogram":
        candidates = _histogram(chart, series, locator)
        _within(candidates, _axis(chart, "axis", locator), f"{locator}.axis")
        return dict(chart)

    categories = _categories(chart, preset, locator)
    if kind == "box":
        candidates = _stats(chart, categories, series, locator)
        _within(candidates, _axis(chart, "axis", locator), f"{locator}.axis")
        return dict(chart)

    if kind == "violin":
        candidates = _samples(chart, categories, series, locator)
        _within(candidates, _axis(chart, "axis", locator), f"{locator}.axis")
        return dict(chart)

    values = _values(chart, categories, series, locator, allow_null=kind in NULL_KINDS)
    if kind in NULL_KINDS and _nulls(values):
        _text(chart.get("notes"), f"{locator}.notes")

    candidates: list[float] = [value for row in values for value in row if value is not None]

    if kind in NON_NEGATIVE_KINDS:
        for row_index, row in enumerate(values):
            for column, value in enumerate(row):
                if value is not None:
                    _require(
                        value >= 0,
                        f"{kind} values must be non-negative: {value}",
                        f"{locator}.values[{row_index}][{column}]",
                    )

    if kind in {"stacked_bar", "area"}:
        # A declared axis must cover the plotted stack, not just each raw value.
        candidates = plotted_extent(kind, values)

    if kind == "heatmap":
        _require(len(values) <= 12, "a heatmap accepts at most 12 rows", f"{locator}.values")

    if kind == "pie":
        _require("hole" in chart, "a pie chart needs a hole value", f"{locator}.hole")
        hole = _number(chart["hole"], f"{locator}.hole")
        _require(0 <= hole <= 0.7, "pie hole must be between 0 and 0.7", f"{locator}.hole")
        for row_index, row in enumerate(values):
            for column, value in enumerate(row):
                _require(value is not None and value >= 0, "pie values must be non-negative", f"{locator}.values[{row_index}][{column}]")
        _require(sum(candidates) > 0, "pie values must sum to more than zero", f"{locator}.values")

    if kind == "radar":
        _require(3 <= len(categories) <= 8, "radar needs 3-8 categories", f"{locator}.categories")

    if kind == "waterfall":
        totals = chart.get("totals")
        _require(isinstance(totals, list), "waterfall needs a totals list", f"{locator}.totals")
        _require(
            len(totals) == len(categories),
            "totals must be parallel to categories",
            f"{locator}.totals",
        )
        _require(all(isinstance(flag, bool) for flag in totals), "totals must be booleans", f"{locator}.totals")
        running = 0.0
        # The plotted geometry is the cumulative extent, not the raw deltas: a
        # -7 loss is a bar from 52 down to 45 and never a negative coordinate.
        extent = [0.0]
        for index, row in enumerate(values):
            value = row[0]
            _require(value is not None, "waterfall rows cannot be null", f"{locator}.values[{index}]")
            if totals[index]:
                _require(
                    math.isclose(value, running, rel_tol=1e-9, abs_tol=1e-9),
                    f"total row {index} must equal the running sum {running:g}",
                    f"{locator}.values[{index}]",
                )
                extent.append(value)
            else:
                running += value
                extent.append(running)
        candidates = extent

    if kind == "error_bar":
        errors = chart.get("errors")
        _require(isinstance(errors, list), "error_bar needs errors", f"{locator}.errors")
        _require(len(errors) == len(values), "errors need one row per category", f"{locator}.errors")
        spread: list[float] = []
        for row_index, row in enumerate(errors):
            _require(isinstance(row, list), "each error row must be a list", f"{locator}.errors[{row_index}]")
            _require(len(row) == len(series), "one error per series", f"{locator}.errors[{row_index}]")
            for column, error in enumerate(row):
                cell = f"{locator}.errors[{row_index}][{column}]"
                if error is None:
                    _require(
                        values[row_index][column] is None,
                        "an error may be null only where the value is null",
                        cell,
                    )
                    continue
                _require(
                    values[row_index][column] is not None,
                    "an error needs a value; a gap keeps a null error so nothing is silently dropped",
                    cell,
                )
                _number(error, cell)
                _require(error >= 0, "errors must be non-negative", cell)
                value = values[row_index][column]
                spread.extend([value - error, value + error])
        candidates.extend(spread)

    _within(candidates, _axis(chart, "axis", locator), f"{locator}.axis")
    return dict(chart)


def _nodes(diagram: dict, preset: presets.DiagramPreset, locator: str) -> list[dict]:
    nodes = diagram.get("nodes")
    _require(isinstance(nodes, list), f"{preset.preset} needs nodes", f"{locator}.nodes")
    if preset.min_nodes is not None:
        _require(
            len(nodes) >= preset.min_nodes,
            f"{preset.preset} needs at least {preset.min_nodes} nodes, got {len(nodes)}",
            f"{locator}.nodes",
        )
    if preset.max_nodes is not None:
        _require(
            len(nodes) <= preset.max_nodes,
            f"{preset.preset} needs at most {preset.max_nodes} nodes, got {len(nodes)}",
            f"{locator}.nodes",
        )
    seen: set[str] = set()
    for index, node in enumerate(nodes):
        node = _mapping(node, f"{locator}.nodes[{index}]")
        node_id = _text(node.get("id"), f"{locator}.nodes[{index}].id")
        _require(node_id not in seen, f"duplicate node id: {node_id}", f"{locator}.nodes")
        seen.add(node_id)
        _text(node.get("label"), f"{locator}.nodes[{index}].label")
        if "sub" in node:
            _text(node["sub"], f"{locator}.nodes[{index}].sub")
    return nodes


def _edges(diagram: dict, nodes: list[dict], locator: str, *, required: bool) -> list[dict]:
    if required:
        _require("edges" in diagram, "this preset needs edges", f"{locator}.edges")
    edges = diagram.get("edges", [])
    _require(isinstance(edges, list), "edges must be a list", f"{locator}.edges")
    known = {node["id"] for node in nodes}
    for index, edge in enumerate(edges):
        edge = _mapping(edge, f"{locator}.edges[{index}]")
        for end in ("from", "to"):
            endpoint = _text(edge.get(end), f"{locator}.edges[{index}].{end}")
            _require(endpoint in known, f"edge endpoint missing: {endpoint}", f"{locator}.edges")
        _require(edge["from"] != edge["to"], "self edges are not supported", f"{locator}.edges")
        if "kind" in edge:
            _require(edge["kind"] in {"arrow", "line"}, f"unsupported edge kind: {edge['kind']!r}", f"{locator}.edges")
    return edges


def _groups(diagram: dict, nodes: list[dict], preset: presets.DiagramPreset, locator: str) -> None:
    groups = diagram.get("groups")
    if not groups:
        return
    _require(preset.allow_groups, f"{preset.preset} does not support groups", f"{locator}.groups")
    known = {node["id"] for node in nodes}
    seen: set[str] = set()
    for index, group in enumerate(groups):
        group = _mapping(group, f"{locator}.groups[{index}]")
        group_id = _text(group.get("id"), f"{locator}.groups[{index}].id")
        _require(group_id not in seen, f"duplicate group id: {group_id}", f"{locator}.groups")
        seen.add(group_id)
        _text(group.get("label"), f"{locator}.groups[{index}].label")
        for member in group.get("nodes", []):
            _require(member in known, f"group member missing: {member}", f"{locator}.groups")


def _tree(edges: list[dict], nodes: list[dict], locator: str) -> None:
    identifiers = [node["id"] for node in nodes]
    incoming = {node_id: 0 for node_id in identifiers}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in identifiers}
    for edge in edges:
        incoming[edge["to"]] += 1
        adjacency[edge["from"]].append(edge["to"])
    roots = [node_id for node_id in identifiers if incoming[node_id] == 0]
    _require(len(roots) == 1, f"a tree needs exactly one root, found {len(roots)}", locator)
    for node_id in identifiers:
        if node_id != roots[0]:
            _require(incoming[node_id] == 1, f"non-root node needs in-degree 1: {node_id}", locator)

    state: dict[str, int] = {}

    def visit(node_id: str) -> None:
        _require(state.get(node_id) != 1, "diagram edges must be acyclic", locator)
        if state.get(node_id) == 2:
            return
        state[node_id] = 1
        for child in adjacency[node_id]:
            visit(child)
        state[node_id] = 2

    for node_id in identifiers:
        visit(node_id)


def _cycle(nodes: list[dict], edges: list[dict], locator: str) -> None:
    identifiers = [node["id"] for node in nodes]
    expected = {
        (identifiers[index], identifiers[(index + 1) % len(identifiers)])
        for index in range(len(identifiers))
    }
    actual = [(edge["from"], edge["to"]) for edge in edges]
    _require(
        len(actual) == len(expected) and set(actual) == expected and len(set(actual)) == len(actual),
        "cycle edges must form one ring in node order",
        f"{locator}.edges",
    )


def validate_diagram(block: dict, *, root: Path | None = None) -> dict:
    """Validate a diagram block and return the diagram mapping; never a fallback."""
    locator = f"{block.get('id', 'block')}.diagram"
    diagram = _mapping(block.get("diagram"), locator)
    preset_name = diagram.get("preset")
    _require(preset_name in presets.DIAGRAM_PRESETS, f"unknown diagram preset: {preset_name!r}", f"{locator}.preset")
    preset = presets.DIAGRAM_PRESETS[preset_name]

    allowed = {"preset", "synthetic"} | set(DIAGRAM_PAYLOADS[preset_name])
    for key in diagram:
        _require(key in allowed, f"diagram payload key not allowed for {preset_name}: {key}", f"{locator}.{key}")
    for key in DIAGRAM_PAYLOADS[preset_name]:
        if key == "groups":
            continue
        _require(key in diagram, f"{preset_name} needs {key}", f"{locator}.{key}")

    synthetic = diagram.get("synthetic", False)
    _require(isinstance(synthetic, bool), "diagram synthetic must be a boolean", f"{locator}.synthetic")
    if synthetic:
        _text(block.get("note"), f"{locator}.note")
        _require(
            not block.get("sourceAnchors"),
            "a synthetic diagram must not carry sourceAnchors",
            f"{locator}.sourceAnchors",
        )

    if preset_name == "timeline":
        events = diagram.get("events")
        _require(isinstance(events, list), "timeline needs events", f"{locator}.events")
        _require(
            preset.min_events <= len(events) <= preset.max_events,
            f"timeline needs {preset.min_events}-{preset.max_events} events",
            f"{locator}.events",
        )
        seen: set[str] = set()
        for index, event in enumerate(events):
            event = _mapping(event, f"{locator}.events[{index}]")
            event_id = _text(event.get("id"), f"{locator}.events[{index}].id")
            _require(event_id not in seen, f"duplicate event id: {event_id}", f"{locator}.events")
            seen.add(event_id)
            _text(event.get("label"), f"{locator}.events[{index}].label")
            _text(event.get("when"), f"{locator}.events[{index}].when")
            if "sub" in event:
                _text(event["sub"], f"{locator}.events[{index}].sub")
        _fit_diagram(preset_name, diagram, locator, root)
        return dict(diagram)

    if preset_name == "matrix":
        rows = diagram.get("rows")
        columns = diagram.get("columns")
        cells = diagram.get("cells")
        _require(isinstance(rows, list), "matrix needs rows", f"{locator}.rows")
        _require(isinstance(columns, list), "matrix needs columns", f"{locator}.columns")
        _require(
            preset.min_rows <= len(rows) <= preset.max_rows,
            f"matrix needs {preset.min_rows}-{preset.max_rows} rows",
            f"{locator}.rows",
        )
        _require(
            preset.min_columns <= len(columns) <= preset.max_columns,
            f"matrix needs {preset.min_columns}-{preset.max_columns} columns",
            f"{locator}.columns",
        )
        for index, row in enumerate(rows):
            _text(row, f"{locator}.rows[{index}]")
        for index, column in enumerate(columns):
            _text(column, f"{locator}.columns[{index}]")
        _require(isinstance(cells, list), "matrix needs cells", f"{locator}.cells")
        _require(len(cells) == len(rows), "matrix needs one cell row per row", f"{locator}.cells")
        for row_index, row in enumerate(cells):
            _require(isinstance(row, list), "each cell row must be a list", f"{locator}.cells[{row_index}]")
            _require(len(row) == len(columns), "one cell per row x column", f"{locator}.cells[{row_index}]")
            for column_index, cell in enumerate(row):
                _text(cell, f"{locator}.cells[{row_index}][{column_index}]")
        _fit_diagram(preset_name, diagram, locator, root)
        return dict(diagram)

    if preset_name == "venn":
        sets = diagram.get("sets")
        _require(isinstance(sets, list), "venn needs sets", f"{locator}.sets")
        _require(
            preset.min_sets <= len(sets) <= preset.max_sets,
            f"venn needs {preset.min_sets}-{preset.max_sets} sets",
            f"{locator}.sets",
        )
        set_ids: set[str] = set()
        for index, item in enumerate(sets):
            item = _mapping(item, f"{locator}.sets[{index}]")
            set_id = _text(item.get("id"), f"{locator}.sets[{index}].id")
            _require(set_id not in set_ids, f"duplicate set id: {set_id}", f"{locator}.sets")
            set_ids.add(set_id)
            _text(item.get("label"), f"{locator}.sets[{index}].label")
        overlaps = diagram.get("overlaps", [])
        _require(isinstance(overlaps, list), "overlaps must be a list", f"{locator}.overlaps")
        _require(len(overlaps) <= preset.max_overlaps, f"venn allows at most {preset.max_overlaps} region labels", f"{locator}.overlaps")
        signatures: set[tuple[str, ...]] = set()
        for index, region in enumerate(overlaps):
            region = _mapping(region, f"{locator}.overlaps[{index}]")
            _text(region.get("id"), f"{locator}.overlaps[{index}].id")
            _text(region.get("label"), f"{locator}.overlaps[{index}].label")
            members = region.get("sets")
            _require(isinstance(members, list) and members, "a region needs its set ids", f"{locator}.overlaps[{index}].sets")
            for member in members:
                _require(member in set_ids, f"region names an unknown set: {member}", f"{locator}.overlaps[{index}].sets")
            signature = tuple(sorted(members))
            _require(signature not in signatures, f"duplicate venn region: {signature}", f"{locator}.overlaps")
            signatures.add(signature)
        _fit_diagram(preset_name, diagram, locator, root)
        return dict(diagram)

    if preset_name == "swimlane":
        lanes = diagram.get("lanes")
        stages = diagram.get("stages")
        _require(isinstance(lanes, list), "swimlane needs lanes", f"{locator}.lanes")
        _require(isinstance(stages, list), "swimlane needs stages", f"{locator}.stages")
        _require(
            preset.min_lanes <= len(lanes) <= preset.max_lanes,
            f"swimlane needs {preset.min_lanes}-{preset.max_lanes} lanes",
            f"{locator}.lanes",
        )
        _require(
            preset.min_stages <= len(stages) <= preset.max_stages,
            f"swimlane needs {preset.min_stages}-{preset.max_stages} stages",
            f"{locator}.stages",
        )
        lane_ids = {_text(_mapping(item, f"{locator}.lanes[{index}]").get("id"), f"{locator}.lanes[{index}].id") for index, item in enumerate(lanes)}
        stage_ids = {_text(_mapping(item, f"{locator}.stages[{index}]").get("id"), f"{locator}.stages[{index}].id") for index, item in enumerate(stages)}
        _require(len(lane_ids) == len(lanes), "duplicate lane id", f"{locator}.lanes")
        _require(len(stage_ids) == len(stages), "duplicate stage id", f"{locator}.stages")
        for index, item in enumerate(lanes):
            _text(item.get("label"), f"{locator}.lanes[{index}].label")
        for index, item in enumerate(stages):
            _text(item.get("label"), f"{locator}.stages[{index}].label")
        nodes = _nodes(diagram, preset, locator)
        occupied: set[tuple[str, str]] = set()
        for index, node in enumerate(nodes):
            lane = _text(node.get("lane"), f"{locator}.nodes[{index}].lane")
            stage = _text(node.get("stage"), f"{locator}.nodes[{index}].stage")
            _require(lane in lane_ids, f"node names an unknown lane: {lane}", f"{locator}.nodes[{index}].lane")
            _require(stage in stage_ids, f"node names an unknown stage: {stage}", f"{locator}.nodes[{index}].stage")
            _require((lane, stage) not in occupied, "at most one node per lane x stage cell", f"{locator}.nodes[{index}]")
            occupied.add((lane, stage))
            _text(node.get("label"), f"{locator}.nodes[{index}].label")
        _fit_diagram(preset_name, diagram, locator, root)
        return dict(diagram)

    nodes = _nodes(diagram, preset, locator)
    edges = _edges(diagram, nodes, locator, required=preset_name in GRAPH_PRESETS)
    _groups(diagram, nodes, preset, locator)

    if preset_name == "cycle":
        _cycle(nodes, edges, locator)
    elif preset_name in {"hierarchy", "decision_tree"}:
        _tree(edges, nodes, locator)
        if preset_name == "decision_tree":
            for index, edge in enumerate(edges):
                _text(edge.get("label"), f"{locator}.edges[{index}].label")
    _fit_diagram(preset_name, diagram, locator, root)
    return dict(diagram)
