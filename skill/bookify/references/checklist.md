# Authoring self-critique

Use this as your own review pass before you hand the PDF over. It is not a
developer gate and not a substitute for reading the pages. Tick only what you
actually verified; write `unresolved` where you could not.

Mode: `source-faithful` / `teachable` (from the selected command — do not mix
contracts in one book).

## Before you author

- [ ] The source was read, not guessed; the source file is unchanged.
- [ ] The intake/evidence exists and every page has a stable anchor (page text or
      an honest `unresolved` note).
- [ ] Image-only or unreadable units are listed and none has fabricated text.
- [ ] The source's own structure, figures, tables and exercises are inventoried.
- [ ] Rights for every reused image or external source are known, or explicitly
      `unconfirmed`.

## Coverage, order and provenance

- [ ] Every source unit is covered, merged or excluded with a reason.
- [ ] Strict: content follows source page order; merges/reorders are recorded.
- [ ] Teachable: every reorder, merge, split and omission is recorded with a
      decision.
- [ ] Every factual block has a source anchor (and, in teachable mode, every
      external claim has a permissioned citation).
- [ ] No invented number, name, date, category, label, quote or citation.
- [ ] Machine-read blocks are `inferred`, never `verified`; each names its OCR
      region and (for tables) `ocr-table-v1` and the reconstruction note.
- [ ] Every machine-read digit has a recorded cross-check; a below-threshold OCR
      page is excluded with its measured reason, not summarised into a guess.
- [ ] No OCR number became a chart value, and the `MACHINE_READ_DIGITS` warning
      is answered in the review notes.
- [ ] An unreadable label, value or name is `unresolved`/`null` with a note, not
      a plausible guess.
- [ ] Approximate or inferred values remain visibly approximate/inferred.
- [ ] Presentation-only text in strict mode asserts no new fact.

## Additions and mode boundaries

- [ ] Strict: no outside material, no teaching apparatus, no reading list, no
      glossary, no exercises unless the source supplies them.
- [ ] Teachable: teaching apparatus is recorded as `explain`/`example`/
      `assessment`/`glossary` or equivalent, and labelled as framing where it
      could be mistaken for source fact.
- [ ] Outside enrichment was explicitly requested and permitted, cited at the
      point of use, and recorded with a stable locator or local hash.
- [ ] No outside enrichment arrived by “quick check”, prior permission or “use
      your judgement”.
- [ ] Illustrative examples are labelled illustrative; they are not presented as
      real observations.
- [ ] Quotations, attribution, uncertainty notes and enrichment citations remain
      visible.

## Voice (teachable)

- [ ] The chapter states its teaching point directly instead of narrating the
      input.
- [ ] The chapter defines terms where needed, works an example, and gives a
      short check that uses its own vocabulary.
- [ ] Recurring “the materials/course/slides/provided content say” framing is
      removed, including paraphrases.
- [ ] Naming the source survives only where attribution, quotation, uncertainty
      or enrichment citation is the point.
- [ ] A semantic read of every chapter finds direct prose, legitimate citations
      and no upgraded evidence. Exact banned-phrase checks are regression aids,
      not the review.

## Visual form and composition

- [ ] The visual system is coherent: hierarchy, body measure, margins, serif
      family and white space are intentional.
- [ ] Figures do real work; there is no filler and no quota. A book with no
      illustration is acceptable if the material does not need one.
- [ ] Composition is explicit data: `full`, `side-left` or `side-right`; absent
      means full; charts and diagrams carry no composition.
- [ ] A side illustration's companion is the immediately following prose block in
      the same section, used once, at most 520 collapsed characters including
      title/term/note.
- [ ] The composition is unbreakable: image, caption, credit and companion share
      one page; the whole unit defers if needed; no split or silent drop.
- [ ] Side captions are column-centred on every line; credits stay separate and
      left in the image column; full/chart/diagram descriptions remain
      page-centred.
- [ ] Description and provenance share one centred caption at caption size; the
      credit is a separate left line; no 9.2 pt figure note survives (D5).
- [ ] Every definition is inline (`Term: definition`) in body type; no grey role
      label or isolated term line (D1). A glossary, if any, is one authored
      table.
- [ ] Every chapter and subsection prints its number: the chapter heading reads
      `Chapter 1: Title` (appendix `Appendix A: Title`), body headings print
      `1.1` (level 2), `1.1.1` (level 3), `1.1.1.1` (level 4) and `1.1.1.1.1`
      (level 5), and terminal branches print their section number with a letter
      (`1.1 a)` in section `1.1`, `1.1.1 a)` in a subsection); depth-5 contents
      and cross-references print the same number, no two sections share a
      reference, and no number ends with a period (D3).
- [ ] One selected cover composition (cover-1 … cover-7) renders; an absent
      selection is reported as `engine-fallback` (`cover-3`), never claimed as a
      user choice. An art-bearing composition with no artwork record shows a
      blank field and `artwork: absent`; nothing is invented. No folio, no
      colour, no stock image, no chapter index (D2).
- [ ] Each chapter heading is one `Chapter n: Title` line followed by at least
      one visible body blank line; every heading keeps that blank line before
      prose, a figure or a caption (D4, D6).
- [ ] Chapters with a visual carry one full-measure plate where the material
      supports it; a centred visual keeps the 430 pt figure width and a side
      group is not recorded as a plate; a chapter without a plate records a
      `no-plate` reason (D4).
- [ ] A two-column chapter, if authored, sets its heading and standfirst at the
      full measure and its body in two equal columns; no other chapter changes
      column count silently (A2).
- [ ] One illustration per final page.
- [ ] Labels fit their boxes; no clipped text, overlapping marks or unreadably
      small labels.
- [ ] Captions are attached to their figures; cross-references resolve.
- [ ] Charts are labelled synthetic where they are; diagrams illustrative where
      they are; reconstructions labelled as reconstructions.

## Readability judgement (D7)

Density is never a target and never a hard failure. Read the page, not the
number.

- [ ] The verify report's readability warnings are read with their pages,
      values and bands.
- [ ] Each warning has a recorded decision in the review notes file: either the
      page is deliberate reference matter, or it was fixed.
- [ ] Every warning id appears in the review notes; an unanswered warning fails
      the review check even though the density itself never fails the gate.
- [ ] For every chapter: can a reader follow the argument on the page? Is a long
      paragraph a wall or a deliberate unit? Is a table or plate doing work?
      Are the definitions usable inline? Is the density run deliberate?
- [ ] No page, word, figure or table quota was used to judge the book, and no
      filler was added to change a metric.

## Page inspection

- [ ] Every rendered page was viewed at a readable resolution, not only checked
      by text extraction.
- [ ] Contact sheet or per-page evidence exists and is recorded.
- [ ] Each page has a result (pass / attention / block) with a reason for
      anything not passing.
- [ ] Orphaned headings, split compositions, detached captions, cramped labels,
      accidental blank space and monotonous page rhythm were fixed or recorded.

## Build and verify

- [ ] `manuscript check` and `design check` pass (or the failures are understood
      and recorded).
- [ ] The build ran offline with the pinned toolchain.
- [ ] A second build exists for comparison.
- [ ] `verify` returns `gate: pass`, or each failing check is recorded as a
      finding rather than hidden.
- [ ] The review record is honest: agent inspection, not human sign-off.
- [ ] `uv run python -m pytest -q` passes (`uv run pytest` cannot spawn the
      console script in this environment).

## Catalogue regression (only when the catalogue is touched)

The catalogue is a regression fixture, not a required book shape. When a change
can affect it, confirm:

- [ ] Exact inventory: 16 chart figures / 15 families, 10 diagram presets,
      4 illustration families.
- [ ] Pie (`hole: 0`) and donut (`hole > 0`) are both present and counted as one
      family.
- [ ] The 29-row coverage table matches the PDF.
- [ ] Four illustrations appear once each, on four distinct pages; no page holds
      two; one `side-left`, one `side-right` and one `full` are demonstrated.
- [ ] The 30-figure geometry check passes within its existing tolerance.
