# SPEC-visual-catalogue — v1 visual extension

Status: **proposed 2026-11-10, awaiting human approval**. This extends the approved v1 modules; it is not a new capability. No new module id, service, CLI command or capability map. The boundaries in `SPEC-INDEX.md` remain in force until this spec is approved. No product code, dependency, asset or plan is produced at this stage.

## Objective

Produce one offline, deterministic A4 PDF, `dist/catalogue.pdf`, that lets a reader review the extended visual vocabulary in one pass: 15 bounded chart families, 10 diagram presets and 4 illustration families. Every figure carries a centred description; every provenance fact stays visible; every named family is present in the PDF and in a coverage table.

The catalogue is a review instrument for the reusable skill, not a factual chapter and not a claim to cover every possible visualisation.

## Assumptions

1. The catalogue is a demonstration document: chart values are synthetic, diagrams are illustrative schematics, illustrations are curated classifications, not evidence claims.
2. Existing module boundaries and the closed v1 manuscript schema stay. Schema additions are optional and additive; `schemaVersion` remains `"1.0"`.
3. The global `pdf-book-design` skill is a design reference only. Its left-aligned caption rule is superseded by the confirmed instruction to centre figure descriptions; the global skill is not edited.
4. The specimen and trial builds keep their page counts (6 and 3), page text and existing text probes. Their grouped-bar chart has one series, so the multi-series label change below does not alter it.
5. No new runtime dependency, no new font, no paid image generation, and no network access in `build` or `verify`.
6. Catalogue section titles stay short enough to appear as one contents line: the existing contents parser is line-based.

## Bounded inventory

This is the complete scope. A family not listed here is out of scope and needs a new spec; it is not "to be added later" by implication.

### Charts — 15 families, 16 figures

| Kind id | Payload beyond the envelope | Rules |
| --- | --- | --- |
| `grouped_bar` | `categories`, `series` 1–4, `values` | Existing contract retained; the single-series specimen output is unchanged. Multi-series bars are grouped and take direct series labels (no legend), which affects only new multi-series figures. |
| `bar` | `categories`, `series` exactly 1, `values` | One bar per category; negative values allowed. |
| `stacked_bar` | `categories`, `series` 2–4, `values` | Values ≥ 0; cumulative segments; stack total labelled. |
| `line` | `categories`, `series` 1–4, `values` | `null` is a gap with a note, never zero. |
| `area` | `categories`, `series` 1–4, `values` | Values ≥ 0; stacked when more than one series. |
| `scatter` | `series` 1–3, `points` | `[x, y]`; 3–40 points per series; numeric `xAxis`. |
| `bubble` | `series` 1–3, `points` | `[x, y, size]`; `size > 0`; 3–40 points per series. |
| `histogram` | `bins`, `series` 1–3, `counts` | Bin edges strictly increasing, `len(bins) = len(counts) + 1`; counts are stored non-negative integers, never binned at render. |
| `box` | `categories`, `series` 1–3, `stats` | One five-number summary per category; `min ≤ q1 ≤ median ≤ q3 ≤ max`; outliers optional. |
| `violin` | `categories`, `series` 1–3, `samples` | ≥ 5 stored samples per group; fixed Gaussian KDE; `notes` required. |
| `heatmap` | `categories` (rows), `series` (columns) 1–6, `values` | 1–12 rows × 1–6 columns; vector cells; each cell carries its value. |
| `pie` | `categories` 2–8, `series` exactly 1, `values`, `hole` | Values ≥ 0, sum > 0; `hole` 0–0.7; one family, two figures: pie (`hole: 0`) and donut (`hole > 0`). |
| `waterfall` | `categories`, `series` exactly 1, `values`, `totals` | `totals` is parallel to `categories`; `values` are deltas, and a total row must equal the running sum. |
| `radar` | `categories` 3–8, `series` 1–3, `values` | Values ≥ 0; closed polygons; one shared scale. |
| `error_bar` | `categories`, `series` 1–4, `values`, `errors` | `errors` ≥ 0, same shape as `values`; `null` only where the value is `null`. |

**Chart rules (all kinds).** `values` is a matrix whose rows are categories and whose columns are series, except for the named payloads above. Every number is finite. `null` is allowed only in matrix `values` for `grouped_bar`, `bar`, `stacked_bar`, `line`, `area` and `error_bar`; it renders a gap and requires `notes`. Declared axis bounds win; a missing bound is derived from the data; `min < max`; a value outside a declared bound fails. Caps in the table are binding; exceeding one is `SCHEMA_INVALID`. Series identity is direct (last mark for bars/lines/areas, first mark for point/distribution kinds, slice for pie, spoke for radar); no legend. The palette is greys plus the single accent, never a categorical palette. Output is vector SVG only, with no `<image>` element: the heatmap uses vector cell primitives, not `imshow`. The violin density uses numpy only (already a dependency), with Silverman bandwidth and a fixed 64-point grid; no scipy. Pie labels show the stored value and its derived share.

### Diagrams — 10 presets, 10 figures

| Preset | Payload | Rules |
| --- | --- | --- |
| `process` | `nodes` 2–6, `edges`, `groups`? | Row layout; forward and feedback edges; groups label phases. |
| `model` | `nodes` 2–6, `edges`, `groups`? | Vertical layers; approved id retained; catalogue display label is "Layered model". |
| `cycle` | `nodes` 3–8, `edges` | One ring in node order; exactly one incoming and one outgoing edge per node. |
| `hierarchy` | `nodes` 2–9, `edges` | One root; every other node has in-degree 1; acyclic; no groups. |
| `decision_tree` | `nodes` 2–9, `edges` with `label` | Tree rules; every edge carries its branch condition. |
| `network` | `nodes` 3–10, `edges` | Deterministic circular layout; arbitrary non-self edges; no groups. |
| `timeline` | `events` 2–8 | `{id, label, sub?, when}`; horizontal; labels alternate above and below. |
| `matrix` | `rows` 2–4, `columns` 2–4, `cells` | Complete grid; one label per row × column cell. |
| `venn` | `sets` 2–3, `overlaps`? | Fixed 2-set and 3-set geometry; up to four region labels. |
| `swimlane` | `lanes` 2–4, `stages` 2–6, `nodes` | At most one node per lane × stage cell; no edges. |

**Diagram rules (all presets).** Node and edge ids are unique; every edge endpoint exists; no self-edges; group members exist. Labels are fitted inside their boxes by a deterministic stepwise size reduction (0.5 pt steps, floor 5.5 pt); a label that cannot fit is `SCHEMA_INVALID`, never clipped silently. Layout stays a pure function of stored geometry in `typst/cetz/`; Python only validates and serialises. `process` and `model` keep their current rendered geometry.

### Illustrations — 4 curation families, 4 figures

| Family | Record `kind` | Source |
| --- | --- | --- |
| Photograph | `contemporary_photograph` | Reuse `photo-1`: public domain, verified, already frozen in the repository. |
| Historical image | `contemporary_photograph` (period photograph) or `later_depiction` | One public-domain historical image sourced with credible licence evidence and frozen (open question 2). |
| Editorial artwork | `conceptual_artwork` | Original local vector artwork authored in this repository; no paid generation. |
| Conceptual reconstruction | `reconstruction` | Original local vector artwork authored in this repository; caption states that no original was traced. |

The existing record contract (`path`, `originUrl`, `creator`, `licence`, `credit`, `caption`, `alt`, `kind`, `rightsStatus`) is unchanged. Local originals use `originUrl: "local:<repo-relative path>"` and `licence: "Original work created for this catalogue"`. A historical image that cannot be verified is reported absent and fails the catalogue gate; it is never replaced by generated or decorative art presented as documentary.

## Captions

A caption is the description that follows a chart, diagram or illustration. Its printed label (`Figure N.` / `Photograph N.`) is part of the description and is centred with it.

- The only template change is a shared `preset-figure-caption` used by `preset-chart`, `preset-diagram` and `preset-illustration`: `align(tokens.figure.caption_align, ...)` with `set par(justify: false)`. Each rendered line is centred, including wrapped lines.
- `tokens.figure.caption_align = center` lives in `typst/theme.typ`; templates contain no raw alignment or size.
- Credits and source notes remain separate elements with their own presets (open question 1). They are not part of the centred description.
- Existing figure keep-together (`breakable: false`), label detection, cross-references and notes are preserved. A wrapped caption must not make an illustration's page map unresolved.
- Measurable acceptance: every caption line's PDF bounding-box centre is within ±2 pt of the page centre (297.64 pt on A4); a deliberately left-aligned control fixture fails; at least one single-line and one wrapped caption exist for charts, diagrams and illustrations.

## Contracts

### Chart envelope

```yaml
chart:
  kind: waterfall
  categories: [Start, Gain, Loss, End]
  series: [{ id: delta, label: Change }]
  values: [[40], [12], [-7], [45]]
  totals: [false, false, false, true]   # waterfall only
  axis: { unit: index, min: 0 }
  verification: synthetic               # verified | inferred | synthetic
  notes: "Synthetic values authored for the catalogue; not measurements."
```

`verification: verified | inferred` requires `source: {sourceId, page}` and forbids fabricated evidence. `verification: synthetic` forbids `source` and block `sourceAnchors`, requires `notes`, and makes `normalize` append "Synthetic data." to the printed caption and a build warning. Synthetic values never claim a source anchor. The canonical hash covers the whole chart spec, not just ids, so a changed value changes the cached figure hash.

### Diagram envelope

```yaml
diagram:
  preset: decision_tree
  synthetic: true                       # illustrative; no source evidence
  nodes:
    - { id: n-q, label: "Signal seen?" }
    - { id: n-y, label: "Read the setting" }
    - { id: n-n, label: "Record the gap" }
  edges:
    - { from: n-q, to: n-y, kind: arrow, label: "yes" }
    - { from: n-q, to: n-n, kind: arrow, label: "no" }
```

`edge.kind` is `arrow` (default) or `line`. Backward and feedback edges are dashed by the preset, not by the author. `synthetic: true` forbids `sourceAnchors`, requires a block `note`, and makes `normalize` append "Illustrative diagram." to the caption. Non-synthetic diagrams keep the existing `confidence: inferred` → "Reconstruction." rule. Unknown presets fail; there is no fallback.

### Schema additions

Additive only: `chart.verification` gains `synthetic`; `chart.source` becomes conditionally required; new chart payload fields (`errors`, `bins`, `stats`, `samples`, `points`, `totals`, `hole`, `xAxis`); new diagram payload shapes (`events`, `rows`/`columns`/`cells`, `sets`/`overlaps`, `lanes`/`stages`/`nodes`) and `diagram.synthetic`. Existing `grouped_bar`, `process` and `model` manuscripts remain valid; no migration and no `schemaVersion` bump.

## Commands (existing commands, no new subcommand)

```bash
uv run bookify manuscript check --manuscript content/catalogue.yaml --json
uv run bookify design check --manuscript content/catalogue.yaml --json
uv run bookify figures render --manuscript content/catalogue.yaml --out build/figures/catalogue --json

uv run bookify build --manuscript content/catalogue.yaml --out dist/catalogue.pdf \
  --offline --build-dir build/catalogue --json
uv run bookify build --manuscript content/catalogue.yaml --out dist/catalogue-rebuild.pdf \
  --offline --build-dir build/catalogue-rebuild

mkdir -p build/catalogue-pages
pdftoppm -png -r 110 dist/catalogue.pdf build/catalogue-pages/page
magick montage build/catalogue-pages/page-*.png -tile 4x build/catalogue-contact.png

uv run bookify verify --pdf dist/catalogue.pdf --manuscript content/catalogue.yaml \
  --previous-pdf dist/catalogue-rebuild.pdf \
  --build-report build/catalogue/build-report.json \
  --contact-sheet build/catalogue-contact.png \
  --reviewed-by "<name>" --reviewed-at "<ISO time>" \
  --report build/catalogue-verify.json

uv run pytest
```

Existing regressions stay in the gate: the specimen and trial double builds with `verify` (same commands, different manuscripts).

## Project structure

| Path | Change |
| --- | --- |
| `src/bookify/figures/charts.py` | 15 kind renderers behind one registry; shared axes/labels/palette helpers; full-spec hash. |
| `src/bookify/figures/diagrams.py` | Serialise validated geometry; no layout decisions. |
| `src/bookify/figures/presets.py` | `ChartPreset`/`DiagramPreset` registries, per-kind caps, palette, sizes. |
| `src/bookify/figures/checks.py` | New: per-kind shape, range, cap and chart-font validation used by validation and render. |
| `typst/cetz/diagram.typ` | Dispatcher and drawing primitives; no preset-specific layout. |
| `typst/cetz/layouts.typ` | New: 10 named layouts and label fitting. |
| `typst/blocks.typ` | Shared centred figure-caption preset. |
| `typst/theme.typ` | `figure.caption_align` and diagram label/rule tokens. |
| `src/bookify/design/tokens.py` | Mirror the new alignment and diagram token names for the lint/theme test. |
| `src/bookify/manuscript/model.py` | Calls figure checks; synthetic provenance rules. |
| `schemas/manuscript.schema.json` | Additive chart/diagram definitions. |
| `src/bookify/publish/normalize.py` | Synthetic caption wording and warnings. |
| `src/bookify/design/coverage.py` | New diagram/chart strings; chart text limited to the Latin/Vietnamese chain. |
| `src/bookify/verify/checks/captions.py` | New: rendered caption alignment and short/wrapped coverage. |
| `src/bookify/verify/checks/catalogue.py` | New: finite-inventory gate, run only for the catalogue manuscript. |
| `src/bookify/verify/runner.py` | Wire the two checks. |
| `content/catalogue.yaml` | Catalogue manuscript. |
| `fixtures/expected/catalogue.json` | Reviewed inventory: expected block ids, kinds/presets, counts, family labels. |
| `assets/illustrations/<id>/` | Four records and frozen files. |
| `assets/catalogue/artwork/` | Original editorial and reconstruction SVG files. |
| `tests/test_figures.py`, `tests/test_design.py`, `tests/test_publish.py` | Extended regressions. |
| `tests/test_verify_captions.py`, `tests/test_catalogue.py` | New check tests. |
| `skill/bookify/SKILL.md`, `skill/bookify/references/checklist.md` | Local skill: new families, catalogue command, caption rule; no global skill edit. |

## Code style

```python
@dataclass(frozen=True)
class ChartPreset:
    kind: str
    shape: str
    render: Callable[[dict, Theme, Axes], None]

PRESETS: dict[str, ChartPreset] = {...}

def render(block: dict, root: Path, out_dir: Path) -> ChartRender:
    """Return SVG for a validated chart; an unknown kind is an error, never a fallback."""
    spec = checks.validate_chart(block)      # one boundary for shape, caps and ranges
    preset = PRESETS[spec["kind"]]
    ...
    payload = canonical_json(spec)           # values included; stable key order
    digest = sha256(payload.encode()).hexdigest()[:12]
```

```typst
#let preset-figure-caption(caption) = align(tokens.figure.caption_align, {
  set par(justify: false)
  set text(size: tokens.type.caption, fill: tokens.ink.grey_1, style: "italic")
  caption
})
```

The catalogue manuscript contains data only: no per-figure Python, no per-figure Typst snippet, no custom script. A new figure is a preset name plus stored values or geometry.

## Catalogue document

`content/catalogue.yaml`, `id: visual-catalogue`, `schemaVersion: "1.0"`, `revision: 1`, languages `[en, vi, ja]`. Short section titles keep the contents parser one-line:

1. **About this catalogue** — scope, synthetic-data statement, caption rule, illustration classification. One Vietnamese and one Japanese paragraph.
2. **Charts: bars** — `bar`, `grouped_bar`, `stacked_bar`.
3. **Charts: lines** — `line`, `area`.
4. **Charts: points** — `scatter`, `bubble`.
5. **Charts: distributions** — `histogram`, `box`, `violin`, `error_bar`.
6. **Charts: matrices** — `heatmap`, `radar`.
7. **Charts: parts** — pie, donut, `waterfall`.
8. **Diagrams: flow** — `process`, `cycle`, `timeline`.
9. **Diagrams: structure** — `hierarchy`, `decision_tree`, `model`.
10. **Diagrams: relations** — `network`, `matrix`, `venn`, `swimlane`.
11. **Illustrations** — four blocks, one per family; placement defers them to distinct pages.
12. **Coverage** — 29-row table: 15 chart families, 10 diagram presets, 4 illustration families, each with its figure reference. Pie/donut is one row referencing two figures.

Figure numbering is document order: Figures 1–16 are charts, 17–26 diagrams; Photographs 1–4. Captions mix short (one rendered line) and wrapped (two or more) descriptions. At least one caption in each group wraps so multiline alignment and illustration page mapping are exercised. Crossrefs to a chart, a diagram and a photograph are present.

Multilingual labels: chart categories are Latin/Vietnamese only because Matplotlib renders through the Spectral chain; Japanese and Vietnamese appear in diagrams, body text and captions where Typst's explicit fallback chain applies (open question 3). Chart captions are Typst text and may be bilingual.

## Testing strategy

`pytest` under `tests/`:

- **Figures:** every kind renders twice with the same hash; changing one value changes the hash; unknown kind fails; each cap and each range/order rule has a negative case; every SVG has no `<image>`; `process`/`model` output stays stable; each new preset emits a snippet that compiles and extracts its labels; a long diagram label is fitted, an impossibly long one fails; a Japanese chart label fails with `GLYPH_MISSING`.
- **Design:** `figure.caption_align` and diagram tokens exist; lint passes (including `typst/cetz`); every new label field is collected; existing token/preset tests stay green.
- **Captions:** a centred short caption and a centred wrapped caption pass; a left-aligned control fails; a block that cannot be isolated fails loudly; Table captions are ignored.
- **Catalogue:** exact inventory (no missing, no extra kind/preset/family); pie and donut are both present; each family name and figure label is in the PDF text; counts match; the editorial caption names it as original artwork and the reconstruction caption names the reconstruction; every illustration is placed once and no page holds two.
- **Publish:** the catalogue builds offline twice with identical page count, page text, placement map and numbering; `verify` gate passes; notes, credits and synthetic wording are extractable; specimen and trial rebuild with their existing page counts and probes.

## Acceptance

1. `manuscript check` and `design check` pass; `figures render` writes 16 chart files and 10 diagram files, all deterministic and vector.
2. The catalogue builds offline twice; page count, page text, illustration page map, figure/table numbering and contents pages are identical; `verify` returns `gate: pass`.
3. The catalogue check proves exactly the 15 chart families, 10 diagram presets and 4 illustration families, including both pie and donut; no extra or missing family; editorial and reconstruction captions name their class.
4. Every chart, diagram and photograph caption is centred: every rendered line's bbox centre is within ±2 pt; at least one short and one wrapped caption exist per group; a left-aligned control fails.
5. Captions stay with their figures; captions, notes, credits, cross-references and labels are extractable; illustration detection still works for a naturally wrapped caption.
6. At most one illustration per final page; four illustrations appear on four distinct pages; deferrals are reported, never silent.
7. All fonts are embedded; Vietnamese and Japanese labels have no missing glyph; chart text is confined to the Spectral chain.
8. Every page is rendered and inspected; the inspection record and contact sheet are in the report.
9. Existing specimen (6 pages) and trial (3 pages) builds and verification still pass, with unchanged page counts and text.
10. No network or model call occurs in `build` or `verify`; no new dependency or font is added.

## Boundaries

- **Always:** use the preset registry and stored data; validate at the manuscript boundary; centre only figure descriptions; keep credit and source notes separate; label synthetic values and illustrative diagrams; keep one illustration per page; keep build/verify offline; report every deferral and uncertainty.
- **Ask first:** changing the 15/10/4 inventory; adding a chart kind or diagram preset; centring credits, source notes, table or equation captions; changing a cap or the chart-font constraint; sourcing a new external image or changing its licence; bumping the schema version.
- **Never:** write per-figure scripts; invent a source anchor, value or licence; present synthetic, generated or reconstructed art as documentary evidence; use a categorical palette, 3-D effects or decorative fills; clip a label silently; edit the global `pdf-book-design` skill, any external repository or global asset; access personal context stores.

## Open questions

1. **Credit and source-note alignment.** The confirmed instruction covers descriptions. Proposal: descriptions centred; illustration credits and chart/diagram source notes stay left in their existing presets, preserving the distinction. Should they also be centred?
2. **Historical image sourcing.** Proposal: allow one Wikimedia Commons public-domain historical image, fetched once during authoring, frozen under `assets/illustrations/hist-1/` with origin URL, creator, licence URL, `retrievedAt` and `sha256`; no paid generation. Is that acceptable, or should the catalogue use only already-local assets and mark the historical family absent?
3. **CJK inside charts.** Charts render through Matplotlib and Spectral; the vendored CJK face only registers at ExtraLight weight there. Proposal: Vietnamese in charts, Japanese in diagrams/body/captions. Is that sufficient multilingual coverage, or must charts carry Japanese labels too?
4. **Table and equation captions.** Proposal: leave them as they are; the instruction named photographs, charts and diagrams only. Should they follow the centred rule for visual consistency?
