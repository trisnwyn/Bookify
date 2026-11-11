# SPEC-figure-engine

Module id: `figure-engine` · depends on: `manuscript-model`, `design-system` · build step 3 · status: approved 2026-11-10.

## Objective

Turn verified chart data and editable diagram geometry into precise vector figures, deterministically and offline. AI may interpret a source chart once; the rendered figure must be a pure function of the stored numbers and geometry, so a rebuild cannot introduce new values or new shapes.

## Tech stack

Matplotlib for charts, emitting SVG (vector, no raster fallback) with a pinned config. CeTZ for diagrams inside the Typst document, driven by stored geometry through a small Typst module. Both are part of the approved target stack; Matplotlib is not yet installed and its version is pinned after toolchain validation.

## Commands (proposed, not implemented)

```bash
uv run bookify figures render --manuscript content/specimen.yaml --out build/figures
uv run bookify figures check --manuscript content/specimen.yaml --json
```

## Project structure

```
src/bookify/figures/
  charts.py                  # grouped_bar -> SVG, deterministic rcParams
  diagrams.py                # geometry -> CeTZ source
  presets.py                 # named chart/diagram presets, one per figure kind
  checks.py                  # data completeness, label coverage
typst/cetz/diagram.typ       # node/edge/groups rendering from geometry
build/figures/<hash>.svg     # disposable outputs, hashed by input
```

## Contracts

`chart` (from the manuscript) — v1 kinds: `grouped_bar` only.

```yaml
chart:
  kind: grouped_bar
  categories: [Alder, Birch, Cedar]
  series: [{ id: likely, label: "Samples recorded" }]
  values: [[72], [64], [58]]        # one row per category, one value per series
  axis: { unit: "%", min: 0, max: 100 }
  source: { sourceId: example-source, page: 7 }
```

Rules: `values` must match categories × series exactly; a `null` value renders as a gap plus a footnote, never as zero; the axis range comes from the declared axis or the data, never from a hard-coded default; every series is labelled directly (no legend by default); bars use greys plus the single accent, never a categorical palette.

`diagram` — v1 presets: `process` (linear/feedback process) and `model` (layered/cycle model).

```yaml
diagram:
  preset: process
  nodes: [{ id: n1, label: "Plan", sub: "definition" }]
  edges: [{ from: n1, to: n2, kind: arrow }]
  groups: [{ id: g1, label: "Act", nodes: [n1, n2] }]
```

Rules: every edge endpoint must exist; labels stay inside their boxes by construction (font size and padding are preset values); no decorative shapes; a reconstructed figure states the reconstruction in its caption, not in the drawing.

## Commands of the boundary

`figures render` is called by `publish build`; it may also run standalone for tests. It never writes into the manuscript.

## Code style

```python
def grouped_bar(chart: ChartSpec, theme: Theme) -> str:
    """Return SVG for a validated grouped-bar chart."""
    require_complete_matrix(chart)          # raises; never drops a category silently
    with deterministic_rcparams(theme):
        fig, ax = plt.subplots(figsize=theme.figure_size)
        ...
    return svg_without_timestamps(fig)
```

Determinism: fixed `svg.hashsalt`, no `DATE`/`CREATOR` metadata, pinned `font.family`, `svg.fonttype = "path"` or an embedded local font, fixed DPI, sorted keys.

## Testing strategy

`pytest` under `tests/figures/`:

- Golden hash: the same chart spec renders byte-identical SVG twice; changing one value changes the hash.
- Data integrity: missing matrix cell, extra series, `null` without a note, and a value outside the axis each fail with the named code or render the documented gap.
- Labels: every bar carries a direct label; no legend is emitted by default.
- Diagram: unknown node in an edge fails; every node is inside its group; render output is stable CeTZ source.
- Visual: rendered specimen page inspected; no clipping, no overlapping labels.

## Boundaries

- Always: consume stored data only; keep outputs hashed and disposable; label directly; state reconstruction in the caption; use the theme's tokens.
- Ask first: adding a chart kind or diagram preset, changing a preset's geometry, switching Matplotlib output backend.
- Never: re-read a slide image at render time; infer missing numbers from a chart; interpolate; add decorative fills or 3-D effects; use a categorical colour palette.

## Success criteria

1. The specimen's grouped-bar chart is regenerated from stored values with a stable hash across two builds.
2. The specimen's process/model diagram is regenerated from stored geometry with a stable CeTZ output.
3. A `null` value is visible as a gap with a note and never becomes zero.
4. No figure kind exists without a preset; a figure with an unknown preset fails.
5. Rendering performs no network or model access.
