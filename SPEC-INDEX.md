# SPEC-INDEX — Bookify v1

Approved capability map: [`capability-map.md`](capability-map.md) (approved 2026-11-10).
Stage: **specs approved 2026-11-10**; planning is in `tasks/plan.md` and `tasks/todo.md`. Each spec below is a v1 contract for one approved module id. Requirements were not changed at approval; the accepted defaults are recorded in `.opencode/planning.md`.

Publication note (2026-11-11): the private development trial is not published. The public test suite uses the source-independent `fixtures/synthetic-trial.yaml`, documented in `docs/synthetic-trial.md`. References here to `tasks/` and `.opencode/` are historical planning notes that are not part of the public snapshot.

## Module specs

| Module id | Spec | Built at step |
| --- | --- | --- |
| `build-toolchain` | [SPEC-build-toolchain.md](SPEC-build-toolchain.md) | 0 |
| `manuscript-model` | [SPEC-manuscript-model.md](SPEC-manuscript-model.md) | 1 |
| `design-system` | [SPEC-design-system.md](SPEC-design-system.md) | 2 |
| `figure-engine` | [SPEC-figure-engine.md](SPEC-figure-engine.md) | 3 |
| `publish-engine` | [SPEC-publish-engine.md](SPEC-publish-engine.md) | 4 |
| `verify-harness` | [SPEC-verify-harness.md](SPEC-verify-harness.md) | 5 (specimen gate) |
| `source-intake` | [SPEC-source-intake.md](SPEC-source-intake.md) | 6 |
| `authoring-pipeline` | [SPEC-authoring-pipeline.md](SPEC-authoring-pipeline.md) | 7 |

## Scope assumptions (surface now, correct before approval)

1. One local Python project plus local Typst templates: eight module ids are submodules of one package, not eight packages or services. There is no hosted app, server or database.
2. The product surface is a local CLI plus an agent-guided skill. AI calls happen only in `authoring-pipeline`; publishing and verification are offline and model-free.
3. Typst + Matplotlib + CeTZ is the target stack. Setup may fetch pinned tools and packages; the build/verify run may not.
4. Deck PDFs are optional fixtures. The specimen manuscript is a small neutral fixture, so acceptance tests mechanics rather than subject content.
5. Manuscript is authored as YAML and validated against a closed JSON Schema (Draft 2020-12) with `schemaVersion` and `revision`. The schema is normative; YAML is the serialization. Closed objects, no unknown fields.
6. Supplied deck artwork proves permission to use the deck, not a third-party licence. Unknown rights stay explicit (`licence: unknown`, `rightsStatus: unconfirmed`) and are never inferred or silently upgraded.
7. Byte-identical PDFs are not required. "Reproducible layout" means: identical page count, page-by-page extracted text, illustration page map and numbering across two consecutive builds from the same inputs and pins.
8. Version policy: only versions verified by inspection are stated as facts; everything else is "pinned after toolchain validation". No invented pin values.

## Shared conventions (apply to every spec)

### Commands (proposed, not yet implemented)

```bash
uv sync --locked                                            # setup; may fetch pinned tools once
uv run bookify toolchain doctor --json                      # report local pins, fonts, packages
uv run bookify intake --source fixtures/decks --out build/intake --changed-only
uv run bookify author plan --intake build/intake --out build/author-plan.json
uv run bookify author apply --plan build/author-plan.json --manuscript content/specimen.yaml
uv run bookify build --manuscript content/specimen.yaml --out dist/specimen.pdf --offline
uv run bookify verify --pdf dist/specimen.pdf --manuscript content/specimen.yaml --report build/verify.json
uv run pytest -q
```

`bookify` is one thin dispatcher owned by `build-toolchain`; each subcommand delegates to its module. None of these exist yet.

### Errors

One shape everywhere: `{ "code": ..., "message": ..., "locator": ... }` on stderr and in JSON reports. Codes: `INPUT_INVALID`, `SCHEMA_INVALID`, `SOURCE_UNREADABLE`, `FONT_MISSING`, `GLYPH_MISSING`, `RIGHTS_INCOMPLETE`, `ILLUSTRATION_LIMIT`, `XREF_MISSING`, `BUILD_FAILED`, `NETWORK_DENIED`, `MODEL_CALL_DENIED`. Exit 2 for input/schema errors, 3 for build/verification failures, 1 for internal errors. No mixed error styles.

### Boundaries

- **Always:** validate at the boundary (CLI input, source files, third-party data); keep publishing a pure function of manuscript + assets; record uncertainty instead of guessing; keep the original repo and global skill untouched.
- **Ask first:** changing the manuscript schema incompatibly, adding a runtime dependency, changing tokens/presets approved in the specimen, widening rights assumptions.
- **Never:** call a model or the network from `build`/`verify`; invent unreadable values or metadata; infer a licence; let two illustrations share a final page; overwrite the global `pdf-book-design` skill.

### Rights and illustration policy

Every illustration record carries `path`, `originUrl`, `creator`, `licence`, `credit`, `caption`, `alt`, `kind` (`contemporary_photograph` | `later_depiction` | `reconstruction` | `conceptual_artwork`), `rightsStatus` (`verified` | `unconfirmed`). Publishing refuses `unconfirmed` records outside explicitly marked authoring drafts. Generated art may represent only conceptual or fictional subjects, never documentary evidence. Captions must name the kind for later depictions and reconstructions.

### Fonts and scripts

Explicit per-script fallback chain declared in one manifest: Latin/Vietnamese → Spectral; CJK → a verified local Japanese face; maths → a verified local maths face. A character not covered by the chain is a build error (`GLYPH_MISSING`), never a silent substitution. Verified today: Spectral covers all 134 precomposed Vietnamese characters and basic maths symbols, and has no CJK; a TrueType CJK fallback renders correctly; Noto CJK is CFF and its Typst support is unverified.

### Specimen acceptance gate (first deliverable)

One build must contain: chapter opener, body, Vietnamese + Japanese + special characters, an equation, a grouped-bar chart, a reconstructed process/model diagram, one sourced photograph with caption and credit, a table, and a working cross-reference. It passes only when `verify` proves offline, model-free rebuild; consistent layout across two builds; rendered-page inspection; text extraction; glyph coverage; and the one-illustration-per-page limit, including an adversarial fixture.

## Global non-goals for v1

No hosted service, auth, database, queue, multi-book library, web UI, EPUB/HTML output, OCR engine, or automatic image search. Presets expansion, extra chart types and the revised local skill's refinement follow the specimen; they are deferred, not cancelled.
