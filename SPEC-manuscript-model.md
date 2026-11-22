# SPEC-manuscript-model

Module id: `manuscript-model` · depends on: nothing · build step 1 · status: approved 2026-11-10.

## Objective

Define the single contract between AI-assisted authoring and deterministic publishing. One manuscript file plus its assets must be enough to rebuild the book, with every claim traceable to a source anchor or explicitly marked as inferred. Publishing must keep working when all caches and model output are deleted.

The specimen manuscript is a small neutral fixture (not an existing chapter) so acceptance tests mechanics: chapter opener, body, Vietnamese/Japanese/special characters, an equation, a grouped-bar chart, a reconstructed process diagram, one licensed photograph, a table and a cross-reference.

## Tech stack

YAML (readable and agent-writable) validated against a closed JSON Schema Draft 2020-12, `schemaVersion: "1.0"`. Validation uses a JSON Schema implementation chosen in the plan; no extra service. YAML is serialization, the schema is normative.

## Commands (proposed, not implemented)

```bash
uv run bookify manuscript check --manuscript content/specimen.yaml --json
uv run bookify manuscript schema --print            # emit the normative schema
```

## Project structure

```
schemas/manuscript.schema.json      # closed objects, additionalProperties: false
schemas/examples/specimen.yaml      # valid fixture used by publishing tests
src/bookify/manuscript/
  schema.py                          # load + validate, stable error report
  model.py                           # typed view for consumers
  migrations.py                      # v1 only; additive rules documented
  xref.py                            # target index and label resolution
content/specimen.yaml                # working manuscript
assets/illustrations/<id>/           # image file + rights sidecar
```

## Contract (v1, condensed)

```yaml
schemaVersion: "1.0"
revision: 1
id: specimen
metadata: { title: "...", languages: [en, vi, ja], institution: "...", course: "..." }
sections:
  - id: sec-opening
    title: "Opening"
    level: 1             # optional 1|2|3; absent means 1 (chapter)
    breakBefore: page    # optional auto|page; absent means page for level 1, auto for level 2/3
    blocks:
      - id: b-1
        type: paragraph
        text: "See {ref:fig-process} for the synthetic example diagram."
        sourceAnchors: [{ sourceId: example-source, page: 3 }]
        confidence: verified            # verified | inferred | unreadable
      - id: fig-process
        type: diagram
        caption: "Synthetic process diagram for the example."
        geometry: { preset: process, nodes: [...], edges: [...] }
        sourceAnchors: [{ sourceId: example-source, page: 3 }]
        confidence: inferred
      - id: b-chart
        type: chart
        chart: { kind: grouped_bar, series: [...], categories: [...], values: [...],
                 source: { sourceId: example-source, page: 7 }, verification: verified }
        caption: "..."
      - id: b-photo
        type: illustration
        illustrationId: photo-1
```

Illustration records (in `assets/illustrations/<id>/record.yaml`) carry `path`, `originUrl`, `creator`, `licence`, `credit`, `caption`, `alt`, `kind` and `rightsStatus` as fixed in `SPEC-INDEX.md`.

Block types v1: `paragraph`, `lead`, `definition`, `example`, `case`, `assessment`, `table`, `equation`, `chart`, `diagram`, `illustration`, `quote`, `list`. Anything else is a schema error, not a silent fallback.

## Validation rules (testable)

1. Closed objects at every level; unknown fields rejected.
2. Unique `id` per section, block, illustration and xref target; ids are kebab-case.
3. Every `{ref:<id>}` resolves to an existing block or section; dangling refs fail with `XREF_MISSING`.
4. `confidence: unreadable` requires the value to be absent or `null` plus a note — a guessed number is a schema error.
5. `chart` data must be complete: one value per series/category pair, or an explicit `null` with a note; no NaN, no interpolation at validation time.
6. `diagram.geometry` must contain every id referenced by an edge; no orphan edges.
7. `illustration` must reference an existing record with all rights fields present; `rightsStatus` is required.
8. `revision` increments on any content change; breaking shape changes require a migration, never a silent rename.
9. Section `level` is an optional integer `1|2|3`. Absent means `1`. The first body section must be level 1. A section may not skip a level: a level 3 section requires a current level 2 parent in the preceding flow, and `1 → 3` is rejected with `SCHEMA_INVALID` at `sections[i].level`. A valid `1 → 2 → 3 → 2 → 1` flow is accepted.
10. Section `breakBefore` is an optional enum `auto|page`. Absent means `page` for level 1 and `auto` for levels 2/3. `auto` flows; `page` starts a new page. `breakBefore: page` on the first body section is ignored and never creates a blank page. A level alone never implies a break.
11. Section titles must be unique. The contents/xrefs checks key entries by printed title and would otherwise collapse two sections named alike; duplicates fail with `SCHEMA_INVALID` at `sections[i].title`.

## Code style

```python
@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    locator: str

def require_target(target: str, index: Mapping[str, Anchor]) -> Anchor:
    """Return the xref target or fail loudly; never fall back to the raw id."""
    anchor = index.get(target)
    if anchor is None:
        raise BookifyError("XREF_MISSING", f"unknown reference: {target}", target)
    return anchor
```

## Testing strategy

`pytest` under `tests/manuscript/`:

- Golden: `schemas/examples/specimen.yaml` validates; a published copy of it also validates after a round-trip.
- Negative fixtures: unknown field, duplicate id, dangling xref, missing licence, guessed unreadable value, incomplete chart matrix, orphan diagram edge — each expected to fail with its named code.
- Migration: v1 fixture stays valid; no migration code beyond rejecting unsupported versions.
- Cache independence: deleting `build/cache/` never changes validation results.

## Boundaries

- Always: keep the schema closed; validate once at the boundary; preserve source anchors on every interpreted block; version the schema.
- Ask first: adding a block type, changing an existing field's meaning, bumping to a new schema version.
- Never: store prose without provenance in a `verified` block; hide an unknown value; store absolute local paths; require a cache or model output to render.

## Success criteria

1. `bookify manuscript check` accepts the fixture and rejects every listed negative fixture with the matching error code.
2. Publishing the fixture uses only `content/specimen.yaml` + `assets/`; deleting all caches changes nothing.
3. Every block in the fixture reaches a source anchor or is marked `inferred`/`unreadable`.
4. Adding a field to the schema requires a spec change first; the validator has no undocumented exceptions.
5. `revision` and `schemaVersion` are present and checked on every load.

## Amendment — Phase 2 section hierarchy (2026-11-13)

User authorization, verbatim: “Proceed with the coordinated line-spacing and page-break layout changes.” This is an additive `schemaVersion: "1.0"` extension; no migration, new block type, dependency or schema-version bump. It does not claim earlier approval of `level` or `breakBefore`.

- `level` (`integer`, enum `[1,2,3]`) and `breakBefore` (`string`, enum `["auto","page"]`) are optional properties of `$defs.section`; the schema stays closed, so malformed values still fail as `SCHEMA_INVALID`.
- Defaults are documented here, not written into the JSON Schema: level 1, and `breakBefore` `page` for level 1 / `auto` for level 2/3. `normalize` materialises the concrete values so the template never infers.
- Missing fields keep legacy chapter semantics: every existing manuscript still validates and its sections still default to level 1 with a page before each non-first section. The corrected line leading is the only intentional legacy layout change.
- The first body section resolves to `breakBefore: auto` regardless of input; the template also keeps an explicit `section-index > 0` guard, so a redundant or explicit break cannot insert a blank page.
- A pure plate section (exactly one `illustration` block, optionally preceded by an `unresolved` note) is normalised with `keepTogether: true`; its heading, note, image, caption and credit are one unbreakable unit. A section that also holds prose, or more than one illustration, is not collapsed.
- `number` and xref labels remain flat `§N`; hierarchy changes heading level and flow, not printed cross-reference text. Contents is depth 3 and may span pages; report and xrefs parse the whole contents range.

## Amendment — Bookify v2 numbering and roles (2026-11-14)

Additive `schemaVersion: "1.0"` extension per the owner-approved
`SPEC-bookify-v2.md` §4. OCR fields (`region`, `machineRead`) belong to the
separate intake workstream and are not part of this design amendment.

- `$defs.section.role` is an optional enum `chapter|appendix`; absent means
  `chapter`. It is a level-1 property: a level-2/3 section may not declare it.
- Validation rules: an appendix may not be the first body section; every
  level-1 section after the first appendix must also be an appendix (a chapter
  after an appendix is `SCHEMA_INVALID` at that section). Mixed back matter is
  refused rather than renumbered.
- Numbering is structural: level-1 chapters `1`, `2`; level-2 `1.1`; level-3
  `1.1.1`. Appendices print `Appendix A`, `Appendix B` at level 1 and `A.1`,
  `A.1.1` below. There is no `numbering` field and no knob.
- Contents prints the same strings and folios as the page. Cross-reference text
  is the printed number with a section mark: `§1.2`, `§A.1`, `§A` for a
  level-1 appendix. `Figure N`, `Table N` and `Photograph N` keep their counters.
- Front matter (cover, contents) is unnumbered and is generated, so no new
  mandatory field was added to suppress it. Every level-1 body section is
  numbered by default; a manuscript without `role` normalises exactly as before
  except that printed numbering now appears (a rendering change, not a schema
  change).

## Amendment — production layout integration (2026-11-16)

Additive to `schemaVersion: "1.0"`; no migration and no version bump. Every
existing manuscript still validates, and absent fields keep their previous
meaning.

- `metadata.cover` (optional object): `composition` (enum `cover-1` … `cover-7`,
  required) and `artwork` (optional illustration record slug). `cover-3` is
  typographic only and refuses `artwork` (`SCHEMA_INVALID` at
  `metadata.cover.artwork`). An absent `metadata.cover` is not a default
  composition: `normalize` records `selection: engine-fallback` with `cover-3`.
- `section.layout` (optional object): `columns` enum `[1, 2]`. A column count is
  a chapter-level property; declaring it below level 1 is `SCHEMA_INVALID` at
  `sections[i].layout`. Absent means the single-column default.
- `section.level` (enum `[1, 2, 3, 4, 5]`): the body path is `1.` (level 2),
  `1.1` (level 3), `1.1.1` (level 4) and `1.1.1.1` (level 5); levels 4-5 keep the
  h3 type role. The additive-parent rule is unchanged. A second level-2 section
  keeps the level marker with its index (`1.2.`), and `number` (the cross-
  reference form) keeps that period so no two sections share a reference.
- A chapter's `layout` is inherited by every descendant for validation: a
  `side-left`/`side-right` composition is refused anywhere inside a two-column
  chapter, not only in the chapter's own blocks.
- `branch` block (`type: branch`, required `text`): one terminal branch of its
  section. `normalize` generates the run-in marker from the section number and
  the block's order (`1.1 a)`, `1.1 b)`); the block carries no authored number.
- `composition.preset` gains `centred` (a 430 pt figure-width visual). A side
  preset accepts the legacy single `companion` or an ordered `companions` array
  (1–3 slugs); the blocks must be the immediately following blocks in order,
  each a prose type, each ≤ 520 collapsed characters and the group ≤ 900. `full`
  and `centred` forbid both companion fields.
- `normalize` emits a `heading` string per section (`Chapter 1: Title`,
  `Appendix A: Title`, `1.1 Title`) so the report, cross-reference and opener
  checks compare against the line the page really shows, and `numbering.levels`
  becomes 4.
