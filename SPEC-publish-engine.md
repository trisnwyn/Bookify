# SPEC-publish-engine

Module id: `publish-engine` · depends on: `manuscript-model`, `design-system`, `figure-engine` · build step 4 · status: approved 2026-11-10.

## Objective

Assemble the final A4 document from a validated manuscript and local assets: pagination, contents, numbering, cross-references, figure/table placement, illustration placement under a hard one-per-page limit, and caption/credit rendering. The build is a pure function of manuscript + assets + pinned toolchain: no network, no model, no authoring cache.

## Tech stack

Typst compiles the document; a small Python driver normalizes the manuscript, renders figures, writes the Typst input, invokes Typst with a local root, local fonts and vendored packages, then collects a build report. Poppler inspects the result during verification, not during build.

## Commands (proposed, not implemented)

```bash
uv run bookify build --manuscript content/specimen.yaml --out dist/specimen.pdf --offline
uv run bookify build --manuscript fixtures/adversarial/illustrations.yaml --out /tmp/adversarial.pdf --offline
```

## Project structure

```
src/bookify/publish/
  normalize.py               # manuscript -> resolved document model (ids, numbers, xrefs)
  illustrations.py           # deterministic placement + limit enforcement
  typst_driver.py            # writes typst data, invokes compiler, captures report
  report.py                  # build-report.json: pages, placements, deferrals, warnings
typst/templates/book.typ     # page assembly, TOC, numbering
typst/templates/blocks.typ   # maps manuscript blocks to design presets
content/specimen.yaml
```

## Pipeline

1. **Validate** the manuscript and every asset reference (fail before compiling).
2. **Resolve** section/block ids, figure and table numbers, and `{ref:...}` labels.
3. **Render figures** through `figure-engine`, hashed and cached under `build/figures/`.
4. **Place illustrations** (rule below) and emit the resolved document model.
5. **Compile** with Typst: `--root . --font-path assets/fonts --package-path vendor/typst`, offline guard active.
6. **Report** pages, illustration placements, deferrals and any warnings to `build/build-report.json`.

## Illustration placement rule (deterministic)

Input: illustrations already selected by `authoring-pipeline`, each anchored to a section, ordered by section position and then by declared priority. No selection happens here; no new search, no quota.

1. Compile a layout pass with no illustrations to obtain each section's starting page.
2. For each illustration in order: place it on its section's current page if that page holds no illustration and the block remains readable; otherwise on the next page that (a) still belongs to the same section and (b) holds no illustration.
3. If no such page exists, defer the illustration to the next illustration-free page at the section's end and record `ILLUSTRATION_DEFERRED` with the illustration id and page.
4. Recompile and check the placement map against the page map; repeat at most 3 times. A fourth disagreement fails the build with `ILLUSTRATION_LIMIT` rather than accepting an unstable layout.

Measurements: every illustration entry in `build-report.json` has a final page; the verifier asserts no page carries two; a dropped illustration is never silent.

## Cross-references and numbering

`{ref:<id>}` resolves to a stable printed label: `§2.1` for sections, `Figure 3` for charts/diagrams, `Table 2` for tables, `p. 14` only when explicitly requested. A dangling target fails with `XREF_MISSING` before compilation. Contents lists sections and figures; page numbers come from the compiled document, never from a hand-written map.

## Captions and credits

Caption text comes from the block/record; the credit line comes from the illustration record and is set in `type.credit`. `kind: later_depiction` and `kind: reconstruction` add their wording to the caption by rule, so a reconstruction cannot be presented as a photograph. `rightsStatus: unconfirmed` is a build error outside an explicitly marked draft build.

## Offline and model-free

The driver refuses to run if `--offline` is absent for publish builds, blocks sockets for the duration, and records the guard state in the report. Typst runs with local packages and fonts only; a missing package is a build failure, not a download.

## Code style

```python
def place_illustrations(doc: ResolvedDocument, pages: PageMap) -> Placement:
    """Assign every illustration to exactly one page, never two per page."""
    placement = Placement()
    for item in doc.illustrations_by_section():
        page = pages.first_free_page_in_section(item.section_id)
        if page is None:
            placement.defer(item, reason="no illustration-free page in section")
            continue
        placement.assign(item, page)
    return placement
```

## Testing strategy

`pytest` under `tests/publish/`:

- Golden: specimen builds; page count, page text and illustration page map match stored expectations.
- Limit: an adversarial manuscript with two illustrations competing for one page yields exactly one per page, one deferral, and a report entry.
- Xref: dangling ref fails with `XREF_MISSING`; figure/table numbering is stable across rebuilds.
- Rights: an unconfirmed-rights illustration fails a normal build; a draft build is explicit and marked.
- Offline: build with `--offline` makes no outbound connection; omitting `--offline` is refused.
- Cache independence: deleting `build/` still rebuilds identical output.

## Boundaries

- Always: validate before compiling; keep placement deterministic; report every deferral; keep captions/credits on the record; use local fonts/packages.
- Ask first: changing the placement rule, allowing more than one illustration per page, adding an output format, relaxing the rights check.
- Never: pick illustrations during pagination; retry indefinitely until a layout "looks right"; download a package mid-build; print a reconstruction as a photograph; drop an illustration without a report entry.

## Success criteria

1. One command produces `dist/specimen.pdf` from the fixture with no network and no model call.
2. No final page carries more than one illustration, including the adversarial fixture.
3. Every cross-reference, figure and table number resolves and is stable across two builds.
4. Every illustration appears with caption, credit and kind-appropriate wording.
5. A second build from unchanged inputs has the same page count, page text and placement map.

## Amendment — Phase 2 layout correction (2026-11-13)

User authorization, verbatim: “Proceed with the coordinated line-spacing and page-break layout changes.” Additive to the approved publish contract; no new dependency or output format.

### Section flow

- The template renders `heading(level: section.level, ...)` and breaks only when the normalised `breakBefore == "page"` and `section-index > 0`. The first body section never inserts a redundant break; no blank verso or parity page is added.
- Kickers are a sticky block so a kicker is never left alone at a page foot. A pure plate section (normalised `keepTogether: true`) wraps its heading, note, image, caption and credit in a `block(breakable: false)`; ordinary chapters are never made unbreakable.
- Contents is `depth: 3` and may paginate. The report and `xrefs` check parse every contents page from the first contents page until the first non-contents page, and exclude all of them from section-page lookup. Section titles are unique; `model.load` rejects duplicates.

### Long tables and oversize units

- `preset-table` uses `table.header(repeat: true, ...)` for the header and `table.footer(repeat: false, ...)` for the caption. A split table therefore repeats its header and keeps its caption exactly once, at the end of the table beside the final rows.
- `report.require_unit_fit` measures the rendered caption and credit boxes of every chart, diagram and illustration. A caption line, or a credit line, that exceeds `PAGE_HEIGHT − PAGE_MARGIN + 2 pt` fails with `BUILD_FAILED` and the block id; a caption that cannot be followed completely on one page is treated as detached and also fails. The check deliberately ignores unrelated body prose on the same page, which may legitimately reach the bottom margin. It never clips, shrinks below the authored size, or drops a caption/credit. The remaining approximation is named in the fixed report: an image that bleeds into the margin while its caption still sits inside would not be caught by text boxes alone.
- Side compositions keep their independent column fit check (`require_composition_fit`). The one-illustration-per-page deferral loop is unchanged.

### Cross-references and numbering

- `{ref:<section>}` remains flat `§N`; declaring a level does not change printed cross-reference text. `Figure N`, `Table N` and `Photograph N` numbering is unchanged.
- `build-report.json` records `level` and `breakBefore` per section and the `contentsPages` range; page counts and hashes change by design because leading changed, and are rebaselined only after the rendered measurements pass.

## Amendment — Bookify v2 composition and report (2026-11-14)

Implements the owner-approved `SPEC-bookify-v2.md` §6. Additive; the offline,
model-free, OCR-free build invariant and the one-illustration-per-page rule are
unchanged.

### Cover, numbering and contents

- `normalize` resolves `printed` numbers and `role` per section and emits
  `numbering` (`chapters`, `appendices`, `levels`) plus `cover` (`index`,
  `indexMode`). Level-1 chapters print `1`, `2`; appendices print `Appendix A`
  while their children print `A.1`. The template sets a custom
  `heading(numbering:)` that mirrors `normalize.appendix_letter`; the outline
  prints the same strings. Cross-references resolve to `§1.2` / `§A.1` from the
  same map.
- The cover renders before the contents and is not in the outline. The cover
  page uses `page(numbering: none)`; numbering resumes on the contents page. The
  cover receives `metadata`, `coverIndex` and `coverIndexMode`; it never invents
  metadata. Back matter is data (`role: appendix`), never inferred.
- `report.require_cover_fit` fails the build with a metadata locator when the
  title exceeds three lines or the footer ink loses its ≥ 24 pt slack. The cover
  is never clipped, shrunk or partially printed.

### Openers, plates and captions

- Chapter openers are a template show rule, not per-book markup: printed number,
  0.6 pt full-measure rule, title, then the authored standfirst/lead.
- `full` illustrations, charts and diagrams use `measure.plate` (475.28 pt);
  charts are authored at that measure so their type is not scaled. Side
  compositions keep 46 % + 16 pt and stay illustration-only.
- `preset-chart`, `preset-diagram` and the full illustration preset emit one
  centred caption carrying description and `note`; a separate figure note is no
  longer emitted. Credits stay separate and left. Table and equation captions are
  unchanged. Machine-read table notes (OCR, separate workstream) keep their own
  below-table treatment.
- `report.plate_entries` records every plate with `widthPt` and `basis`:
  `measured` from the placed image box for raster illustrations, `declared` for
  vector charts/diagrams and vector full illustrations. A chapter with a visual
  and no plate is a `plateGaps` entry.

### Build report additions

`build-report.json` gains `numbering`, `cover` (`indexMode`, `coverIndex`,
`entries`, `folio`), `plates`, `plateGaps`, `definitions`
(`count`, `glossaryTables`), `captions` (`unified`, `separateNotes`), and
`readability` (metrics, bands, exemptions, warnings). These are evidence for
verify and review, not a second source of truth. No page or figure target is
recorded.

### Residual limits

A vector chart or diagram carries no raster image object, so verify reads its
declared measure from the same template token and the design test pins the
template; raster illustrations are measured from the placed box. The report is
therefore honest about the basis of each plate width.

## Amendment — production layout integration (2026-11-16)

- The template dispatches the cover to `typst/cover.typ`
  (`render-cover(metadata, cover)`); the ledger/index cover is removed. The
  document's `cover` object records `composition`, `selection`
  (`author`/`engine-fallback`), `artwork` (`present`/`absent`/`not-applicable`),
  `artworkPath`/`artworkCredit` when present, and `indexPrinted: false`. It no
  longer carries `index`/`indexMode`.
- A level-1 chapter heading is one h1 line, `Chapter 1: Title` (`Appendix A:
  Title`); the counter still numbers the contents with the bare `1`. The 40 pt
  numeral/rule stack is removed.
- `require_cover_fit` no longer enforces a footer-slack rule or a printed index.
  It enforces the title's three-line budget and that every cover line stays
  inside the 60 pt text block; the raster cover check keeps the ink-accurate
  gate, plus no folio, no chromatic pixels and no raster image unless an artwork
  record was selected.
- `report.plate_entries` returns `(plates, gaps, visuals)`: only full-measure
  visuals are plates; a centred visual (430 pt) and a side visual (46 % column)
  are recorded in `visuals` with their measured or declared width. `plates`
  still drive the per-chapter plate gap and the readability exemption.
- `report.composition_entries` covers every visual type (chart, diagram,
  illustration) and records the preset plus `companionIds`.
- `report.analyse` and `readability.measure` find a section's page through
  `report.line_is_section`, which accepts the `Chapter n:`/`1.`/`1.1` prefix so
  a wrapped heading is still located.
- A chapter with `layout.columns == 2` sets its descendant sections inside the
  same column flow; a chart, diagram or illustration inside it takes the 229.64
  pt column measure (`typst/compositions.typ`), and a side composition is
  refused by the model in such a chapter **and in any descendant** (the layout is
  inherited). `captions`, `figure-geometry` and `require_unit_fit` read the
  effective, inherited column count. `rhythm` takes its two-column page set from
  the authored layout, never from where lines happen to start, and stops before a
  following chapter that begins on a later page; when a following chapter starts
  on the same page, only that shared page is declared two-column and the later
  pages stay single-column.
- `section_numbers` emits a unique `number` per section: the printed form for
  body levels (including the level-2 period), the chapter number for a chapter
  and the bare letter for an appendix. `xrefs` resolves a reference followed by
  sentence punctuation against the allowed forms.
- `_workspace_mounts` binds each rights-record image file the manuscript uses at
  its own relative path, with a book-root containment check; the
  `assets/illustrations` folder is still mounted whole.

## Amendment — placement convergence (2026-11-21)

Additive to "Illustration placement rule" step 4, and a correction of it. The
fixed "repeat at most 3 times, a fourth disagreement fails" rule is replaced by a
convergence test, following WeasyPrint's repagination loop
(`layout_document()`, up to eight passes, stop when nothing changed):

1. A pass is repeated only while the placement map still reports a conflict.
   Agreement, not an attempt count, is the stop condition.
2. Two passes with the same placement map are the same layout. A repeat is a
   document that oscillates and fails at once with `ILLUSTRATION_LIMIT` and the
   repeating page map, instead of spending the remaining passes.
3. The safety ceiling is eight passes; reaching it also fails with
   `ILLUSTRATION_LIMIT`, now naming the pass count.
4. `build-report.json` gains `placementPasses`, the number of defer-and-recompile
   passes actually used, so a converging build is visible as evidence.

The one-illustration-per-page rule, determinism requirement and deferral
reporting are unchanged. No page or figure target is introduced.
