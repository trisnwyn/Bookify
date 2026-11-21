# SPEC-verify-harness

Module id: `verify-harness` · depends on: `manuscript-model`, `publish-engine` · build step 5 (specimen gate) · status: approved 2026-11-10.

## Objective

Decide, with evidence, whether the specimen is acceptable. The harness converts the intake's first-deliverable claims into checks with named pass conditions, so "it looks right" cannot pass and a regression cannot be reported as success. It is read-only over built artifacts and offline.

## Tech stack

Python checks over Poppler output (`pdfinfo`, `pdffonts`, `pdftotext`, `pdftoppm`) and the build report; no new runtime service. Poppler 26.01.0 and Ghostscript 10.06.0 are verified present. Rendering inspection uses the locally produced page images; the harness never fetches anything.

## Commands (proposed, not implemented)

```bash
uv run bookify verify --pdf dist/specimen.pdf --manuscript content/specimen.yaml --report build/verify.json
uv run bookify verify --pdf /tmp/adversarial.pdf --manuscript fixtures/adversarial/illustrations.yaml --report build/verify-adversarial.json
uv run pytest -q
```

## Project structure

```
src/bookify/verify/
  runner.py                  # orchestrates checks, writes one report
  checks/
    offline.py               # guard log, no network/model attempts
    determinism.py           # two builds, compared
    glyphs.py                # per-script coverage and pdffonts embedding
    text.py                  # extracted text expectations
    pages.py                 # page count, A4, non-blank render, review record
    illustration_limit.py    # at most one per page, from the PDF
    rights.py                # caption/credit/licence/kind completeness
    xrefs.py                 # labels resolve, numbering matches contents
fixtures/expected/specimen.json   # expected pages, text probes, placement map
```

## Checks and pass conditions

| Check | Pass condition |
| --- | --- |
| Schema | `manuscript check` passes; no warnings promoted to success |
| Offline | Guard active; report shows zero network and zero model attempts; `NETWORK_DENIED`/`MODEL_CALL_DENIED` count is 0 |
| Build determinism | Two builds from unchanged inputs: equal page count, equal page-by-page extracted text, equal illustration page map, equal figure/table numbers |
| Page geometry | A4 (595.28 × 841.89 pt ± 1); expected page count; no blank page |
| Glyphs | Every character in the manuscript covered by its script chain; every visible face in `pdffonts` has `emb yes`; no `.notdef` in render |
| Text extraction | Extracted text contains: chapter title, a Vietnamese string with diacritics, a Japanese string, the equation's symbols, a caption, a credit line, and a resolved `§` reference |
| Illustration limit | No page contains more than one illustration; adversarial fixture produces exactly one deferral and no page with two |
| Rights | Every illustration has licence, credit, caption, alt and kind; `unconfirmed` rights fail a normal build; reconstructions are named as such in the caption |
| Xref and numbering | Every `{ref:}` resolves; contents page numbers match printed folios; figure/table numbers are sequential |
| Layout consistency | Same block sequence, no orphaned heading at page foot, no split figure block; page images inspected and the inspection recorded |
| Model-free | No model cache is read during build; deleting `build/` leaves results unchanged |

Rendered-page inspection is a recorded human/agent step: the report stores `reviewedBy`, `reviewedAt` and a contact-sheet path. A check that cannot be automated is marked `manual` with its evidence, never `passed`.

## Report

One JSON file: `{ schemaVersion, generatedFrom { manuscriptRevision, pdfSha256 }, pins, checks: [{ id, status: "pass" | "fail" | "manual", detail, evidence }], gate: "pass" | "fail" }`. Exit 0 only when `gate == "pass"` and no check is `manual` without an inspection record. Exit 3 for a failed gate.

## Code style

```python
def check_illustration_limit(pages: list[PageIllustrations]) -> CheckResult:
    """Fail if any page carries more than one illustration."""
    offenders = [p for p in pages if len(p.illustrations) > 1]
    if offenders:
        return CheckResult.fail("ILLUSTRATION_LIMIT", [p.number for p in offenders])
    return CheckResult.pass_("no page has two illustrations", evidence=len(pages))
```

## Testing strategy

`pytest` under `tests/verify/`:

- Harness self-tests use deliberately broken fixtures: two illustrations on one page, a dangling xref, a missing Japanese glyph, an unembedded font, a blank page, a timestamp-only difference — each must fail for the right reason and no other.
- A passing specimen report must not contain `manual` checks without inspection evidence.
- Determinism check itself is tested with two identical PDFs and with one differing placement.
- Report schema is validated; exit codes match the documented mapping.

## Boundaries

- Always: name the failing check and its evidence; compare against stored expectations; keep the harness read-only; record manual inspection honestly.
- Ask first: adding a gate check that can fail an otherwise acceptable book, changing expected page/text baselines.
- Never: fetch anything; edit the PDF or manuscript to make a check pass; mark a manual check as automated; report "verified" from a single run.

## Success criteria

1. The specimen gate passes only when every automated check passes and the inspection record exists.
2. The adversarial illustration fixture fails on exactly one check, `ILLUSTRATION_LIMIT`, with the offending pages listed.
3. The report is machine-readable, reproducible and contains no hand-waved status.
4. Each intake claim for the first deliverable maps to at least one check above.
5. Two consecutive spec-approval-stage builds produce the same gate outcome.

## Amendment — Bookify v2 checks and warnings (2026-11-14)

Per the owner-approved `SPEC-bookify-v2.md` §7. Existing check ids and
conditions are unchanged; the additions are additive.

### New and extended checks

| Check | Pass condition | Severity |
| --- | --- | --- |
| `cover` | Title at 34 pt (±1) in ≤3 rendered lines, subtitle/institution/footer when present, at least one full-measure rule, zero chromatic pixels, no image, no folio, ink inside the 60 pt margin, index or ledger matches the document | fail |
| `definitions` | Each definition renders inline as `Term: definition` at body size; no isolated small term line | fail |
| `xrefs` (extended) | Contents entries are numbered and match printed folios; body headings print the same number; `§` references match a known printed number; figure/table/photograph numbering is sequential | fail |
| `rhythm` | Body 15.30 and paragraph 20.70 where sampled; h2 ≥36.0 pt and band ≥8.0 pt; h3 ≥31.0 pt and band ≥5.0 pt; h1 deck ≥32.7; wrapped headings keep 30/16.5/14; below every heading a measured white row between its descenders and the next line's ascenders (≥ one 300-dpi raster row, 0.24 pt; a merged band fails); no adjacent headings. Zero samples are recorded, never invented | fail |
| `plates` | Every level-1 opener has numeral 40 pt, a full-measure rule and title; a chapter with a visual carries a visual at the measure ±1 pt | fail on opener; warn on a missing plate |
| `captions` (extended) | For charts, diagrams and full illustrations the description and provenance are one centred caption at `type.caption`; credit separate and left at 7.6 pt; no separate 9.2 pt figure note; table/equation captions unchanged. Coverage requires both single- and multi-line captions across the figure set | fail |
| `readability` | Four metrics computed from the PDF and manuscript, bands applied, exemptions listed; out-of-band values are warnings with values, bands and pages | warn |
| `review` (extended) | Contact sheet and reviewer/time, and one recorded decision per warning id in `--review-notes` (JSON object mapping id → decision) | manual; unanswered warning fails |

The physics of the gate is unchanged: `fail` fails the gate, `manual` without
evidence fails, `warn` does **not** fail by itself. A missing warning decision
fails `review`, which then fails the gate. `report.schemaVersion` becomes `"1.1"`
and the report lists every warning with its check, id and evidence. Exit codes
stay 2 (input/schema) and 3 (build/verification).

### Measured basis

- Caption centring keeps the independent 2.0 pt geometry gate; the caption and
  provenance lines share one target centre.
- Geometry canvases are the text measure for charts, diagrams and full
  illustrations (475.28 pt), and the declared 46 % column for side illustrations.
  A full-measure dark row is removed as ornament only on narrower canvases, so a
  figure's own frame remains its ink.
- The cover title size is derived from the rendered line box divided by the
  measured 1.5217 em line-box ratio of the pinned faces, never from the declared
  token.
- Readability bands: words per page median 140–650, any body page 60–800, tables
  per page ≤2, paragraph words median ≤150 and any ≤240, dense run ≤3 pages above
  650 words. Cover, contents, chapter-opener, plate and appendix pages are
  exempt from the thin-page warning with the reason listed. Calibration basis is
  the measured public books, not an aspiration.

### Residual limits

Zero-sample rhythm dimensions are reported as zero rather than failed; the
type-token pitches are independently pinned by rendered measurement tests. The
plate width for vector charts/diagrams is the declared measure (a vector figure
has no raster image object) and the template token is pinned by a design test;
raster illustration plates are measured from the placed image box.

## Amendment — PDF identity check (2026-11-21)

Additive. Implements W1 and W2 of `docs/weasyprint-integration-proposal.md`, after
the WeasyPrint study in `docs/weasyprint-report.md`.

- New check `docmeta`. It reads the PDF's own `/Info` fields and XMP packet with
  the already-pinned Poppler (`pdfinfo`, `pdfinfo -meta`) and compares them with
  the manuscript: the title must be present and equal, a declared author must be
  present and equal, and a file that names an author the manuscript does not
  contain fails (the "never invent metadata" rule, applied to the file).
- A standard the file *claims* is checked structurally: PDF/A needs a valid
  conformance level and an `/OutputIntent`; PDF/UA needs a tagged file. A file
  that claims no standard is not penalised, so the check does not require
  `--pdf-standard` to be turned on.
- The declared document language is evidence, not a gate. Typst sets it through
  `text(lang:)`, which changes line breaking, so requiring it here would move
  every page baseline; the mismatch stays visible in the report until that work
  lands.
- `report.schemaVersion` becomes `"1.2"`. Gate physics, exit codes and the
  warning/review contract are unchanged.
