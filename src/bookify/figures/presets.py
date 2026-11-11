"""Named figure presets and their binding caps.

Sizes are points; colours mirror the theme tokens. The registries are the one
place a chart kind or diagram preset, its payload shape and its caps are named.
`figures.checks` validates against these entries; renderers resolve through them
and never invent a fallback.
"""

from __future__ import annotations

from dataclasses import dataclass

from bookify.design import tokens

CHART_FIGSIZE = (4.7, 2.45)
CHART_UNIT_WIDTH = 0.8
DIAGRAM_WIDTH_PT = 430
SERIES_COLOURS = (
    tokens.GREY_3_HEX,
    tokens.ACCENT_HEX,
    tokens.GREY_1_HEX,
    tokens.ACCENT_TINT_3_HEX,
)
GRID_COLOUR = tokens.GREY_3_HEX
LABEL_COLOUR = tokens.GREY_1_HEX
LABEL_FLOOR_PT = 5.5
LABEL_STEP_PT = 0.5


@dataclass(frozen=True)
class ChartPreset:
    """One bounded chart family: shape, series/category caps, figure size."""

    kind: str
    shape: str
    min_series: int
    max_series: int
    min_categories: int | None
    max_categories: int | None
    size: tuple[float, float] = CHART_FIGSIZE


@dataclass(frozen=True)
class DiagramPreset:
    """One bounded diagram preset: layout, node caps and optional payload caps."""

    preset: str
    layout: str
    min_nodes: int | None
    max_nodes: int | None
    allow_groups: bool
    min_events: int | None = None
    max_events: int | None = None
    min_rows: int | None = None
    max_rows: int | None = None
    min_columns: int | None = None
    max_columns: int | None = None
    min_sets: int | None = None
    max_sets: int | None = None
    max_overlaps: int | None = None
    min_lanes: int | None = None
    max_lanes: int | None = None
    min_stages: int | None = None
    max_stages: int | None = None
    width_pt: float = DIAGRAM_WIDTH_PT
    label_floor_pt: float = LABEL_FLOOR_PT
    label_step_pt: float = LABEL_STEP_PT


CHART_PRESETS: dict[str, ChartPreset] = {
    preset.kind: preset
    for preset in (
        ChartPreset("grouped_bar", "matrix", 1, 4, 1, None),
        ChartPreset("bar", "matrix", 1, 1, 1, None),
        ChartPreset("stacked_bar", "matrix", 2, 4, 1, None),
        ChartPreset("line", "matrix", 1, 4, 1, None),
        ChartPreset("area", "matrix", 1, 4, 1, None),
        ChartPreset("scatter", "points", 1, 3, None, None),
        ChartPreset("bubble", "points", 1, 3, None, None),
        ChartPreset("histogram", "histogram", 1, 3, None, None),
        ChartPreset("box", "box", 1, 3, 1, None),
        ChartPreset("violin", "samples", 1, 3, 1, None),
        ChartPreset("heatmap", "matrix", 1, 6, 1, 12),
        ChartPreset("pie", "pie", 1, 1, 2, 8),
        ChartPreset("waterfall", "matrix", 1, 1, 1, None),
        ChartPreset("radar", "matrix", 1, 3, 3, 8),
        ChartPreset("error_bar", "matrix", 1, 4, 1, None),
    )
}

DIAGRAM_PRESETS: dict[str, DiagramPreset] = {
    preset.preset: preset
    for preset in (
        DiagramPreset("process", "row", 2, 6, True),
        DiagramPreset("model", "layers", 2, 6, True),
        DiagramPreset("cycle", "ring", 3, 8, False),
        DiagramPreset("hierarchy", "tree", 2, 9, False),
        DiagramPreset("decision_tree", "tree", 2, 9, False),
        DiagramPreset("network", "circle", 3, 10, False),
        DiagramPreset(
            "timeline", "timeline", None, None, False,
            min_events=2, max_events=8,
        ),
        DiagramPreset(
            "matrix", "grid", None, None, False,
            min_rows=2, max_rows=4, min_columns=2, max_columns=4,
        ),
        DiagramPreset(
            "venn", "venn", None, None, False,
            min_sets=2, max_sets=3, max_overlaps=4,
        ),
        DiagramPreset(
            "swimlane", "lanes", 1, 24, False,
            min_lanes=2, max_lanes=4, min_stages=2, max_stages=6,
        ),
    )
}
