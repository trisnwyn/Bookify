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
