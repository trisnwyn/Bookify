"""Fifteen bounded chart families from stored values, as deterministic vector SVG.

`checks.validate_chart` is the one validation boundary: every shape, cap, range,
order and null rule is enforced there before a mark is drawn. `render` then
resolves a kind through the registry below, draws from the validated spec and
hashes the whole spec (values included) into the SVG filename.

Text is converted to paths (`svg.fonttype = "path"`) so the SVG is
self-contained and needs no font when embedded. A null value breaks a line, area
or bar and is reported as a gap; it never becomes zero.
"""

from __future__ import annotations

import hashlib
import json
import math
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from bookify.design import tokens
from bookify.errors import BookifyError
from bookify.figures import checks, presets

FONT_DIR = "assets/fonts"
AXIS_MARGIN = 0.05
# Visible-ink balancing: measure the same white canvas the SVG is saved from.
# `tight_layout` already returns equal box margins, but a rotated y-axis label's
# text box reserves blank ascent/descent space, so the ink a reader sees still
# sits off-centre. Rasterise at a high, fixed DPI and balance the pixels.
INK_THRESHOLD = 245
MEASURE_DPI = 300
VALUE_FONTSIZE = 9.0
SERIES_FONTSIZE = 8.6
COUNT_FONTSIZE = 8.4
GAP_FONTSIZE = 8.6
LINE_WIDTH = 1.2
MARKER_SIZE = 3.0
HEAT_LOW = "#f7f7f7"
HEAT_CELL_EDGE = "#ffffff"


@dataclass(frozen=True)
class ChartRender:
    """One rendered chart and the deterministic facts a test can assert on."""

    block_id: str
    path: Path
    sha256: str
    bars: tuple[tuple[str, str, float | None], ...]
    gaps: tuple[str, ...]
    labels: tuple[str, ...] = ()
    series_labels: tuple[str, ...] = ()
    cells: tuple[tuple[str, str, float], ...] = ()
    bins: tuple[float, ...] = ()


@dataclass
class _Drawn:
    """Mutable drawing record while one figure is composed."""

    bars: list[tuple[str, str, float | None]] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    series_labels: list[str] = field(default_factory=list)
    cells: list[tuple[str, str, float]] = field(default_factory=list)
    bins: list[float] = field(default_factory=list)


def _register_fonts(root: Path) -> None:
    for path in sorted((root / FONT_DIR).glob("Spectral-*.ttf")):
        font_manager.fontManager.addfont(str(path))


def _setup(root: Path) -> None:
    _register_fonts(root)
    plt.rcParams.update(
        {
            "font.family": "Spectral",
            "font.size": 10.5,
            "svg.fonttype": "path",
            "svg.hashsalt": "bookify-chart-v1",
            "axes.edgecolor": tokens.INK_HEX,
            "axes.linewidth": 0.5,
            "text.color": tokens.INK_HEX,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            # The balanced canvas is the saved canvas; never re-crop it on save.
            "savefig.bbox": None,
        }
    )


def _series_colour(index: int) -> str:
    """Greys plus the single accent; a fourth series gets the accent tint.

    `presets.SERIES_COLOURS` is contract-owned and currently names three
    colours; the fourth-family fallback is recorded as a request in
    `.opencode/catalogue-charts.md` rather than editing the contract file.
    """
    if index < len(presets.SERIES_COLOURS):
        return presets.SERIES_COLOURS[index]
    return tokens.ACCENT_TINT_3_HEX


def _value_text(value: float) -> str:
    return f"{float(value):g}"


def _annotate(
    axes: Axes,
    x: float,
    y: float,
    text: str,
    *,
    colour: str = tokens.INK_HEX,
    weight: str = "normal",
    size: float = VALUE_FONTSIZE,
    ha: str = "center",
    va: str = "bottom",
    dx: float = 0.0,
    dy: float = 2.0,
    mask: bool = False,
    xycoords: str = "data",
) -> None:
    options: dict[str, Any] = {}
    if mask:
        options["bbox"] = {
            "boxstyle": "round,pad=0.18",
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.88,
        }
    axes.annotate(
        text,
        (x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        xycoords=xycoords,
        ha=ha,
        va=va,
        fontsize=size,
        color=colour,
        fontweight=weight,
        annotation_clip=False,
        zorder=5,
        **options,
    )


def _series_note(
    drawn: _Drawn,
    axes: Axes,
    x: float,
    y: float,
    text: str,
    *,
    dx: float = -4.0,
    dy: float = 6.0,
    ha: str = "right",
    va: str = "bottom",
    mask: bool = False,
) -> None:
    _annotate(
        axes, x, y, text,
        colour=tokens.INK_HEX, weight="bold", size=SERIES_FONTSIZE,
        ha=ha, va=va, dx=dx, dy=dy, mask=mask,
    )
    drawn.labels.append(text)
    drawn.series_labels.append(text)


def _bounds(
    axis: dict[str, Any] | None,
    values: Iterable[float],
    locator: str,
    *,
    headroom: float = AXIS_MARGIN,
) -> tuple[float, float]:
    """Declared bounds win; otherwise derive the missing side from the data."""
    numbers = [float(value) for value in values]
    axis = axis or {}
    has_min, has_max = "min" in axis, "max" in axis
    if has_min and has_max:
        lower, upper = float(axis["min"]), float(axis["max"])
        if not math.isfinite(lower) or not math.isfinite(upper) or lower >= upper:
            raise BookifyError("SCHEMA_INVALID", "axis bounds are not a finite ordered pair", locator)
        return lower, upper

    data_min = min(numbers) if numbers else 0.0
    data_max = max(numbers) if numbers else 1.0
    lower = float(axis["min"]) if has_min else min(0.0, data_min)
    if has_max:
        upper = float(axis["max"])
    else:
        span = data_max - lower
        upper = data_max + (span if span > 0 else 1.0) * headroom
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise BookifyError("SCHEMA_INVALID", "non-finite axis bound", locator)
    if upper <= lower:
        upper = lower + 1.0
    return lower, upper


def _style_axes(
    axes: Axes,
    *,
    y_bounds: tuple[float, float] | None = None,
    unit: str | None = None,
    grid: str = "y",
) -> None:
    if y_bounds is not None:
        axes.set_ylim(y_bounds[0], y_bounds[1])
    if grid in {"y", "both"}:
        axes.yaxis.grid(True, color=presets.GRID_COLOUR, linewidth=0.3, alpha=0.75, zorder=1)
    if grid == "both":
        axes.xaxis.grid(True, color=presets.GRID_COLOUR, linewidth=0.3, alpha=0.75, zorder=1)
    axes.set_axisbelow(True)
    if unit:
        axes.set_ylabel(unit)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)


def _align_edge_ticks(axes: Axes, bounds: tuple[float, float] | None = None) -> None:
    """Keep the first/last numeric tick label inside the figure edge."""
    lower, upper = bounds if bounds is not None else axes.get_xlim()
    for label in axes.get_xticklabels():
        position = float(label.get_position()[0])
        if position <= lower + 1e-9:
            label.set_horizontalalignment("left")
        elif position >= upper - 1e-9:
            label.set_horizontalalignment("right")


def _gap_note(axes: Axes, chart: dict, drawn: _Drawn) -> None:
    if not drawn.gaps:
        return
    text = f"Gap: {chart['notes']}" if chart.get("notes") else "Gap: value not reported"
    wrapped = textwrap.fill(text, width=58)
    _annotate(
        axes, 0.012, 0.985, wrapped,
        colour=presets.LABEL_COLOUR, size=GAP_FONTSIZE,
        ha="left", va="top", dx=0.0, dy=0.0, mask=True,
        xycoords="axes fraction",
    )
    drawn.labels.append(wrapped)


def _draw_bars(spec: dict, axes: Axes, *, stacked: bool) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    series = spec["series"]
    values = spec["values"]
    count = len(series)
    unit_width = presets.CHART_UNIT_WIDTH
    width = unit_width / count if not stacked else unit_width * 0.78

    if stacked:
        bottoms = [0.0] * len(categories)
        for series_index, item in enumerate(series):
            colour = _series_colour(series_index)
            label_x = label_y = None
            for category_index, category in enumerate(categories):
                value = values[category_index][series_index]
                if value is None:
                    drawn.gaps.append(f"{category}:{item['id']}")
                    continue
                value = float(value)
                bottom = bottoms[category_index]
                axes.bar(
                    category_index, value, bottom=bottom, width=width,
                    color=colour, edgecolor="none", zorder=2,
                )
                drawn.bars.append((category, item["id"], value))
                bottoms[category_index] = bottom + value
                if category_index == len(categories) - 1:
                    label_x, label_y = category_index, bottom + value / 2
            if count > 1 and label_x is not None and label_y is not None:
                _annotate(
                    axes, label_x + 0.46, label_y, item["label"],
                    colour=tokens.INK_HEX, weight="bold", size=SERIES_FONTSIZE,
                    ha="left", va="center", dx=0.0, dy=0.0,
                )
                drawn.labels.append(item["label"])
                drawn.series_labels.append(item["label"])
        for index, total in enumerate(bottoms):
            _annotate(
                axes, index, total, _value_text(total),
                colour=tokens.INK_HEX, weight="bold", size=VALUE_FONTSIZE,
                ha="center", va="bottom", dx=0.0, dy=2.0,
            )
            drawn.labels.append(_value_text(total))
        bounds = _bounds(spec.get("axis"), checks.plotted_extent("stacked_bar", values), "chart.axis")
    else:
        for series_index, item in enumerate(series):
            colour = _series_colour(series_index)
            weight = "normal" if series_index == 0 else "bold"
            label_colour = presets.LABEL_COLOUR if series_index == 0 else tokens.INK_HEX
            label_x = label_y = None
            for category_index, category in enumerate(categories):
                value = values[category_index][series_index]
                if value is None:
                    drawn.gaps.append(f"{category}:{item['id']}")
                    continue
                value = float(value)
                offset = category_index + (series_index - (count - 1) / 2) * width
                axes.bar(
                    offset, value, width=width,
                    color=colour, edgecolor="none", zorder=2,
                )
                va = "bottom" if value >= 0 else "top"
                dy = 2.0 if value >= 0 else -2.0
                _annotate(
                    axes, offset, value, _value_text(value),
                    colour=label_colour, weight=weight, size=VALUE_FONTSIZE,
                    ha="center", va=va, dx=0.0, dy=dy,
                )
                drawn.labels.append(_value_text(value))
                drawn.bars.append((category, item["id"], value))
                label_x, label_y = offset, value
            if count > 1 and label_x is not None and label_y is not None:
                _annotate(
                    axes, label_x, label_y, item["label"],
                    colour=tokens.INK_HEX, weight="bold", size=SERIES_FONTSIZE,
                    ha="center", va="bottom", dx=0.0, dy=18.0,
                )
                drawn.labels.append(item["label"])
                drawn.series_labels.append(item["label"])
        bounds = _bounds(
            spec.get("axis"),
            [value for row in values for value in row if value is not None],
            "chart.axis",
            headroom=0.14 if count > 1 else AXIS_MARGIN,
        )

    axes.set_xticks(range(len(categories)), categories)
    _style_axes(axes, y_bounds=bounds, unit=spec.get("axis", {}).get("unit"))
    _gap_note(axes, spec, drawn)
    return drawn


def _draw_line(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    series = spec["series"]
    values = spec["values"]
    numbers: list[float] = []

    for series_index, item in enumerate(series):
        colour = _series_colour(series_index)
        segments: list[tuple[list[int], list[float]]] = []
        xs: list[int] = []
        ys: list[float] = []
        for index, row in enumerate(values):
            value = row[series_index]
            if value is None:
                drawn.gaps.append(f"{categories[index]}:{item['id']}")
                if xs:
                    segments.append((xs, ys))
                    xs, ys = [], []
                continue
            value = float(value)
            xs.append(index)
            ys.append(value)
            numbers.append(value)
        if xs:
            segments.append((xs, ys))
        for segment_x, segment_y in segments:
            axes.plot(
                segment_x, segment_y, color=colour,
                linewidth=LINE_WIDTH, marker="o", markersize=MARKER_SIZE,
                markerfacecolor=colour, markeredgecolor="none", zorder=2,
            )
        if len(series) > 1 and segments:
            last_x, last_y = segments[-1][0][-1], segments[-1][1][-1]
            _series_note(drawn, axes, last_x, last_y, item["label"], dx=-4.0, dy=6.0)

    axes.set_xticks(range(len(categories)), categories)
    _style_axes(
        axes,
        y_bounds=_bounds(spec.get("axis"), numbers, "chart.axis", headroom=0.10),
        unit=spec.get("axis", {}).get("unit"),
    )
    _gap_note(axes, spec, drawn)
    return drawn


def _draw_area(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    series = spec["series"]
    values = spec["values"]
    count = len(series)

    matrix: list[list[float | None]] = [
        [None if row[index] is None else float(row[index]) for index in range(count)]
        for row in values
    ]
    valid = [all(row[index] is not None for index in range(count)) for row in matrix]
    for category_index, row in enumerate(values):
        for series_index, item in enumerate(series):
            if row[series_index] is None:
                drawn.gaps.append(f"{categories[category_index]}:{item['id']}")

    for series_index, item in enumerate(series):
        colour = _series_colour(series_index)
        label_point: tuple[int, float] | None = None
        # Build each contiguous valid run so a gap is never filled as zero.
        run: list[int] = []
        for category_index in range(len(categories) + 1):
            if category_index < len(categories) and valid[category_index]:
                run.append(category_index)
                continue
            if run:
                bottoms: list[float] = []
                tops: list[float] = []
                for index in run:
                    bottom = 0.0
                    for previous in range(series_index):
                        value = matrix[index][previous]
                        bottom += float(value) if value is not None else 0.0
                    value = matrix[index][series_index]
                    top = bottom + (float(value) if value is not None else 0.0)
                    bottoms.append(bottom)
                    tops.append(top)
                axes.fill_between(
                    run, bottoms, tops, color=colour, alpha=0.35,
                    linewidth=0, zorder=1 + series_index,
                )
                axes.plot(run, tops, color=colour, linewidth=0.8, zorder=2 + series_index)
                label_point = (run[-1], tops[-1])
                run = []
        if count > 1 and label_point is not None:
            _series_note(
                drawn, axes, label_point[0], label_point[1], item["label"],
                dx=-4.0, dy=5.0,
            )

    axes.set_xticks(range(len(categories)), categories)
    _style_axes(
        axes,
        y_bounds=_bounds(spec.get("axis"), checks.plotted_extent("area", values), "chart.axis", headroom=0.10),
        unit=spec.get("axis", {}).get("unit"),
    )
    _gap_note(axes, spec, drawn)
    return drawn


def _draw_points(spec: dict, axes: Axes, *, bubble: bool) -> _Drawn:
    drawn = _Drawn()
    series = spec["series"]
    points = spec["points"]
    all_x: list[float] = []
    all_y: list[float] = []
    # Bubble area must encode the stored size consistently across series, so
    # one global maximum scales every point rather than each series separately.
    global_largest = (
        max(float(point[2]) for row in points for point in row) if bubble else 1.0
    )

    for series_index, item in enumerate(series):
        colour = _series_colour(series_index)
        xs = [float(point[0]) for point in points[series_index]]
        ys = [float(point[1]) for point in points[series_index]]
        all_x.extend(xs)
        all_y.extend(ys)
        if bubble:
            sizes = [float(point[2]) for point in points[series_index]]
            areas = [90.0 * (size / global_largest) for size in sizes]
            axes.scatter(
                xs, ys, s=areas, color=colour, alpha=0.72,
                edgecolors=colour, linewidths=0.4, zorder=2,
            )
        else:
            axes.scatter(
                xs, ys, s=16, color=colour, alpha=0.8,
                edgecolors="white", linewidths=0.4, zorder=2,
            )
        if len(series) > 1:
            if series_index == 0:
                dx, dy, ha, va = -8.0, 8.0, "right", "bottom"
            elif series_index == 1:
                dx, dy, ha, va = 8.0, -8.0, "left", "top"
            else:
                dx, dy, ha, va = 8.0, 8.0, "left", "bottom"
            _series_note(
                drawn, axes, xs[0], ys[0], item["label"],
                dx=dx, dy=dy, ha=ha, va=va, mask=True,
            )

    x_axis = spec.get("xAxis", {})
    y_axis = spec.get("axis", {})
    x_bounds = _bounds(x_axis, all_x, "chart.xAxis")
    axes.set_xlim(*x_bounds)
    _align_edge_ticks(axes, x_bounds)
    _style_axes(
        axes,
        y_bounds=_bounds(y_axis, all_y, "chart.axis"),
        unit=y_axis.get("unit"),
        grid="both",
    )
    if x_axis.get("unit"):
        axes.set_xlabel(x_axis["unit"])
    return drawn


def _draw_histogram(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    bins = [float(edge) for edge in spec["bins"]]
    counts = spec["counts"]
    series = spec["series"]
    count = len(series)
    widths = [bins[index + 1] - bins[index] for index in range(len(bins) - 1)]
    centres = [(bins[index] + bins[index + 1]) / 2 for index in range(len(bins) - 1)]

    for series_index, item in enumerate(series):
        colour = _series_colour(series_index)
        heights = [float(row[series_index]) for row in counts]
        positions = [
            centres[index] + (series_index - (count - 1) / 2) * (widths[index] / count)
            for index in range(len(centres))
        ]
        axes.bar(
            positions, heights,
            width=[width * 0.9 / count for width in widths],
            align="center", color=colour, edgecolor="none", zorder=2,
        )
        for position, height in zip(positions, heights):
            _annotate(
                axes, position, height, _value_text(height),
                colour=presets.LABEL_COLOUR if series_index == 0 else tokens.INK_HEX,
                weight="normal" if series_index == 0 else "bold",
                size=COUNT_FONTSIZE, ha="center", va="bottom", dx=0.0, dy=2.0,
            )
            drawn.labels.append(_value_text(height))
        if count > 1:
            _annotate(
                axes, positions[0], heights[0], item["label"],
                colour=tokens.INK_HEX, weight="bold", size=SERIES_FONTSIZE,
                ha="center", va="bottom", dx=0.0, dy=14.0,
            )
            drawn.labels.append(item["label"])
            drawn.series_labels.append(item["label"])

    drawn.bins.extend(bins)
    axes.set_xticks(bins)
    axes.set_xlim(bins[0], bins[-1])
    _align_edge_ticks(axes, (bins[0], bins[-1]))
    _style_axes(
        axes,
        y_bounds=_bounds(
            spec.get("axis"),
            [0.0, *[float(value) for row in counts for value in row]],
            "chart.axis",
        ),
        unit=spec.get("axis", {}).get("unit"),
    )
    axes.yaxis.set_major_locator(MaxNLocator(integer=True))
    return drawn


def _draw_box(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    series = spec["series"]
    stats = spec["stats"]
    count = len(series)
    width = 0.8 / count
    numbers: list[float] = []

    for series_index, item in enumerate(series):
        colour = _series_colour(series_index)
        summaries: list[dict] = []
        positions: list[float] = []
        for category_index in range(len(categories)):
            low, q1, median, q3, high = [float(value) for value in stats[category_index][series_index]]
            numbers.extend([low, q1, median, q3, high])
            summaries.append(
                {
                    "med": median,
                    "q1": q1,
                    "q3": q3,
                    "whislo": low,
                    "whishi": high,
                    "fliers": [],
                }
            )
            positions.append(
                category_index + (series_index - (count - 1) / 2) * width
            )
        axes.bxp(
            summaries,
            positions=positions,
            widths=width * 0.7,
            patch_artist=True,
            showfliers=False,
            manage_ticks=False,
            boxprops={"facecolor": colour, "edgecolor": tokens.INK_HEX, "linewidth": 0.6, "alpha": 0.55},
            medianprops={"color": tokens.INK_HEX, "linewidth": 1.0},
            whiskerprops={"color": tokens.INK_HEX, "linewidth": 0.5},
            capprops={"color": tokens.INK_HEX, "linewidth": 0.5},
            zorder=2,
        )
        if count > 1:
            _annotate(
                axes, positions[0], summaries[0]["whishi"], item["label"],
                colour=tokens.INK_HEX, weight="bold", size=SERIES_FONTSIZE,
                ha="center", va="bottom", dx=0.0, dy=8.0,
            )
            drawn.labels.append(item["label"])
            drawn.series_labels.append(item["label"])

    axes.set_xticks(range(len(categories)), categories)
    _style_axes(
        axes,
        y_bounds=_bounds(spec.get("axis"), numbers, "chart.axis", headroom=0.12 if count > 1 else AXIS_MARGIN),
        unit=spec.get("axis", {}).get("unit"),
    )
    return drawn


def _silverman_density(samples: Sequence[float], grid: np.ndarray) -> np.ndarray:
    """Fixed Gaussian KDE with Silverman's bandwidth; numpy only."""
    values = np.asarray(samples, dtype=float)
    count = values.size
    deviation = float(values.std(ddof=1)) if count > 1 else 0.0
    if deviation > 0:
        bandwidth = 1.06 * deviation * count ** (-0.2)
    else:
        span = float(grid[-1] - grid[0])
        bandwidth = max(span, 1.0) / 64.0
    z = (grid[:, None] - values[None, :]) / bandwidth
    return np.exp(-0.5 * z * z).sum(axis=1) / (count * bandwidth * math.sqrt(2.0 * math.pi))


def _draw_violin(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    series = spec["series"]
    samples = spec["samples"]
    count = len(series)
    width = 0.8 / count

    flattened = [float(value) for row in samples for group in row for value in group]
    low, high = min(flattened), max(flattened)
    span = high - low
    pad = span * 0.12 if span > 0 else 1.0
    grid = np.linspace(low - pad, high + pad, 64)

    densities: dict[tuple[int, int], np.ndarray] = {}
    for category_index in range(len(categories)):
        for series_index in range(count):
            densities[(category_index, series_index)] = _silverman_density(
                samples[category_index][series_index], grid
            )
    largest = max(float(np.max(density)) for density in densities.values()) or 1.0

    for series_index, item in enumerate(series):
        colour = _series_colour(series_index)
        for category_index in range(len(categories)):
            density = densities[(category_index, series_index)]
            half = (density / largest) * (width * 0.42)
            position = category_index + (series_index - (count - 1) / 2) * width
            axes.fill_betweenx(
                grid, position - half, position + half,
                color=colour, alpha=0.42, linewidth=0, zorder=2,
            )
            axes.plot(position - half, grid, color=colour, linewidth=0.35, zorder=3)
            axes.plot(position + half, grid, color=colour, linewidth=0.35, zorder=3)
        if count > 1:
            _annotate(
                axes, 0.0 + (series_index - (count - 1) / 2) * width, high + pad,
                item["label"],
                colour=tokens.INK_HEX, weight="bold", size=SERIES_FONTSIZE,
                ha="center", va="bottom", dx=0.0, dy=4.0,
            )
            drawn.labels.append(item["label"])
            drawn.series_labels.append(item["label"])

    axes.set_xticks(range(len(categories)), categories)
    _style_axes(
        axes,
        y_bounds=_bounds(spec.get("axis"), [low, high], "chart.axis", headroom=0.12 if count > 1 else AXIS_MARGIN),
        unit=spec.get("axis", {}).get("unit"),
    )
    return drawn


def _draw_heatmap(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    series = spec["series"]
    values = [[float(value) for value in row] for row in spec["values"]]
    rows, columns = len(categories), len(series)
    grid = np.asarray(values, dtype=float)
    lowest, highest = float(grid.min()), float(grid.max())
    spread = highest - lowest
    cmap = LinearSegmentedColormap.from_list("bookify_heat", (HEAT_LOW, tokens.ACCENT_HEX))

    axes.pcolormesh(
        np.arange(columns + 1), np.arange(rows + 1), grid,
        cmap=cmap, edgecolors=HEAT_CELL_EDGE, linewidth=0.8, zorder=2,
    )
    for row_index, row in enumerate(values):
        for column_index, value in enumerate(row):
            # A constant heatmap has no gradient; intensity 0 keeps the value
            # ink dark on the near-white low end instead of white on white.
            intensity = (value - lowest) / spread if spread > 0 else 0.0
            colour = "#ffffff" if intensity > 0.55 else tokens.INK_HEX
            _annotate(
                axes, column_index + 0.5, row_index + 0.5, _value_text(value),
                colour=colour, size=COUNT_FONTSIZE, ha="center", va="center",
                dx=0.0, dy=0.0,
            )
            drawn.labels.append(_value_text(value))
            drawn.cells.append((categories[row_index], series[column_index]["id"], value))

    axes.set_xlim(0, columns)
    axes.set_ylim(rows, 0)
    axes.set_xticks([index + 0.5 for index in range(columns)], [item["label"] for item in series])
    axes.set_yticks([index + 0.5 for index in range(rows)], categories)
    axes.tick_params(length=0)
    for spine in axes.spines.values():
        spine.set_visible(False)
    if spec.get("axis", {}).get("unit"):
        axes.set_ylabel(spec["axis"]["unit"])
    drawn.series_labels.extend(item["label"] for item in series)
    return drawn


def _draw_pie(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    values = [float(row[0]) for row in spec["values"]]
    total = sum(values)
    hole = float(spec["hole"])
    labels = [
        f"{category}\n{_value_text(value)} ({value / total * 100:.0f}%)"
        for category, value in zip(categories, values)
    ]
    colours = [_series_colour(index) for index in range(len(categories))]
    wedgeprops: dict[str, Any] = {
        "edgecolor": HEAT_CELL_EDGE,
        "linewidth": 1.0,
    }
    if hole > 0:
        wedgeprops["width"] = 1.0 - hole
    axes.pie(
        values,
        colors=colours,
        startangle=90,
        counterclock=False,
        labels=labels,
        labeldistance=1.06,
        textprops={"fontsize": VALUE_FONTSIZE, "color": tokens.INK_HEX},
        wedgeprops=wedgeprops,
        normalize=True,
    )
    axes.set_aspect("equal")
    axes.axis("off")
    drawn.labels.extend(labels)
    return drawn


def _draw_waterfall(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    series = spec["series"][0]
    values = [float(row[0]) for row in spec["values"]]
    totals = spec["totals"]
    running = 0.0
    levels: list[float] = []

    for index, (category, value, is_total) in enumerate(zip(categories, values, totals)):
        if is_total:
            bottom, height, colour = 0.0, value, tokens.ACCENT_HEX
            level = value
        else:
            bottom, height = running, value
            colour = presets.SERIES_COLOURS[0] if value >= 0 else presets.LABEL_COLOUR
            level = running + value
        axes.bar(
            index, height, bottom=bottom, width=0.6,
            color=colour, edgecolor="none", zorder=2,
        )
        drawn.bars.append((category, series["id"], value))
        end = bottom + height
        va = "bottom" if height >= 0 else "top"
        dy = 2.0 if height >= 0 else -2.0
        _annotate(
            axes, index, end, _value_text(value),
            colour=tokens.INK_HEX, weight="bold" if is_total else "normal",
            size=VALUE_FONTSIZE, ha="center", va=va, dx=0.0, dy=dy,
        )
        drawn.labels.append(_value_text(value))
        running = level
        levels.append(level)
        if index < len(categories) - 1:
            axes.plot(
                [index + 0.3, index + 0.7], [level, level],
                color=presets.GRID_COLOUR, linewidth=0.6,
                linestyle=(0, (2, 2)), zorder=1,
            )

    axes.set_xticks(range(len(categories)), categories)
    _style_axes(
        axes,
        y_bounds=_bounds(spec.get("axis"), [0.0, *levels], "chart.axis"),
        unit=spec.get("axis", {}).get("unit"),
    )
    return drawn


def _draw_radar(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    series = spec["series"]
    values = spec["values"]
    count = len(categories)
    angles = np.linspace(0, 2 * math.pi, count, endpoint=False)
    closed = np.concatenate([angles, angles[:1]])
    numbers = [float(value) for row in values for value in row]
    lower, upper = _bounds(spec.get("axis"), [0.0, *numbers], "chart.axis")

    axes.set_theta_offset(math.pi / 2)
    axes.set_theta_direction(-1)
    for series_index, item in enumerate(series):
        colour = _series_colour(series_index)
        radii = [float(row[series_index]) for row in values]
        radii_closed = np.asarray(radii + radii[:1], dtype=float)
        axes.plot(
            closed, radii_closed, color=colour, linewidth=1.1,
            marker="o", markersize=2.5, markerfacecolor=colour,
            markeredgecolor="none", zorder=3,
        )
        axes.fill(closed, radii_closed, color=colour, alpha=0.12, zorder=2)
        spoke = series_index % count
        inward = {
            0: (8.0, 8.0, "left", "bottom"),
            1: (-8.0, -8.0, "right", "top"),
            2: (-8.0, 8.0, "right", "bottom"),
            3: (8.0, 8.0, "left", "bottom"),
            4: (8.0, -8.0, "left", "top"),
        }
        dx, dy, ha, va = inward.get(spoke, (8.0, 8.0, "left", "bottom"))
        _annotate(
            axes, closed[spoke], radii_closed[spoke], item["label"],
            colour=tokens.INK_HEX, weight="bold", size=SERIES_FONTSIZE,
            ha=ha, va=va, dx=dx, dy=dy, mask=True,
        )
        drawn.labels.append(item["label"])
        drawn.series_labels.append(item["label"])

    axes.set_xticks(angles, categories)
    axes.set_ylim(lower, upper)
    ticks = [lower + (upper - lower) * fraction for fraction in (0.25, 0.5, 0.75, 1.0)]
    axes.set_yticks(ticks)
    axes.set_yticklabels([])
    axes.tick_params(axis="y", length=0, pad=0.5)
    axes.tick_params(axis="x", labelsize=8.6, colors=tokens.INK_HEX, pad=2.0)
    axes.grid(True, color=presets.GRID_COLOUR, linewidth=0.4, alpha=0.85)
    axes.spines["polar"].set_color(presets.GRID_COLOUR)
    axes.spines["polar"].set_linewidth(0.5)
    if spec.get("axis", {}).get("unit"):
        axes.set_xlabel(spec["axis"]["unit"], fontsize=SERIES_FONTSIZE, color=presets.LABEL_COLOUR, labelpad=6)
    return drawn


def _draw_error_bar(spec: dict, axes: Axes) -> _Drawn:
    drawn = _Drawn()
    categories = spec["categories"]
    series = spec["series"]
    values = spec["values"]
    errors = spec["errors"]
    count = len(series)
    width = 0.8 / count
    numbers: list[float] = []

    for series_index, item in enumerate(series):
        colour = _series_colour(series_index)
        first = None
        for category_index, category in enumerate(categories):
            value = values[category_index][series_index]
            if value is None:
                drawn.gaps.append(f"{category}:{item['id']}")
                continue
            value = float(value)
            error = float(errors[category_index][series_index])
            position = category_index + (series_index - (count - 1) / 2) * width
            axes.errorbar(
                position, value, yerr=error, fmt="o",
                color=colour, ecolor=colour, elinewidth=0.9,
                capsize=3, capthick=0.9, markersize=4, zorder=2,
            )
            numbers.extend([value - error, value + error])
            if count == 1:
                _annotate(
                    axes, position, value + error, _value_text(value),
                    colour=tokens.INK_HEX, size=COUNT_FONTSIZE,
                    ha="center", va="bottom", dx=0.0, dy=3.0,
                )
                drawn.labels.append(_value_text(value))
            if first is None:
                first = (position, value + error)
        if count > 1 and first is not None:
            _series_note(drawn, axes, first[0], first[1], item["label"], dx=0.0, dy=8.0, ha="center")

    axes.set_xticks(range(len(categories)), categories)
    _style_axes(
        axes,
        y_bounds=_bounds(spec.get("axis"), [*numbers, *[value for row in values for value in row if value is not None]], "chart.axis", headroom=0.10 if count > 1 else AXIS_MARGIN),
        unit=spec.get("axis", {}).get("unit"),
    )
    _gap_note(axes, spec, drawn)
    return drawn


RenderFunc = Callable[[dict, Axes], _Drawn]

_RENDERERS: dict[str, RenderFunc] = {
    "grouped_bar": lambda spec, axes: _draw_bars(spec, axes, stacked=False),
    "bar": lambda spec, axes: _draw_bars(spec, axes, stacked=False),
    "stacked_bar": lambda spec, axes: _draw_bars(spec, axes, stacked=True),
    "line": _draw_line,
    "area": _draw_area,
    "scatter": lambda spec, axes: _draw_points(spec, axes, bubble=False),
    "bubble": lambda spec, axes: _draw_points(spec, axes, bubble=True),
    "histogram": _draw_histogram,
    "box": _draw_box,
    "violin": _draw_violin,
    "heatmap": _draw_heatmap,
    "pie": _draw_pie,
    "waterfall": _draw_waterfall,
    "radar": _draw_radar,
    "error_bar": _draw_error_bar,
}

_MISSING = set(checks.CHART_KINDS) - set(_RENDERERS)
if _MISSING:  # pragma: no cover - a programming error, not an input error
    raise RuntimeError(f"chart renderers missing: {sorted(_MISSING)}")


def _digest(spec: dict) -> str:
    """Hash the whole validated spec, so a changed value changes the filename."""
    payload = json.dumps(
        spec, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _visible_ink_margins(figure: Figure) -> tuple[float, float]:
    """Left/right visible-ink margins of the rendered canvas, in inches.

    A matplotlib text bbox is not the ink bbox: a rotated label's box reserves
    blank space above and below the glyphs, so `tight_layout` can leave equal
    box margins while the visible ink sits several points off-centre. The
    figure is rasterised at a fixed high DPI and the outermost non-white pixels
    are measured, which is what the reader and the catalogue geometry check see.
    """
    dpi = figure.dpi
    figure.set_dpi(MEASURE_DPI)
    try:
        figure.canvas.draw()
        pixels = np.asarray(figure.canvas.buffer_rgba())[..., :3]
        ink = np.any(pixels < INK_THRESHOLD, axis=2)
    finally:
        figure.set_dpi(dpi)
    columns = np.flatnonzero(ink.any(axis=0))
    if columns.size == 0:  # pragma: no cover - every chart kind draws a mark
        raise RuntimeError("chart has no visible ink to centre")
    width = ink.shape[1]
    return columns[0] / MEASURE_DPI, (width - 1 - columns[-1]) / MEASURE_DPI


def _balance_horizontal_ink(figure: Figure, axes: Axes) -> None:
    """Grow the shorter horizontal canvas side so the visible ink is centred.

    The canvas is only ever grown; no artist moves relative to the ink, no mark
    is rescaled or cropped, and there is no per-kind or per-figure offset. The
    axes position is rewritten in absolute inches so the added white space goes
    entirely to the shorter side while the drawn content keeps its size.
    """
    left, right = _visible_ink_margins(figure)
    difference = abs(left - right)
    if difference <= 1e-9:
        return

    width, height = figure.get_size_inches()
    position = axes.get_position()
    axes_left = position.x0 * width
    axes_width = position.width * width
    # A larger right margin means the ink sits left of centre; grow the left
    # side and shift the content right by the same amount. Otherwise grow right.
    shift = difference if right > left else 0.0
    width += difference
    figure.set_size_inches(width, height, forward=True)
    axes.set_position(
        [
            (axes_left + shift) / width,
            position.y0,
            axes_width / width,
            position.height,
        ]
    )


def render(block: dict, root: Path, out_dir: Path) -> ChartRender:
    """Render one validated chart block; an unknown kind is an error, never a fallback."""
    spec = checks.validate_chart(block)
    kind = spec["kind"]
    preset = presets.CHART_PRESETS[kind]
    renderer = _RENDERERS.get(kind)
    if renderer is None:
        raise BookifyError("SCHEMA_INVALID", f"no renderer for chart kind: {kind!r}", f"{block['id']}.chart.kind")

    _setup(root)
    projection = {"projection": "polar"} if kind == "radar" else None
    figure, axes = plt.subplots(figsize=preset.size, subplot_kw=projection if projection else None)
    try:
        drawn = renderer(spec, axes)
        figure.tight_layout(pad=0.3)
        if kind in {"scatter", "bubble", "histogram"}:
            # The locator can choose new ticks during layout; align the finals.
            _align_edge_ticks(axes)
        # Last layout step: the visible ink, not the text boxes, must be centred.
        _balance_horizontal_ink(figure, axes)
        digest = _digest(spec)
        target = out_dir / f"chart-{block['id']}-{digest}.svg"
        out_dir.mkdir(parents=True, exist_ok=True)
        figure.savefig(target, format="svg", metadata={"Date": None})
    finally:
        plt.close(figure)

    return ChartRender(
        block_id=block["id"],
        path=target,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        bars=tuple(drawn.bars),
        gaps=tuple(drawn.gaps),
        labels=tuple(drawn.labels),
        series_labels=tuple(drawn.series_labels),
        cells=tuple(drawn.cells),
        bins=tuple(drawn.bins),
    )
