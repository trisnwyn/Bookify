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
