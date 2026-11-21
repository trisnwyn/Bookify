# Proposal — what to take from WeasyPrint, and what not to

Companion to [`weasyprint-report.md`](weasyprint-report.md). This document proposes a
specific integration, names the files it touches, and states what it costs. It does not
change any approved spec; where a proposal would, it says so and stops for the owner.

**Recommendation in one line:** take WeasyPrint's **PDF conformance knowledge**, its
**converging pagination pattern** and its **hyphenation limits**, and leave its layout
engine, its CSS stack and its dependencies out of Bookify.

## 0. Status (2026-11-21)

Landed: **W1** (the template now sets `document(title:, author:)` from the manuscript,
so every PDF carries its own identity while the pinned `CREATION_TIMESTAMP` keeps builds
comparable), **W2** (new `docmeta` verify check, report `schemaVersion` `1.2`; amendments
recorded in `SPEC-verify-harness.md`), and **W5** (placement now converges instead of
counting attempts, ceiling eight, `placementPasses` in the build report; amendment
recorded in `SPEC-publish-engine.md`).

Open question 3 is answered in the affirmative and question 1 is now a requirement: the
compile passes `--pdf-standard a-2b`, and `docmeta` proves the claim. Specimen and
catalogue both compile unchanged under it — same page count, identical extracted text —
so archival conformance costs no layout. Question 2 (equation `alt` text) remains the
only thing blocking PDF/UA; question 5 (re-baseline) still gates W4.

Open: **W4** (hyphenation and language) waits on the re-baseline question in §7;
**W3** (alt text and tagged PDF) waits on the equation `alt` schema decision; **W6**
(print-ready pagination) is a product decision.

Consequence worth stating: the three shipped evidence workspaces under
`content/agent-skill/*/evidence/` were built before W1, so their recorded PDFs carry no
title or author and no longer replay a passing gate. They need a rebuild from their
documented recipe, which changes their recorded SHA-256 values — an owner call, not a
silent edit.


---

## 1. Why not the obvious thing

The obvious integration is "use WeasyPrint to render the book". It should be rejected,
and the reason is not taste:

| Constraint (from `SPEC-INDEX.md`, `SPEC-publish-engine.md`) | Effect of adopting WeasyPrint as the renderer |
| --- | --- |
| Build is a pure function of manuscript + assets + pinned tools | Adds Pango, HarfBuzz, fontconfig and 8 Python packages to the pinned set |
| Offline, model-free, `bwrap --unshare-net` | Still offline, but the toolchain doctor now has a native-library matrix to verify |
| Design values are *measured* (0.660 em line box, 475.28 pt plate) and proven at 300 dpi | CSS's line-box model replaces them; every rhythm baseline invalidates |
| Figures are Matplotlib + CeTZ vectors through Typst | Needs re-plumbing to SVG/raster for a different renderer |
| One-illustration-per-page placement over a compiled page map | Rule must be re-implemented in a different break model |
| WeasyPrint's own policy: rendering changes every release | A pinned WeasyPrint still moves when the pin moves; layout is not a contract |

Bookify would spend its verified surface (theme, rhythm baselines, plate widths, cover
ink gate) to buy capabilities it can obtain directly. The rest of this document is those
capabilities.

---

## 2. Evidence the proposal rests on

All measured here, on the pinned toolchain, not assumed.

| Probe | Result |
| --- | --- |
| `pdfinfo dist/specimen.pdf` | No `/Title`, `/Author`, `/Subject`, `/Keywords` |
| `pdfinfo -meta dist/specimen.pdf` | XMP has only `CreatorTool`, `dc:language`, dates, `NPages`, `format`, `InstanceID` — no `dc:title`, `dc:creator`, `dc:description` |
| `typst compile --help` (0.15.1) | `--pdf-standard a-1b…a-4e, ua-1`; tagging on by default |
| Specimen recompiled with `--pdf-standard a-2b` | **Succeeds unchanged**; XMP gains `pdfaid:part 2`, `pdfaid:conformance B`; `OutputIntent`/`GTS_PDFA1` present |
| Specimen recompiled with `--pdf-standard a-2b,ua-1` | **Fails**: `missing alt text` (equation, chart, illustration) and `missing document title` |
| Probe with `set document(title:)` + `image(alt:)` + `figure($…$, alt:)` | `a-2b,ua-1` compiles cleanly; `pdfinfo` shows `Title`, `Tagged: yes` |
| Narrow-measure justified probe | Vietnamese: no hyphenation at all; English: `char-` orphaned on its own line |
| `pdfinfo -meta` availability | Present in pinned Poppler 26.01 — no new dependency needed to verify metadata |

Two facts follow directly. Archival conformance is **one flag away**. Accessibility is
**two plumbing gaps away** (image alt text is already in the illustration records; the
document title is already in the manuscript). Neither needs WeasyPrint code — it needs
WeasyPrint's *field list*, which is `pdf/metadata.py`, `pdf/pdfa.py` and `pdf/pdfua.py`.

---

## 3. Workstreams

Effort bands are estimates, not measured: S = under a day, M = one to two days,
L = a week or more. Every workstream that changes the template changes page count and
hashes, so each ends with the rule Bookify already states: rebaseline only after rendered
measurements pass.

### W1 — Give the PDF an identity (S) · recommended first

The file currently has no title and no author. Fix is small and has no visual effect.

- `typst/templates/book.typ`: add `set document(title: …, author: …, keywords: …, date: …)`
  fed from `doc.metadata`.
- `src/bookify/publish/normalize.py`: nothing new needed — `metadata` already reaches the
  template; `author`, `subtitle`, `title`, `languages` are present in `book.json`.
- `src/bookify/publish/typst_driver.py`: keep using the pinned `CREATION_TIMESTAMP` so the
  build stays deterministic.

Acceptance: `pdfinfo` reports `Title` and `Author`; XMP carries `dc:title`, `dc:creator`
and `dc:language` matching `metadata.languages`; two consecutive builds still agree on
page count, text and placement map.

### W2 — A `docmeta` verify check (M) · recommended second

Nothing currently fails a book whose PDF says nothing about itself. This closes that.

- New `src/bookify/verify/checks/docmeta.py`, registered in
  `src/bookify/verify/runner.py` beside the other eighteen checks.
- Read the XMP with `pdfinfo -meta` and parse with stdlib `xml.etree`; read `/Info` fields
  from `pdfinfo`. No new dependency.
- Compare `dc:title` / `dc:creator` / `dc:language` against the manuscript; fail on
  divergence or absence, and fail on a field the manuscript does not contain (Bookify's
  "never invent metadata" rule, applied to the file).
- When a standard is requested, assert `pdfaid:part` / `pdfaid:conformance`, the
  `OutputIntent` with `GTS_PDFA1`, and — if `ua-1` — `StructTreeRoot`, `MarkInfo` and
  `Lang`.
- Report `schemaVersion` bumps to `"1.2"`; the gate physics is unchanged.

Reference for exactly which fields each standard obliges: `weasyprint/pdf/metadata.py`
(field mapping), `pdf/pdfa.py` (variant table and removals), `pdf/pdfua.py`, `pdf/tags.py`.

### W3 — Alt text and a tagged-PDF gate (M, needs one schema decision)

`illustrations[].alt` already exists and is enforced by the rights spec. It is not passed
to Typst, so PDF/UA-1 refuses the build.

- `typst/templates/book.typ`: pass `alt:` on every `image()` and on math figures.
- Equations are the blocker: `blocks[type=equation]` has `caption`, `id`, `label`, `typst`
  and no `alt`, and inline maths inside prose needs its own alt too. That is a
  **manuscript-schema change** — `SPEC-manuscript-model.md` — so it is an "ask first"
  item, not a work item.
- Interim honest position: adopt `a-2b` now (no alt needed), record PDF/UA as blocked on
  the equation-alt decision, and do not claim accessibility.

### W4 — Hyphenation and language policy (M, reference-driven)

WeasyPrint's relevant knowledge is small and precise: `hyphens: auto` plus
`hyphenate-limit-chars: (5, 2, 2)` (default in `css/properties.py`), `hyphenate-limit-zone`,
`hyphenate-character`, and `lang` driving dictionary selection in `text/line_break.py`.

Bookify today sets no language anywhere in `typst/` and shows both defects named in §2.

- Declare `lang` per manuscript language in the template.
- Enable hyphenation for languages that have a dictionary; record Vietnamese as
  unsupported rather than letting English rules fire on Vietnamese words.
- Typst exposes no explicit min-chars knobs, so enforce the *outcome* in `verify`:
  parse `pdftotext` output and fail or warn when a line ends in a hyphen with fewer than
  two characters carried to the next line — WeasyPrint's 2/2 rule expressed as a
  measurement rather than a property.
- Measure justification slack on Vietnamese pages and record the band honestly, in the
  same style as the existing readability warnings.

This is the only workstream that changes every line break and therefore every page
baseline. It needs the owner's agreement that a re-baseline is acceptable.

### W5 — Converge instead of counting attempts (S–M)

`SPEC-publish-engine.md` allows three recompiles and fails on a fourth disagreement.
WeasyPrint's `layout_document()` instead stops when nothing changed: after each pass it
asks whether any dependent content changed or whether a page-count-dependent counter
moved, and repeats only then, with `max_loops=8` as a safety net.

- `src/bookify/publish/illustrations.py`: stop when the placement map, section page map
  and page count are all unchanged; keep a hard ceiling of eight passes.
- Keep `ILLUSTRATION_LIMIT` for genuine non-convergence — the error means "this document
  oscillates", not "it needed a fourth try".
- Report the number of passes in `build-report.json` so a converging build is visible.

This is a 30-line change with a better failure story, and it is the one place where
WeasyPrint's control flow is directly transferable.

### W6 — Print-ready pagination (L, product decision) · not recommended yet

Recto/verso starts, blank versos, mirror margins, named pages, `:blank` page styling.
WeasyPrint has the reference model in `layout/page.py` (`PageType`, `page_side`,
`break: recto|verso` with automatic blank insertion, page groups for named sequences).

But `SPEC-publish-engine.md` currently states the opposite as a deliberate choice: "no
blank verso or parity page is added". Doing this means reopening an approved amendment,
not adding a feature. It is listed here so the option is visible, not because it should
start.

### Not proposed

- **Vendoring `CounterStyle`.** Complete and tested, but Bookify numbers with printed
  chapter/appendix strings and needs no roman or alphabetic styles yet. Vendor it only if
  front-matter roman folios become a requirement; if so, take it under BSD-3 with the
  notice in `LICENCES.md`.
- **Vendoring the outline algorithm.** `anchors.py::make_page_bookmark_tree` is the right
  nesting rule, but Poppler has no outline dump, so a check would need a new parser
  before the rule is useful. Read it if nested bookmarks become a gate.
- **The pixel-map test idiom.** Nice, but Bookify's verification is measurement-based
  (`verify/checks/rhythm.py`, `cover.py`) and its baselines are tolerances, not pixels.
  Borrow the *idea* of a legible declared expectation; do not port the harness.
- **`URLFetcher` as code.** Bookify's offline guarantee is `bwrap --unshare-net` plus
  `guard.offline()`, which is stronger than an allow-list. The pattern is worth knowing;
  the code is not needed.
- **WeasyPrint as an HTML→PDF side path.** It has no place in a pipeline whose input is
  a closed YAML schema. Revisit only if a "web source" intake mode is ever approved, and
  then read `urls.py` before writing the fetcher.

---

## 4. Order of work and what each one proves

| Order | Workstream | Proves | Re-baseline needed |
| --- | --- | --- | --- |
| 1 | W1 identity | The PDF describes the book it contains | No (metadata only) |
| 2 | W2 `docmeta` | The gate can fail a mislabelled or non-conforming file | No |
| 3 | W5 convergence | Placement stops for a reason, not for lack of attempts | No (same placements) |
| 4 | W4 hyphenation | Justification quality is measured, not assumed | **Yes** — every page |
| 5 | W3 alt/tagged | Accessibility is either achieved or honestly declared blocked | Schema decision first |

W1 and W2 together are the highest value per hour: they close a real, invisible defect
(untitled, unattributed books that pass the gate) and they make any future PDF/A claim
verifiable rather than decorative.

---

## 5. Licensing actions

- **Reading WeasyPrint** (this report, the proposal, the field lists): no obligation.
- **Vendoring any WeasyPrint file**: BSD-3-Clause requires retaining the copyright
  notice and the licence text, and forbids using the authors' names to endorse Bookify.
  Add the file to `LICENCES.md` beside the existing third-party records.
- **Never copy from Pyphen**: it is triple-licensed GPL-2.0+/LGPL-2.1+/MPL-1.1. Only the
  MPL-1.1 option is compatible with an MIT project, and it is file-level copyleft.
  WeasyPrint's own BSD-3 code is the only part safe to copy.
- **If WeasyPrint is ever added as a dependency** (not recommended): pin it in
  `toolchain.lock.json`, record its native libraries in `toolchain doctor`, and note that
  70.0 was a security release (CVE-2026-55073).

---

## 6. Risks

1. **Re-baselining under time pressure.** W4 changes every page. Bookify's own rule —
   rebaseline only after rendered measurements pass — must hold, or the gate becomes
   decorative.
2. **Conformance claimed, not verified.** Passing `--pdf-standard a-2b` is Typst asserting
   conformance; only W2 makes it evidence. Do not ship the flag without the check.
3. **Determinism.** Any date written into `set document(...)` must come from the pinned
   `CREATION_TIMESTAMP`, or two builds stop matching on text and hashes.
4. **Half-accessibility.** Tagged PDF without alt text is worse than untagged: it claims a
   structure it does not have. Either finish W3 or stay on `a-2b`.
5. **Silent typographic change.** Enabling hyphenation without the W4 measurement simply
   moves the defect from "no hyphenation" to "bad hyphenation".

---

## 7. Open questions for the owner

1. Is **PDF/A-2b** a product requirement (archival deposit, library ingestion) or a
   nicety? If a requirement, W1+W2 become part of the gate, not an add-on.
2. Is **PDF/UA-1** in scope, and if so may the manuscript schema gain `alt` for equations
   and inline maths? Without that the answer is no.
3. May the pinned compile invocation gain `--pdf-standard`, with the value recorded in
   `toolchain.lock.json` beside the Typst pin?
4. Is **print-ready** output (recto starts, blank versos, mirror margins) in scope? That
   reopens the publish-engine amendment that currently forbids blank pages.
5. Is a full **re-baseline** of page counts and hashes acceptable to fix hyphenation and
   language handling? If not, W4 must wait for a planned rebaseline.
