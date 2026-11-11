# SPEC-visual-layout — approved v1 visual composition extension

Status: **approved 2026-11-11** (user approval recorded in
`.opencode/visual-layout-intake.md`). This extends the approved
`manuscript-model`, `design-system`, `figure-engine`, `publish-engine`,
`verify-harness` and `authoring-pipeline` modules. It adds **no module id, service,
CLI command, error code, dependency, font, illustration asset or capability-map
entry**. The
boundaries in `SPEC-INDEX.md` remain in force. `SPEC-visual-catalogue.md` remains
the governing catalogue spec except for the one caption clause explicitly amended
in Area 3. Requirements below are unchanged from the proposed text. Approval covers
this specification only; it does not approve the implementation plan or any future
PDF. The implementation plan was approved 2026-11-11; Tasks 44–52 are complete
(technical). Tasks 53–56 (independent review/debug/test) are not started. Final human
PDF sign-off remains pending. No product code, schema, asset, plan or task was
changed at the specification stage.

## Objective

Let an illustration be composed at one side of the measure with prose beside it, or
at full measure as today, while keeping the established Spectral typography,
monochrome palette, chart/diagram centring, rights rules and one-illustration-per-page
limit. Composition is authored or preset-controlled data. It is never chosen by a
model, inferred from text, alternated automatically, or nudged per figure.

Also remove the seven known chart-internal visible-ink offsets (2.24–7.22 pt) at the
shared chart-renderer level, without changing chart data, labels, tolerance or
per-catalogue offsets.

The user already chose **illustrations only**: charts and diagrams remain
main-measure-centred and are not eligible for side composition. This spec does not
reopen that choice.

## Assumptions grounded in the current repository

1. The manuscript model is a closed JSON Schema (`schemaVersion: "1.0"`) plus
   semantic checks in `src/bookify/manuscript/model.py`; illustration blocks already
   accept an optional `caption` override.
2. `normalize.py` assigns section, figure, table and photograph labels in document
   order; `report.py` maps photograph labels to pages; `illustrations.py` defers the
   later illustration when two land on one page.
3. `typst/blocks.typ` has one `preset-illustration(figure, caption, credit)`; the
   template inserts it at 88 % of the measure, page-centred, with the credit left.
   Charts use 72 %, diagrams 430 pt.
4. `verify/checks/captions.py` currently requires **every** figure caption line to be
   within ±2 pt of the page centre. That criterion is true for full-measure figures
   and is amended here only for side illustrations.
5. `build/catalogue-figure-geometry.json` records the seven residuals: Figure 2
   +2.24, Figure 6 +7.22, Figure 7 +7.22, Figure 10 +2.72, Figure 13 +2.96,
   Figure 14 −3.76, Figure 15 −4.48 pt. Containers are centred; the ink is not.
6. The catalogue has 16 charts / 15 families, 10 diagrams, four illustration records
   (`photo-1`, `hist-1`, `art-1`, `rec-1`) and 29 coverage rows. The specimen is
   6 pages, the trial 3 pages; both gates pass.
7. Typst 0.15.1 supports `grid`, `column-gutter` and unbreakable blocks.
8. The current catalogue is 19 pages and 517 tests pass. Neither number is a target
   for this change; only unchanged *facts* that this spec names are.

## Six areas

### Area 1 — Optional additive composition contract

Add one optional object to an existing `illustration` block. Nothing else changes.

```yaml
- id: b-photo
  type: illustration
  illustrationId: photo-1
  composition:
    preset: side-left          # full | side-left | side-right
    companion: b-photo-text    # required for side-*; forbidden for full
- id: b-photo-text
  type: paragraph
  text: "Short prose immediately after the illustration."
```

Schema shape: `composition` is an object with `additionalProperties: false`,
`required: [preset]`; `preset` is the closed enum above; `companion` is a slug.
Conditional rules: `side-left` / `side-right` require `companion`; `full` forbids it.
`composition` is rejected on any block that is not an `illustration`. Absence means
`full`, so every existing manuscript validates unchanged and `schemaVersion` stays
`"1.0"`.

Semantic rules, enforced at the manuscript boundary with `SCHEMA_INVALID`:

1. The companion exists, is in the same section, and is the **immediately following
   block**. No search for a nearby paragraph; no implicit pairing.
2. The companion is one of `paragraph`, `lead`, `definition`, `example`, `case`,
   `assessment`, `quote`, `list`. It is not a chart, diagram, table, equation,
   illustration or `unresolved` block.
3. A prose block is the companion of at most one illustration.
4. The companion's printable text, including any `title`, `term`, `definition`,
   `attribution`, list items and `note`, is at most **520 characters** after
   whitespace collapse. This keeps the pair inside the declared column and below
   the shortest landscape side unit.
5. The companion text does not begin with `Figure N.`, `Table N.` or `Photograph N.`
   (with a literal full stop), so it cannot be mistaken for a figure caption by the
   placement scan.
6. `full` keeps the current illustration output exactly: 88 % image, page-centred
   caption, credit left, no companion. `side-*` is the only new rendering path.

The 520-character cap is a validation constraint, not a runtime shrink. A companion
that exceeds it never reaches pagination.

### Area 2 — Adjacent-text semantics, order and overflow

The pair is **one unbreakable composition**. It renders once, at the illustration
block's position; the companion is consumed there and is not rendered again in normal
flow. Figure/photograph numbering, cross-reference labels, source anchors and section
titles are unchanged.

- `side-left`: image column at the left of the measure, prose column at the right.
- `side-right`: prose column at the left, image column at the right.
- The preset name always describes the **image** side, not the text side.
- LTR reading order follows column order: `side-left` reads the image unit
  (image, caption, credit) then the companion; `side-right` reads the companion then
  the image unit. Source order is always illustration → companion; it controls
  numbering and the render anchor, not the visual side.
- The image unit keeps image → caption → credit order. The caption label is part of
  the caption. The credit is never part of the caption.
- The companion renders through its normal prose preset (including a role label and
  note if it has one) inside the text column.

Overflow and deferral, deterministically:

1. The composition is `breakable: false`; image, caption, credit and companion never
   split across pages.
2. If it does not fit the remaining space, Typst pushes the whole composition to the
   next page. The placement report records the final page from the caption label.
3. If two illustrations would share a final page, the later composition is deferred
   as a unit: a page break before its illustration block, one report entry; never
   the companion alone.
4. If a composition cannot fit an otherwise empty text block, the build fails with
   `BUILD_FAILED` and a locator. It is never clipped, shrunk or silently dropped.
5. No new error code. Existing `SCHEMA_INVALID`, `BUILD_FAILED` and
   `ILLUSTRATION_LIMIT` semantics apply.

The build report gains a `compositions` list (`blockId`, `preset`, `companionId`,
`page`, `deferred`) and keeps `deferredIllustrations`. Report entries are evidence,
not a second placement engine.

### Area 3 — Caption, credit and column geometry

One deterministic preset set, held in `typst/theme.typ` and mirrored in
`src/bookify/design/tokens.py`. Proposed values (A4, 60 pt margins, body measure
475.28 pt):

| Token | Proposed value | Consequence |
| --- | --- | --- |
| `measure.side_fraction` | `0.46` | image column 218.63 pt |
| `space.side_gutter` | `16pt` | prose column 240.65 pt |
| side image width | 100 % of its column | fills the image column |
| side caption alignment | `center` within the image column | every wrapped line centred by column |
| side credit alignment | `left` within the image column | credit starts at the column edge |
| full illustration | existing 88 %, page-centred | unchanged |
| chart / diagram | existing 72 % / 430 pt, main-measure-centred | unchanged |

Derived centres on A4: left image column `169.31 pt`; right image column
`425.97 pt`; page/main-measure centre `297.64 pt`. These are computed from tokens,
not duplicated as magic numbers in checks. The grid is
`columns: (body * side_fraction, 1fr), column-gutter: tokens.space.side_gutter`; the
image cell contains the image, then the caption, then the credit line, all at 100 %
of the cell.

**Scoped amendment.** `SPEC-visual-catalogue.md`'s page-centred caption criterion is
replaced **only for side illustrations** by: every rendered caption line's bounding
box centre is within ±2 pt of the declared image-column centre. Table and equation
captions stay left. Chart, diagram and full-measure illustration captions stay
page-centred. The ±2 pt tolerance is unchanged. Credits are never centred: for full
illustrations the credit starts at the page margin; for side illustrations it starts
at the image-column edge (both ±2 pt). This is an explicit amendment, not a silent
relaxation.

The catalogue paragraph that currently says every figure description is centred page-
wide (`b-about-captions`) must be rewritten to state the full/side distinction when
the catalogue content changes; it must not remain a false claim.

### Area 4 — Chart visible-ink centring at the shared renderer

Current cause, measured: the image box is page-centred, but Matplotlib's canvas reserves
asymmetric internal space for y-axis labels/ticks (worst in scatter/bubble) and pie/donut
labels are longer on one side. The fix is in `figures/charts.py`, once, for all kinds:

1. Draw the chart exactly as today, from stored data, with the same labels, colours,
   fonts, `tight_layout`, hash salt and vector SVG output.
2. Before saving, measure the rendered artist bounding box.
3. **Grow the canvas on the shorter horizontal side** so the left and right margins are
   equal. Never crop the canvas, never move or rescale individual marks, never apply a
   per-kind or per-catalogue offset.
4. Save the SVG from that symmetric canvas. The visible ink is then centred in the
   image canvas by construction.

No chart data, caption, axis bound, label text, preset registry, font, tolerance or
`<image>` rule changes. Chart text remains paths and is still not extractable; that
existing limitation is unchanged and not claimed as fixed.

The canvas may grow by the measured asymmetry (roughly 2–7 pt at output scale), so
the chart content inside the fixed 72 % insertion width may shrink slightly (target
≤5 %). Direct labels must remain readable and unclipped; page inspection and the
existing chart tests are the guard.

Verification distinguishes four centres and never passes on box evidence alone:

| Centre | What it is | Use |
| --- | --- | --- |
| canvas | the declared image box from the preset (72 %, 88 %, 430 pt or side column) | must be centred ±1 pt; not sufficient alone |
| plot/frame | the axes frame / diagram frame bbox | reported for charts; diagnostic only |
| visible ink | non-white pixels in the rendered figure band (or SVG content bbox for vector artwork) | **pass criterion ±2 pt** for charts and illustrations |
| caption | each caption line's text bbox | **pass criterion ±2 pt** against the declared centre |

The seven residuals and their required result after the fix:

| Figure | Kind | Before (delta) | Required |
| --- | --- | ---: | --- |
| Figure 2 | grouped_bar | +2.24 pt | ≤2.0 pt |
| Figure 6 | scatter | +7.22 pt | ≤2.0 pt |
| Figure 7 | bubble | +7.22 pt | ≤2.0 pt |
| Figure 10 | violin | +2.72 pt | ≤2.0 pt |
| Figure 13 | radar | +2.96 pt | ≤2.0 pt |
| Figure 14 | pie | −3.76 pt | ≤2.0 pt |
| Figure 15 | donut | −4.48 pt | ≤2.0 pt |

The other charts, all diagrams and all illustrations must stay within ±2 pt of their
declared centre; the current diagram maximum is 1.42 pt and the illustration maximum
is 1.06 pt, and neither may regress. For every illustration, raster or vector, the
visible/content bbox is measured and required; the canvas placement is a separate ±1
pt check. Internal whitespace inside an authored SVG is reported, not assumed.

### Area 5 — Catalogue evidence with the existing four records

Use only the existing records and files; no image search, download, new asset or new
rights record. Proposed mapping, with all four illustrations on four distinct final
pages and at most one illustration per page:

| Block | Record | Proposed composition | Evidence provided |
| --- | --- | --- | --- |
| `b-illustration-photo` | `photo-1` | `side-left` + companion | actual left example |
| `b-illustration-historical` | `hist-1` | `side-right` + companion + bilingual caption | actual right example, narrow wrapped multilingual caption |
| `b-illustration-editorial` | `art-1` | `full` | actual full-measure example |
| `b-illustration-reconstruction` | `rec-1` | `side-left` + companion | second side example, grouping |

At least one `side-left`, one `side-right` and one `full` are mandatory. The fourth may
use any preset. Companion prose is new data-only manuscript text, at most 520
characters, honest about the catalogue/record it accompanies; it introduces no new
historical claim, name, date or value. The bilingual caption is a translation or
paraphrase of facts already in the record's caption, not a new claim. Exact wording is
approved at implementation.

The reviewed inventory fixture gains composition expectations (block id → preset,
companion id) and keeps every existing count: 15 chart families / 16 chart figures,
10 diagram presets / 10 diagrams, 4 illustration families / 4 illustrations, 29
coverage rows, Figures 1–26 and Photographs 1–4 in the same order. Chart data,
diagram geometry, records, rights and credits are unchanged.

The catalogue page count is **not** held at 19. It is whatever the new layout
requires, provided two offline builds agree and every page is non-blank, grouped and
inspected. Large trailing whitespace caused by unbreakable compositions is recorded,
not hidden.

### Area 6 — Verification, repeatability and local skill

`captions.check` is extended to be column-aware:

- full-measure captions keep the page-centre rule and the existing consecutive-line
  isolation;
- side captions are isolated by label and expected token sequence within the declared
  image column, allowing interleaved lines from the adjacent prose column; every line
  is measured against the column centre;
- an ambiguous or unisolatable caption still fails loudly; no caption is skipped.

A new catalogue-scoped `figure-geometry` check measures the rendered PDF (Poppler +
raster, as the existing independent script does) and records canvas, frame, ink and
caption centres for every catalogue figure. It crops to the declared image column for
side compositions and excludes note/credit rows and the prose column before taking
ink. It fails if a band contains no ink or cannot be isolated, and it gates all 30
catalogue figures. It runs with the existing `verify` command; there is no new
subcommand. General manuscripts keep the caption/column checks and the rendered-page
inspection; the chart renderer itself is covered by a kind-independent unit test.

Determinism: same manuscript + assets + tokens + pins produce the same composition
map, page count, page-by-page text, caption lines, figure/photograph labels, placement
pages and geometry measurements across two offline builds. Byte-identical PDFs are not
required. `build` and `verify` still make zero network and zero model calls.

The local skill (`skill/bookify/SKILL.md` and `references/checklist.md`) teaches the
presets and the exact repeatable commands, never a runtime/model layout choice:

```bash
uv run bookify manuscript check --manuscript content/catalogue.yaml --json
uv run bookify design check --manuscript content/catalogue.yaml --json
uv run bookify figures render --manuscript content/catalogue.yaml --out build/figures/catalogue --json
uv run bookify build --manuscript content/catalogue.yaml --out dist/catalogue.pdf \
  --offline --build-dir build/catalogue --json
uv run bookify build --manuscript content/catalogue.yaml --out dist/catalogue-rebuild.pdf \
  --offline --build-dir build/catalogue-rebuild
uv run bookify verify --pdf dist/catalogue.pdf --manuscript content/catalogue.yaml \
  --previous-pdf dist/catalogue-rebuild.pdf --build-report build/catalogue/build-report.json \
  --contact-sheet build/catalogue-contact.png --reviewed-by "<name>" --reviewed-at "<ISO time>" \
  --report build/catalogue-verify.json
uv run python -m pytest -q
```

`uv run pytest` still fails to spawn in this environment; the module form is
authoritative. The global `pdf-book-design` skill is not edited.

## Contracts

### Manuscript addition (closed, optional)

```json
"composition": {
  "type": "object",
  "additionalProperties": false,
  "required": ["preset"],
  "properties": {
    "preset": {"enum": ["full", "side-left", "side-right"]},
    "companion": {"$ref": "#/$defs/slug"}
  }
}
```

Conditional `if/then`: side presets require `companion`; `full` sets
`companion: false`. The property is added to the `illustration` branch only; the
closed top-level block object gains the matching optional property. No migration and
no `schemaVersion` bump. `revision` increments when catalogue content changes.

### Normalised document entry

```json
{
  "type": "illustration",
  "id": "b-photo",
  "path": "/assets/illustrations/photo-1/original.jpg",
  "caption": "Photograph 1. ...",
  "credit": "Photo: ...",
  "composition": "side-left",
  "companion": {"id": "b-photo-text", "type": "paragraph", "text": "..."}
}
```

The companion entry is emitted once, inside the illustration entry, and omitted from
the section's normal block stream. Labels for the companion and the illustration are
built before consumption, so `{ref:...}` still resolves to `§n`.

## Project structure (existing modules only)

| Path | Change |
| --- | --- |
| `schemas/manuscript.schema.json` | Optional `composition` on illustration; conditional companion rules. |
| `src/bookify/manuscript/model.py` | Adjacency, prose type, single-use, 520-character and label-prefix checks. |
| `src/bookify/publish/normalize.py` | Consume companion once; emit composition and companion in the illustration entry. |
| `src/bookify/publish/illustrations.py` | Defer a whole composition; no split. |
| `src/bookify/publish/report.py` | `compositions` evidence; placement unchanged. |
| `typst/theme.typ` | `measure.side_fraction`, `space.side_gutter`; no new type sizes. |
| `typst/blocks.typ` | One `preset-illustration` with an optional composition branch; full path unchanged. |
| `typst/templates/book.typ` | Render the composition at the illustration anchor and skip the consumed companion. |
| `src/bookify/design/tokens.py` | Mirror the two new token names. |
| `src/bookify/figures/charts.py` | Shared symmetric horizontal margin pass. |
| `src/bookify/verify/checks/captions.py` | Column-aware side captions; full rule unchanged. |
| `src/bookify/verify/checks/geometry.py` | New file in the existing `verify-harness` module: canvas/frame/ink/caption evidence. |
| `src/bookify/verify/runner.py` | Wire the catalogue geometry check. |
| `content/catalogue.yaml` | Three companions, four composition fields, one bilingual side caption, corrected `b-about-captions`. |
| `fixtures/expected/catalogue.json` | Composition expectations; counts unchanged. |
| `fixtures/adversarial/compositions.yaml` | New bounded fixture for two side compositions, long companions and overflow. |
| `skill/bookify/SKILL.md`, `skill/bookify/references/checklist.md` | Presets, companion rule, commands. |
| `tests/…` | Additive schema, normalization, Typst, caption, geometry, adversarial and regression tests. |

No new top-level module, service, command, dependency, font, asset or capability.

## Code style

```python
@dataclass(frozen=True)
class Composition:
    preset: str                 # full | side-left | side-right
    companion: str | None = None
```

```typst
#let preset-illustration(figure, caption: none, credit: none,
                         composition: "full", companion: none) = {
  if composition == "full" {
    // existing full-measure path, behaviour unchanged
  } else {
    // grid: image column | prose column, or mirrored; breakable: false
  }
}
```

Templates contain no raw point sizes, colours, font names or alignment; the side
widths, gutter and caption alignment come from tokens. The manuscript contains data
only: no per-figure Python, no per-figure Typst and no per-catalogue offsets.

## Testing strategy

- **Schema/model:** absent composition → `full`; old specimens validate unchanged;
  side without companion, full with companion, non-adjacent companion, non-prose
  companion, duplicate companion, 521-character companion and label-prefixed
  companion each fail with `SCHEMA_INVALID`; composition on a chart/diagram fails.
- **Publish:** side-left/right and full normalise once; companion is not rendered
  twice; labels and numbering unchanged; companion text appears exactly once; a
  two-side-composition fixture yields one deferral and no page with two; a composition
  that cannot fit fails loudly; no split image/caption/credit/companion.
- **Captions:** full captions still page-centred; side captions column-centred
  including wrapped lines; interleaved prose does not break isolation; a side caption
  deliberately aligned to the page centre fails; credits left; a 3-line Vietnamese +
  Japanese caption in the 218.63 pt column passes all geometry and extraction checks.
- **Charts:** all 15 kinds render deterministically; the symmetric-margin unit test
  proves equal left/right artist margins; removing the pass fails the test; chart data
  and label text are unchanged; SVG has no `<image>`; the seven catalogue figures and
  all 16 charts are within ±2 pt of their canvas centre on the rendered PDF.
- **Catalogue:** exact 15/16/10/10/4/4/29 inventory; one `side-left`, one `side-right`
  and one `full`; four records unchanged; four illustrations on four distinct pages;
  coverage table unchanged; composition map matches the reviewed fixture.
- **Regression:** specimen 6 pages and trial 3 pages; normalised text hashes
  (`d4b804c1…`, `2762d85f…`) and all probes unchanged; existing 517 tests and the
  caption tolerance `2.0` unchanged; double offline builds; no network/model; every
  page rendered and inspected; new mutants (remove chart symmetry, allow non-adjacent
  companion, page-centre side caption, split composition, two per page) are killed.

## Acceptance (measurable)

1. `manuscript check` and `design check` pass; old specimen/trial manuscripts validate
   with no `composition` field and render the full path unchanged.
2. Side presets require an immediately following prose companion within 520
   characters; full forbids one; every negative fixture fails with the named code.
3. Side captions: every rendered line's bbox centre is within ±2 pt of the declared
   image-column centre (169.31 pt left, 425.97 pt right); the credit's left edge is
   within ±2 pt of the column edge; no caption line overlaps or crosses the column.
   Full captions remain within ±2 pt of the page centre.
4. Catalogue has at least one actual `side-left`, one `side-right` and one `full`
   composition using exactly `photo-1`, `hist-1`, `art-1`, `rec-1`; four illustrations
   on four distinct pages; none shares a page.
5. A narrow multilingual caption wraps to at least three lines in the side column;
   every line is centred within ±2 pt; all text is extractable; nothing is clipped or
   overlapped.
6. Each of the seven named chart figures has a visible-ink centre within ±2 pt of its
   canvas centre after the shared fix; all 30 catalogue figures (16 charts, 10
   diagrams, 4 illustrations) are within ±2 pt; the geometry report records canvas,
   frame, ink and caption separately, and no figure passes on canvas evidence alone.
7. Two offline builds from identical inputs agree on page count, page text, caption
   lines, composition map, photograph pages, numbering, figure hashes and geometry;
   zero network and zero model attempts.
8. The catalogue still proves 15 chart families / 16 chart figures, 10 diagram
   presets / 10 diagrams, 4 illustration families / 4 illustrations and 29 coverage
   rows; chart data, diagram geometry and rights records are unchanged.
9. Specimen is 6 pages and trial 3 pages; normalised text and probes are unchanged;
   the full suite passes; no tolerance was relaxed and no test was removed.
10. Every final page is rendered and inspected; the contact sheet and inspection
    record are in the verify report; no blank page, no split figure, no orphaned
    caption, no missing glyph and no unverified rights record.

### Criteria by dimension

| Dimension | Measurable criterion |
| --- | --- |
| Text | Companion appears exactly once; caption/credit/companion text extractable in full; no prose lost or duplicated; side column text stays inside its column. |
| Glyphs | Every character in the new prose/caption is covered by the declared chain; every visible face is embedded; no `.notdef`; charts stay Latin/Vietnamese. |
| Rights | Every illustration still has verified rights, credit, alt and kind wording; no new record or licence claim; unconfirmed rights still fail a normal build. |
| Grouping | Image, caption, credit and companion share one page; no split; caption never orphaned; two illustrations never share a page. |
| Caption geometry | Full captions page-centred ±2 pt; side captions column-centred ±2 pt on every line; credits left at the declared edge ±2 pt; table/equation captions unchanged. |
| Readability | No overlap or clipping; direct chart labels remain readable; side prose column 240.65 pt; no new type below 7.6 pt; no composition taller than the text block. |
| Regression | Specimen 6 pages, trial 3; normalised text hashes and probes unchanged; full suite passes; tolerance 2.0 unchanged; 9 existing mutants plus new composition/chart mutants killed. |

## Boundaries

- **Always:** keep composition optional and data-only; validate at the manuscript
  boundary; consume the companion once; centre side captions on the actual image
  column; keep credits and notes separate and left; keep charts/diagrams main-measure
  centred; keep one illustration per final page; report every deferral; keep build and
  verify offline; derive values from tokens.
- **Ask first:** changing the 46 % / 16 pt preset, the 520-character cap or the
  caption tolerance; changing which catalogue record uses which preset, or the
  bilingual caption wording; adding a preset; making figure geometry a gate for every
  manuscript; changing the chart symmetry method.
- **Never:** auto-pair text or auto-alternate sides; choose layout from a model or at
  runtime; add a new image asset, illustration record or image search; per-figure
  nudges, data changes or tolerance relaxation; split a composition; clip or shrink
  silently; add a module, command, dependency or font; edit the global
  `pdf-book-design` skill; claim human approval.

## Open questions (bounded; not scope changes)

Approval note: the user approved this specification as proposed, including its
tradeoffs. The plan treats the proposed defaults below as the working defaults; any
change to them is a plan-level question, not a reopening of the scope.

1. Confirm `measure.side_fraction: 0.46` and `space.side_gutter: 16pt` as the fixed
   side preset (or choose another pair before approval).
2. Confirm the proposed catalogue mapping, the bilingual caption record and the exact
   companion prose (wording approved at implementation).
3. Confirm side credits sit left **inside the image column** rather than at the outer
   page margin.
4. Confirm the automated geometry gate is catalogue-scoped (all 30 figures), while
   general manuscripts keep the caption/column checks and page inspection.
5. Confirm the shared chart fix may grow the canvas and shrink chart content by up to
   ~5 % rather than crop it.
6. Tagged-PDF reading order is out of scope in v1; the contract defines visual column
   order and source order only. Is that acceptable?
