# Capability Map: Bookify — authoring and offline publishing

Status: **approved 2026-11-10** by the project owner, with the v1 specification scope set by `.opencode/spec-handoff.md`. Boundaries, dependency direction and build order below are frozen; module specs trace to these ids and are indexed by `SPEC-INDEX.md`.

Approved scope constraints: local CLI + agent-guided skill; no hosted app and no new AI-provider service; Typst + Matplotlib + CeTZ remain the target stack; decks are optional fixtures; publishing must run offline with no model calls; the revised skill is local only.

## 1. Modules

| Module id | Responsibility | Depends on |
| --- | --- | --- |
| `build-toolchain` | Pin and vendor the toolchain, fonts and assets; record every substitution; provide the single offline build entry point and the no-network guard. Owns "reproducible, model-free, offline". | — |
| `manuscript-model` | The contract between authoring and publishing: one validated manuscript document (sections, blocks, source anchors, uncertainty, decisions, cached interpretations, chart data, diagram geometry, illustration records with rights/credits/alt). Owns schema, validation, fixtures, migrations. | — |
| `source-intake` | Deterministic extraction from supplied documents/slides: text with page/slide anchors, embedded raster extraction, content hashes and change detection. No interpretation, no model calls. | `build-toolchain` |
| `design-system` | Tokens (type scale, spacing, rules, semantic accents), font manifest with explicit fallback chain and per-script coverage, component presets (chapter opener, caption, credit, definition, example, case, assessment), specimen pages. | `build-toolchain` |
| `figure-engine` | Verified chart data → precise vector charts; editable diagram geometry → vector diagrams. Deterministic output, preset library, no model calls at render time. | `manuscript-model`, `design-system` |
| `publish-engine` | Assemble the final document: pagination, cross-references, contents, figure/table placement, illustration import and the one-per-page limit, caption/credit rendering, build command. Pure function of manuscript + assets. | `manuscript-model`, `design-system`, `figure-engine` |
| `authoring-pipeline` | AI-assisted interpretation of intake output into a manuscript: source-grounded writing, chart/diagram interpretation cached as data, uncertainty and decisions recorded, illustrations selected by section relevance and rights captured, incremental reprocessing of changed inputs only. Also owns the authoring guide/skill. | `source-intake`, `manuscript-model` |
| `verify-harness` | Automated acceptance: offline rebuild proof, glyph coverage per script, text extraction, rendered-page inspection, illustration-limit test, layout consistency, determinism check. | `manuscript-model`, `publish-engine` |

Eight responsibilities, one local project: module ids are package submodules and spec-selection keys, not services.

## 2. Dependency direction

Read `A → B` as **"A depends on B"**. The table above is the normative statement; this list is the same graph, spelled out to avoid arrow ambiguity.

```
source-intake      → build-toolchain
design-system      → build-toolchain
authoring-pipeline → source-intake, manuscript-model
figure-engine      → manuscript-model, design-system
publish-engine     → manuscript-model, design-system, figure-engine
verify-harness     → manuscript-model, publish-engine
build-toolchain    → (no module)
manuscript-model   → (no module)
```

No cycle: `manuscript-model` is a leaf contract; `publish-engine` never writes back into authoring; `verify-harness` is read-only over built artifacts. `build-toolchain` is depended on but depends on nothing, so it cannot create a loop.

## 3. Boundary contracts (owned by the named module)

- **`manuscript-model` is the only seam** between AI-assisted authoring and deterministic publishing. Publishing reads a validated manuscript and its assets; it never queries a model, the network, or an authoring cache.
- `source-intake` hands over **anchors + hashes**, not prose: every extracted unit addresses a source file and a page/slide, so citations and re-checks survive re-runs.
- `figure-engine` consumes **data/geometry**, never pictures: verified chart values and diagram node/edge positions are the inputs; rendered vectors are disposable outputs.
- `publish-engine` consumes **illustration records** (local path, original URL, creator, licence, credit, caption, alt, kind: contemporary photograph / later depiction / reconstruction) and owns the deterministic placement rule.
- `authoring-pipeline` owns **cached interpretations** for audit and reuse; publishing stays correct when every cache and model output is deleted and only the manuscript and assets remain.

## 4. Build order

| Step | Modules | Why here |
| --- | --- | --- |
| 0 | `build-toolchain` | Nothing else can be built twice the same way until tools, fonts and packages are local and pinned. |
| 1 | `manuscript-model` | Everything else reads or writes this contract; a fixture manuscript lets publishing proceed without authoring. |
| 2 | `design-system` | Tokens, fonts and presets are inputs to both figure and page rendering. |
| 3 | `figure-engine` | Charts and diagrams must exist before pages can place them. |
| 4 | `publish-engine` | First vertical slice: specimen from the fixture manuscript. |
| 5 | `verify-harness` | **Specimen gate** — the first deliverable is accepted only when offline rebuild, glyph coverage, text extraction, render inspection and the one-illustration-per-page test pass. |
| 6 | `source-intake` | Real inputs replace the fixture; extraction is deterministic and testable in isolation. |
| 7 | `authoring-pipeline` | Incremental authoring over real sources, once the contract and the renderer are proven. |
| 8 | Presets expansion + authoring guide | Only after the specimen is accepted; this is deferred expansion, not a new module and not cancellation. |

Rationale: the intake makes the publishing specimen the proof point for the intended stack, so publishing is built as a thin slice before the AI-assisted flow. `source-intake` and `authoring-pipeline` remain in scope; deferring their build step does not cancel them.

## 5. Deliberately outside the map

- No separate "AI provider" module: model access is an authoring-stage concern inside `authoring-pipeline`, never a publishing dependency.
- No separate "rights database" module: rights live on each illustration record in `manuscript-model`.
- No separate "CLI" module: each module exposes functions; `build-toolchain` exposes the documented build command and dispatches subcommands to them.
- No web app, server, database or background jobs: this is a local authoring + build pipeline.

## 6. Decision status after spec handoff

| Decision | Status |
| --- | --- |
| Publishing stack | **Resolved:** Typst + Matplotlib + CeTZ remain the target. Local setup may fetch pinned tools/packages; the publishing/verification run itself must be offline. Pins are recorded only after toolchain validation. |
| Source corpus | **Resolved:** supplied source documents may be used as optional fixtures; no corpus is required for the specimen. |
| Rights basis | **Resolved in principle:** permission to use supplied deck artwork is not proof of third-party licensing. Unknown rights stay explicit; the specimen uses one clearly licensed photograph. |
| Accent semantics | **Proposed in `SPEC-design-system.md`:** one restrained accent hue with semantic roles; flagged for approval. |
| Specimen subject | **Proposed in `SPEC-manuscript-model.md`:** a small neutral fixture manuscript, not an existing chapter, so the specimen tests mechanics rather than content. |

Module specs live at the project root as `SPEC-<module-id>.md`; shared conventions and the acceptance gate are in `SPEC-INDEX.md`.
