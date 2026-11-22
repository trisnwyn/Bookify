# Progressive map — Bookify

A living ladder. One item is active at a time; each has a gate that must be met
before the next starts. Items may be reordered, never silently dropped.

Baseline: `main` checkout, 2026-11-14. All timings on this host unless marked
otherwise. Numbers marked *(measured)* were taken today with `cProfile` and
`/usr/bin/time` on the current `public-main` code; numbers marked *(benchmark)*
come from the v1 report for the Principles of Accounting book (7 decks,
173 source pages → 60-page PDF, 2 h 17 min wall clock).

---

## Baseline numbers

| Fact | Value | Source |
| --- | --- | --- |
| Full build, 62 pp, accounting manuscript, current engine | 135 s | measured |
| — of which `report.analyse` | 128 s (95%) | measured |
| — `pdftotext` spawns in one analysis pass | 2,276 for 68 sections | measured |
| Full verify, same PDF | 426 s | measured |
| — rhythm check | 243 s (131 rasters for 62 pages) | measured |
| — readability check | 120 s (the same 2,276 spawns) | measured |
| — subprocess wait share | 77% of verify | measured |
| One build + verify cycle | 9 m 21 s | measured |
| v1 end-to-end run | 137 min, 11 builds, 6 inspection passes | benchmark |
| Test suite | 716 s, 102 `build()` calls in 24 files, 15 shared fixtures | measured |

These are the numbers every item below is judged against. Anything that does
not move one of them does not belong in this list.

---

## 1. Textbook layout  ← ACTIVE

Why: the v1 feedback found seven defects, and six of them share one cause —
the engine has no composition concept, only a text flow with rare plates. Page
count and density were optimised instead of reading rhythm.

Scope: the engine's default template and presets, not just one manuscript.
A per-book override would fix the accounting book and leave every future book
broken in the same way.

Sub-items to design (one at a time, in this order):

- [ ] Definitions inline — bold term, colon, definition in one paragraph;
      term tables kept separately for chapter glossaries.
- [ ] Heading hierarchy numbered — chapters, `1.1`, `1.1.1`; contents mirror it;
      appendices as `Appendix A/B`.
- [ ] Chapter opener — numeral, rule, standfirst, kicker; consistent but not
      identical across chapters.
- [ ] Composition variety — at least one earned plate or figure per chapter;
      side compositions only where a diagram earns it; no multi-column, no text
      wrap (engine limits).
- [ ] Captions and source lines — one centred 8.2 pt element; the separate
      left-aligned 9.2 pt note is removed or folded into the caption.
- [ ] Heading spacing — explicit separation before h2/h3, measured, not eyeballed.
- [ ] Cover — a designed typographic cover in the house style, not the stock one.

Gate: accounting manuscript rebuilt with the new defaults; 64–68 pp; each of the
seven v1 defects closed and shown on a rendered page; `verify` passes; all pages
inspected at 110 dpi.

Risk: layout changes touch every fixture and every golden PDF. Re-baselining is
part of the gate, not an accident to be worked around.

---

## 2. Measurement layer

Why: build and verify each re-derive the same facts with per-page subprocesses.
There is no single measurement of a PDF, only repeated ones.

Change: one `PdfMeasure` — a batch `-layout` extraction, a batch `-bbox-layout`
extraction, one raster cache keyed by (page, dpi), consumed by `report`,
`readability`, `rhythm`, `plates`, `geometry`, `cover`.

Targets: build 135 s → ≤ 15 s; verify 426 s → ≤ 120 s; cycle 9 m 21 s → ≤ 2 m 15 s.

Gate: PDF byte-identical; `verify.json` identical except timing fields; the
existing suite passes unchanged.

---

## 3. Incrementality

Why: the loop is a batch compiler driven as an editor. 11 builds and 6 full
inspection passes for one book, each paying full price.

Change, in increasing risk:
- section-scoped build (`--only-section`) for authoring previews;
- changed-page verification that reports what it reused;
- page-diff inspection: hash rendered pages between builds, surface only what
  changed.

Targets: an edit–inspect iteration under 60 s; inspection views per pass down
from ~60 pages to the pages that changed.

Gate: a partial verification must state its coverage explicitly — "gate: pass
(18 of 62 pages changed, 44 reused from build `<sha>`)" or it may not pass.

---

## 4. Instrument pinning

Why: Typst, fonts, CeTZ and Tesseract are hash-pinned; the measurement
instrument is not. `toolchain doctor` reports "all local" without Poppler
installed, and every tolerance is calibrated against Poppler's line boxes
(`LINE_BOX_EM = 1.5217`).

Change: pin Poppler (and Ghostscript where used) in `toolchain.lock.json`;
extend `doctor` and `run_or_fail`; record the instrument in the build and verify
reports.

Gate: a machine without Poppler fails `toolchain doctor` with a named code;
reports name the instrument version used.

---

## 5. Test harness

Why: 716 s for ~1000 tests, dominated by repeated full builds.

Change: session-scoped build fixtures, one verify fixture per manuscript, and a
retention policy for `.cache/publish-*` (715 empty directories today).

Target: ≤ 300 s without dropping a test.

Gate: same test count, same assertions, new timing recorded.

---

## Parked

- **Rust rewrite.** Not now. Measured ceiling is ~10–15%: 95% of build and 77%
  of verify is waiting on external processes, which a port would still spawn.
  Real wins require in-process PDF (pdfium/mupdf), which is available in Python
  today via `pypdfium2`; the language is not the constraint. Revisit only for
  single-binary distribution or an in-process PDF decision.
- **Parallel chapter authoring.** High risk of voice drift and cross-reference
  breakage; only if items 2–3 do not make the loop usable.
- **OCR speed and Vietnamese accuracy.** Separate budgets; not on this ladder.

---

## Decision log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-11-14 | Layout before measurement | Layout changes invalidate golden PDFs; do it before re-baselining timing. |
| 2026-11-14 | No Rust port | Bottleneck is the process boundary, not the language. |
