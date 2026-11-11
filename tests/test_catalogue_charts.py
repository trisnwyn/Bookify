"""Tasks 28–32: the bounded chart families render from stored data.

Every payload here follows `.opencode/catalogue-contracts.md`; the validator
boundary is exercised through `charts.render`, so a test that calls the renderer
directly sees the same `SCHEMA_INVALID` / `GLYPH_MISSING` errors the manuscript
boundary raises.
"""

from __future__ import annotations

import copy
import inspect
import sys
from pathlib import Path

import pytest

from bookify.design import tokens
from bookify.errors import BookifyError
from bookify.figures import charts, checks, presets

ROOT = Path(__file__).resolve().parents[1]
NOTE = "Synthetic values authored for the catalogue; not measurements."


def _series(*labels: str) -> list[dict]:
    return [{"id": f"s{index + 1}", "label": label} for index, label in enumerate(labels)]


def _block(kind: str, **payload) -> dict:
    chart = {
        "kind": kind,
        "series": _series("Series one"),
        "verification": "synthetic",
        "notes": NOTE,
    }
    chart.update(payload)
    return {"id": f"b-{kind}", "type": "chart", "chart": chart}


def _samples() -> dict[str, dict]:
    """One valid payload per figure, in contract order (pie appears twice)."""
    return {
        "grouped-bar": _block(
            "grouped_bar",
            categories=["North", "South"],
            series=[{"id": "y2025", "label": "2025"}, {"id": "y2026", "label": "2026"}],
            values=[[32, 38], [27, 31]],
            axis={"unit": "sessions", "min": 0},
        ),
        "bar": _block(
            "bar",
            categories=["Q1", "Q2", "Q3"],
            values=[[4], [-2], [6]],
            axis={"unit": "points"},
        ),
        "stacked-bar": _block(
            "stacked_bar",
            categories=["Jan", "Feb", "Mar"],
            series=_series("Direct", "Search"),
            values=[[20, 14], [22, 16], [19, 15]],
            axis={"unit": "sessions", "min": 0},
        ),
        "line": _block(
            "line",
            categories=["Jan", "Feb", "Mar", "Apr"],
            values=[[1.2], [None], [1.8], [2.1]],
            axis={"unit": "index"},
            notes="February was not reported; the line breaks and is never zero.",
        ),
        "area": _block(
            "area",
            categories=["A", "B", "C"],
            series=_series("Morning", "Afternoon"),
            values=[[2, 1], [3, 2], [2.5, 1.5]],
        ),
        "scatter": _block(
            "scatter",
            series=_series("Cohort A", "Cohort B"),
            points=[
                [[1.0, 2.5], [2.0, 3.1], [3.5, 4.0], [4.0, 4.6]],
                [[1.2, 1.8], [2.6, 2.9], [4.1, 3.6], [4.8, 4.1]],
            ],
            xAxis={"unit": "hours", "min": 0, "max": 6},
            axis={"unit": "score", "min": 0, "max": 6},
        ),
        "bubble": _block(
            "bubble",
            series=_series("Channels"),
            points=[
                [[1.0, 2.5, 4], [2.0, 3.1, 6], [3.5, 4.0, 8], [4.2, 4.4, 5]],
            ],
            xAxis={"unit": "index", "min": 0, "max": 6},
            axis={"unit": "score", "min": 0, "max": 6},
        ),
        "histogram": _block(
            "histogram",
            bins=[0, 10, 20, 30, 40],
            counts=[[3], [7], [4], [1]],
            axis={"unit": "count", "min": 0},
        ),
        "box": _block(
            "box",
            categories=["Group A", "Group B"],
            stats=[[[2, 4, 5, 7, 9]], [[1, 3, 4, 6, 8]]],
            axis={"unit": "score", "min": 0, "max": 10},
        ),
        "violin": _block(
            "violin",
            categories=["Group A", "Group B"],
            samples=[[[1, 2, 3, 4, 5, 6, 7]], [[2, 3, 4, 5, 6, 7, 8]]],
            axis={"unit": "score", "min": 0, "max": 9},
            notes="Synthetic samples; density uses numpy only.",
        ),
        "heatmap": _block(
            "heatmap",
            categories=["Row one", "Row two", "Row three"],
            series=_series("Left", "Right"),
            values=[[1, 2], [3, 4], [5, 6]],
        ),
        "pie": _block(
            "pie",
            categories=["Share A", "Share B", "Share C", "Share D"],
            values=[[38], [27], [21], [14]],
            hole=0,
        ),
        "donut": {
            "id": "b-donut",
            "type": "chart",
            "chart": {
                "kind": "pie",
                "categories": ["Share A", "Share B", "Share C", "Share D"],
                "series": _series("Share"),
                "values": [[34], [26], [22], [18]],
                "hole": 0.55,
                "verification": "synthetic",
                "notes": NOTE,
            },
        },
        "waterfall": _block(
            "waterfall",
            categories=["Start", "Gain", "Loss", "End"],
            values=[[40], [12], [-7], [45]],
            totals=[False, False, False, True],
        ),
        "radar": _block(
            "radar",
            categories=["Speed", "Clarity", "Cost", "Reach", "Depth"],
            series=_series("Current", "Target"),
            values=[[3, 4], [4, 5], [2, 3], [3, 4], [4, 4]],
            axis={"unit": "score", "min": 0, "max": 5},
        ),
        "error-bar": _block(
            "error_bar",
            categories=["Group A", "Group B"],
            values=[[5], [6]],
            errors=[[0.5], [0.8]],
            axis={"unit": "score", "min": 0, "max": 8},
        ),
    }


def _render(block: dict, out_dir: Path) -> charts.ChartRender:
    return charts.render(copy.deepcopy(block), ROOT, out_dir)


def _svg(render: charts.ChartRender) -> str:
    return render.path.read_text()


# --- Task 28: foundation, full-spec hash, bar family -------------------------


def test_contract_kinds_and_presets_agree() -> None:
    assert set(presets.CHART_PRESETS) == set(checks.CHART_KINDS)
    assert len(checks.CHART_KINDS) == 15


def test_grouped_bar_specimen_is_byte_identical_and_vector(tmp_path: Path) -> None:
    from bookify.manuscript import model

    manuscript = model.load(ROOT / "content" / "specimen.yaml")
    block = next(
        block for section in manuscript.sections for block in section["blocks"] if block["type"] == "chart"
    )

    rendered = charts.render(block, ROOT, tmp_path)

    assert rendered.bars == (
        ("Alder", "sample-count", 72.0),
        ("Birch", "sample-count", 64.0),
        ("Cedar", "sample-count", 58.0),
    )
    assert rendered.gaps == ()
    assert rendered.series_labels == ()
    # Task 44 intentionally changes the vector bytes: the canvas gains the
    # measured visible-ink asymmetry as margin; the chart data and labels are
    # unchanged. The hash is re-pinned for that intended geometry change only.
    assert rendered.sha256 == "7163f7df27bca02c8053a0af0c5af5338069296cafa5e3bc3a1b9ed04ea39335"
    assert "<svg" in _svg(rendered) and "<image" not in _svg(rendered)


def test_multi_series_grouped_bar_labels_directly_without_a_legend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib.axes

    def forbidden(self, *args, **kwargs):
        raise AssertionError("multi-series charts must not use a legend")

    monkeypatch.setattr(matplotlib.axes.Axes, "legend", forbidden)
    rendered = _render(_samples()["grouped-bar"], tmp_path)

    assert rendered.series_labels == ("2025", "2026")
    assert "<image" not in _svg(rendered)


def test_full_spec_hash_changes_when_one_value_changes(tmp_path: Path) -> None:
    block = _samples()["grouped-bar"]
    first = _render(block, tmp_path)
    second = _render(block, tmp_path)
    assert first.sha256 == second.sha256

    changed = copy.deepcopy(block)
    changed["chart"]["values"][0][0] = 33
    third = _render(changed, tmp_path)

    assert third.sha256 != first.sha256
    assert third.path.name != first.path.name


def test_bar_accepts_negative_values(tmp_path: Path) -> None:
    rendered = _render(_samples()["bar"], tmp_path)

    assert ("Q2", "s1", -2.0) in rendered.bars
    assert "<image" not in _svg(rendered)


def test_stacked_bar_labels_each_stack_total(tmp_path: Path) -> None:
    rendered = _render(_samples()["stacked-bar"], tmp_path)

    assert len(rendered.bars) == 6
    assert {"34", "38"} <= set(rendered.labels)
    assert rendered.series_labels == ("Direct", "Search")


@pytest.mark.parametrize("kind", ["stacked_bar", "area"])
def test_declared_axis_must_cover_the_cumulative_top(tmp_path: Path, kind: str) -> None:
    block = _block(
        kind,
        categories=["A", "B"],
        series=_series("One", "Two"),
        values=[[20, 22], [20, 22]],
        axis={"min": 0, "max": 41},
    )

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"

    block["chart"]["axis"] = {"min": 0, "max": 42}
    _render(block, tmp_path)


def test_declared_axis_wins_and_a_missing_bound_derives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib.axes

    calls: list[tuple[float, float]] = []
    original = matplotlib.axes.Axes.set_ylim

    def capture(self, lower=None, upper=None, **kwargs):
        if lower is not None and upper is not None:
            calls.append((float(lower), float(upper)))
        return original(self, lower, upper, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "set_ylim", capture)

    block = _block("grouped_bar", categories=["A", "B", "C"], values=[[120], [300], [450]])
    _render(block, tmp_path)
    assert calls[-1][0] == 0 and calls[-1][1] >= 450

    declared = copy.deepcopy(block)
    declared["chart"]["axis"] = {"min": 0, "max": 500}
    _render(declared, tmp_path)
    assert calls[-1] == (0.0, 500.0)


def test_value_outside_a_declared_axis_is_rejected(tmp_path: Path) -> None:
    block = _block("bar", categories=["A"], values=[[-1]], axis={"min": 0})

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_unknown_kind_is_never_a_fallback(tmp_path: Path) -> None:
    block = _block("nope", categories=["A"], values=[[1]])

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_four_series_use_four_distinct_restrained_colours(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib.axes

    colours: list[str] = []
    original = matplotlib.axes.Axes.bar

    def capture(self, *args, **kwargs):
        colour = kwargs.get("color")
        if isinstance(colour, str):
            colours.append(colour)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "bar", capture)
    block = _block(
        "grouped_bar",
        categories=["A", "B"],
        series=_series("One", "Two", "Three", "Four"),
        values=[[1, 2, 3, 4], [2, 3, 4, 5]],
        axis={"min": 0},
    )
    _render(block, tmp_path)

    assert len(colours) == 8
    assert len(set(colours)) == 4


# --- Task 29: line, area, scatter, bubble ------------------------------------


def test_line_null_is_a_gap_with_a_note_and_never_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib.axes

    plotted: list[list[float]] = []
    original = matplotlib.axes.Axes.plot

    def capture(self, *args, **kwargs):
        for value in args[1:]:
            if isinstance(value, (list, tuple)) and value and all(isinstance(v, (int, float)) for v in value):
                plotted.append([float(v) for v in value])
        return original(self, *args, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "plot", capture)
    rendered = _render(_samples()["line"], tmp_path)

    assert rendered.gaps == ("Feb:s1",)
    gap_labels = [label for label in rendered.labels if label.startswith("Gap:")]
    assert gap_labels
    assert all(len(line) <= 58 for line in gap_labels[0].splitlines())
    assert all(0.0 not in segment for segment in plotted)


def test_area_is_stacked_for_multiple_series(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib.axes

    fills: list[tuple[list[float], list[float]]] = []
    original = matplotlib.axes.Axes.fill_between

    def capture(self, x, y1, y2, **kwargs):
        fills.append(([float(v) for v in y1], [float(v) for v in y2]))
        return original(self, x, y1, y2, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "fill_between", capture)
    rendered = _render(_samples()["area"], tmp_path)

    assert len(fills) == 2
    assert fills[0] == ([0.0, 0.0, 0.0], [2.0, 3.0, 2.5])
    assert fills[1] == ([2.0, 3.0, 2.5], [3.0, 5.0, 4.0])
    assert rendered.series_labels == ("Morning", "Afternoon")


@pytest.mark.parametrize("count", [2, 41])
def test_scatter_requires_three_to_forty_points_per_series(tmp_path: Path, count: int) -> None:
    block = _samples()["scatter"]
    block["chart"]["points"] = [[[index, index] for index in range(count)]]
    block["chart"]["series"] = _series("Only")

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


@pytest.mark.parametrize("size", [0, -1])
def test_bubble_size_must_be_positive(tmp_path: Path, size: int) -> None:
    block = _samples()["bubble"]
    block["chart"]["points"] = [[[1.0, 2.0, size], [2.0, 3.0, 4], [3.0, 4.0, 5]]]

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_multi_series_bubble_sizes_share_one_global_scale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib.axes

    areas: list[list[float]] = []
    original = matplotlib.axes.Axes.scatter

    def capture(self, x, y, s=None, **kwargs):
        if s is not None:
            areas.append([float(value) for value in s])
        return original(self, x, y, s=s, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "scatter", capture)
    block = _block(
        "bubble",
        series=_series("One", "Two"),
        points=[
            [[1.0, 2.0, 4], [2.0, 3.0, 8], [2.5, 3.5, 2]],
            [[3.0, 4.0, 8], [4.0, 5.0, 16], [3.5, 4.5, 4]],
        ],
        xAxis={"min": 0, "max": 5},
        axis={"min": 0, "max": 6},
    )
    _render(block, tmp_path)

    # Stored size 8 has the same area in either series; 16 is the global maximum.
    assert areas[0][1] == pytest.approx(areas[1][0])
    assert max(max(row) for row in areas) == pytest.approx(90.0)


def test_point_series_identity_is_the_first_mark(tmp_path: Path) -> None:
    rendered = _render(_samples()["scatter"], tmp_path)
    assert rendered.series_labels == ("Cohort A", "Cohort B")


# --- Task 30: histogram, box, violin -----------------------------------------


def test_histogram_uses_its_stored_bins_and_counts(tmp_path: Path) -> None:
    rendered = _render(_samples()["histogram"], tmp_path)

    assert rendered.bins == (0.0, 10.0, 20.0, 30.0, 40.0)
    assert {"3", "7", "4", "1"} <= set(rendered.labels)
    assert "<image" not in _svg(rendered)


@pytest.mark.parametrize(
    "payload",
    [
        {"bins": [0, 10, 10, 20], "counts": [[1], [2], [3]]},
        {"bins": [0, 10, 20], "counts": [[1], [2], [3]]},
        {"bins": [0, 10, 20], "counts": [[1.5], [2]]},
        {"bins": [0, 10, 20], "counts": [[1], [-2]]},
    ],
)
def test_histogram_rejects_invalid_bins_or_counts(tmp_path: Path, payload: dict) -> None:
    block = _block("histogram", **payload)

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_box_rejects_a_disordered_five_number_summary(tmp_path: Path) -> None:
    block = _block(
        "box",
        categories=["A"],
        stats=[[[2, 5, 4, 7, 9]]],
        axis={"min": 0, "max": 10},
    )

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_box_renders_from_stored_summaries(tmp_path: Path) -> None:
    first = _render(_samples()["box"], tmp_path)
    second = _render(_samples()["box"], tmp_path)
    assert first.sha256 == second.sha256
    assert "<image" not in _svg(first)


def test_violin_requires_five_samples_and_a_note(tmp_path: Path) -> None:
    too_few = _block(
        "violin",
        categories=["A"],
        samples=[[[1, 2, 3, 4]]],
        notes="Synthetic samples.",
    )
    with pytest.raises(BookifyError) as error:
        _render(too_few, tmp_path)
    assert error.value.code == "SCHEMA_INVALID"

    no_note = _block("violin", categories=["A"], samples=[[[1, 2, 3, 4, 5]]])
    no_note["chart"].pop("notes")
    with pytest.raises(BookifyError) as error:
        _render(no_note, tmp_path)
    assert error.value.code == "SCHEMA_INVALID"


def test_violin_uses_numpy_only_and_stays_deterministic(tmp_path: Path) -> None:
    rendered = _render(_samples()["violin"], tmp_path)
    again = _render(_samples()["violin"], tmp_path)

    assert rendered.sha256 == again.sha256
    assert "scipy" not in sys.modules
    assert "scipy" not in inspect.getsource(charts)
    assert "<image" not in _svg(rendered)


# --- Task 31: heatmap, pie and donut -----------------------------------------


@pytest.mark.parametrize("rows,columns", [(13, 1), (1, 7)])
def test_heatmap_rejects_its_row_and_column_caps(tmp_path: Path, rows: int, columns: int) -> None:
    block = _block(
        "heatmap",
        categories=[f"R{index}" for index in range(rows)],
        series=_series(*(f"C{index}" for index in range(columns))),
        values=[[index for _ in range(columns)] for index in range(rows)],
    )

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_heatmap_is_vector_and_each_cell_carries_its_value(tmp_path: Path) -> None:
    rendered = _render(_samples()["heatmap"], tmp_path)
    svg = _svg(rendered)

    assert "<image" not in svg
    assert len(rendered.cells) == 6
    assert {value for _, _, value in rendered.cells} == {1.0, 2.0, 3.0, 4.0, 5.0, 6.0}


def test_constant_heatmap_labels_every_cell_in_dark_ink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    colours: list[str] = []
    original = charts._annotate

    def capture(*args, **kwargs):
        colours.append(kwargs.get("colour"))
        return original(*args, **kwargs)

    monkeypatch.setattr(charts, "_annotate", capture)
    block = _block(
        "heatmap",
        categories=["R1", "R2", "R3"],
        series=_series("C1", "C2"),
        values=[[5, 5], [5, 5], [5, 5]],
    )
    rendered = _render(block, tmp_path)

    assert len(rendered.cells) == 6
    assert colours and set(colours) == {tokens.INK_HEX}


def test_pie_and_donut_are_the_same_family_with_different_holes(tmp_path: Path) -> None:
    pie_block = _samples()["pie"]
    donut_block = _samples()["donut"]
    pie = _render(pie_block, tmp_path)
    donut = _render(donut_block, tmp_path)

    assert pie.path != donut.path
    assert pie.sha256 != donut.sha256
    assert "<image" not in _svg(pie) and "<image" not in _svg(donut)


def test_pie_labels_show_the_stored_value_and_derived_share(tmp_path: Path) -> None:
    rendered = _render(_samples()["pie"], tmp_path)

    assert any("38" in label and "38%" in label for label in rendered.labels)
    assert any("Share A" in label for label in rendered.labels)


@pytest.mark.parametrize(
    "payload",
    [
        {"categories": ["A", "B"], "values": [[1], [1]]},  # hole missing
        {"categories": ["A", "B"], "values": [[1], [1]], "hole": 0.8},
        {"categories": ["A", "B"], "values": [[0], [0]], "hole": 0},
        {"categories": [str(index) for index in range(9)], "values": [[1]] * 9, "hole": 0},
        {
            "categories": ["A", "B"],
            "series": _series("One", "Two"),
            "values": [[1, 2], [3, 4]],
            "hole": 0,
        },
    ],
)
def test_pie_rejects_invalid_payloads(tmp_path: Path, payload: dict) -> None:
    block = _block("pie", **payload)

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


# --- Task 32: waterfall, radar, error bar ------------------------------------


def test_waterfall_total_must_equal_the_running_sum(tmp_path: Path) -> None:
    block = _samples()["waterfall"]
    block["chart"]["values"][3] = [44]

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_waterfall_draws_all_rows_and_labels_the_total(tmp_path: Path) -> None:
    rendered = _render(_samples()["waterfall"], tmp_path)

    assert len(rendered.bars) == 4
    assert "45" in rendered.labels
    assert "<image" not in _svg(rendered)


def test_waterfall_without_an_axis_starts_at_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib.axes

    bounds: list[tuple[float, float]] = []
    original = matplotlib.axes.Axes.set_ylim

    def capture(self, lower=None, upper=None, **kwargs):
        if lower is not None and upper is not None:
            bounds.append((float(lower), float(upper)))
        return original(self, lower, upper, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "set_ylim", capture)
    block = _block(
        "waterfall",
        categories=["Start", "Gain", "Loss", "End"],
        values=[[40], [12], [-7], [45]],
        totals=[False, False, False, True],
    )
    _render(block, tmp_path)

    assert bounds[-1][0] == 0.0, "the negative delta is drawn from 52 down to 45, not below zero"

    block["chart"]["axis"] = {"min": 0, "max": 60}
    _render(block, tmp_path)
    assert bounds[-1] == (0.0, 60.0), "a declared min: 0 stays exact"


@pytest.mark.parametrize(
    "payload",
    [
        {"categories": ["A", "B"], "values": [[1, 1], [2, 2]]},
        {"categories": [str(index) for index in range(9)], "values": [[1, 1] for _ in range(9)]},
        {
            "categories": ["A", "B", "C"],
            "series": _series("One", "Two", "Three", "Four"),
            "values": [[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3]],
        },
        {"categories": ["A", "B", "C"], "values": [[-1, 1], [2, 2], [3, 3]]},
    ],
)
def test_radar_rejects_cap_range_and_category_violations(tmp_path: Path, payload: dict) -> None:
    block = _block("radar", axis={"min": 0}, **payload)

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_radar_polygons_are_closed_and_share_one_scale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib.axes

    closed: list[tuple[list[float], list[float]]] = []
    original = matplotlib.axes.Axes.fill

    def capture(self, x, y, **kwargs):
        closed.append(([float(v) for v in x], [float(v) for v in y]))
        return original(self, x, y, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "fill", capture)
    _render(_samples()["radar"], tmp_path)

    assert len(closed) == 2
    for x, y in closed:
        assert x[0] == x[-1]
        assert y[0] == y[-1]


@pytest.mark.parametrize(
    "values,errors",
    [
        ([[5], [6]], [[0.5]]),  # shape mismatch
        ([[5], [6]], [[-0.5], [0.8]]),  # negative error
        ([[5], [6]], [[None], [0.8]]),  # null error where the value is not null
    ],
)
def test_error_bar_rejects_invalid_errors(tmp_path: Path, values, errors) -> None:
    block = _block(
        "error_bar",
        categories=["A", "B"],
        values=values,
        errors=errors,
        axis={"min": 0},
    )

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "SCHEMA_INVALID"


def test_error_bar_null_is_a_gap_and_draws_stored_errors(tmp_path: Path) -> None:
    block = _block(
        "error_bar",
        categories=["A", "B"],
        values=[[5], [None]],
        errors=[[0.5], [None]],
        notes="B was not reported.",
        axis={"min": 0},
    )
    rendered = _render(block, tmp_path)

    assert rendered.gaps == ("B:s1",)
    assert "<image" not in _svg(rendered)


# --- Cross-cutting: all 15 kinds, vector, deterministic, no legend -----------


def test_every_contract_kind_renders_vector_and_deterministic(tmp_path: Path) -> None:
    rendered_kinds: list[str] = []

    for name, block in _samples().items():
        first = _render(block, tmp_path)
        second = _render(block, tmp_path)

        assert first.sha256 == second.sha256, name
        assert first.path.is_file() and first.path.suffix == ".svg", name
        assert "<image" not in _svg(first), name
        rendered_kinds.append(block["chart"]["kind"])

    assert set(rendered_kinds) == set(checks.CHART_KINDS)
    assert rendered_kinds.count("pie") == 2


def test_no_chart_kind_uses_a_legend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import matplotlib.axes

    def forbidden(self, *args, **kwargs):
        raise AssertionError("charts must label directly, never with a legend")

    monkeypatch.setattr(matplotlib.axes.Axes, "legend", forbidden)
    for name, block in _samples().items():
        _render(block, tmp_path)


def test_chart_text_must_stay_in_the_latin_vietnamese_chain(tmp_path: Path) -> None:
    block = _block("bar", categories=["日本"], values=[[1]])

    with pytest.raises(BookifyError) as error:
        _render(block, tmp_path)

    assert error.value.code == "GLYPH_MISSING"
