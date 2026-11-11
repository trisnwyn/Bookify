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
