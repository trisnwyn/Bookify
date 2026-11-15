# A1 — Textbook layout (working document)

**Status:** `brainstorm` · **Owner:** user · **Encoder:** AI
**Latest disposable proof:** `build/design/a1/` (not approved). It renders the four reference compositions at the current A4/type/measure tokens, applies the confirmed numerical hierarchy (`Chapter 1: Title` → `1. …` → `1.1 …` → `1.1 a)` / `1.1.1 …`), and enforces the fixed rule that every heading clears following content by at least one visible body blank line. Measured minimum: 15.84 pt against the 15.30 pt body line pitch. A1's layout questions remain open; this is not a decision or approval.
**Scope of this document:** the body page only. Everything below is open until the
user records a decision. Nothing here is a proposal; the baseline is what the current
build measures, not what the design should be.

## Scope

A1 covers the body page at the layout level:

- page grid: margins, text block, measure
- body type size and leading as they set the line rhythm
- paragraph spacing and first-line indent
- placement of headings within the text flow (levels and clearance, not their type)
- running heads and folios at the layout level (whether and where, not their content)

**Out of scope (other items):** type families and cuts (A2), the spacing scale as a
system (A3), ink and greys (A4), rule weights (A5), running-head *content* and
numbering (E1, E3), page templates (B).

## Current baseline (as measured)

These are the values the current build produces, read from the theme and the rendered
pages. They are the starting point for comparison, **not** an approved design.

| Property | Measured value | Note |
| --- | --- | --- |
| Trim | A4, 595.28 × 841.89 pt | 210 × 297 mm |
| Margins | 60 pt on all sides | symmetric |
| Text measure | 475.28 pt (6.60 in) | 595.28 − 2 × 60 |
| Body type | 10.1 pt | |
| Body leading | 15.30 pt total pitch | ~1.51 × body size |
| Paragraph gap | 20.70 pt | 15.30 leading + 5.4 pt extra |
| h1 pitch | 30.00 pt | total line pitch; type size 25 pt |
| h2 pitch | 16.50 pt | total line pitch; type size 12.6 pt |
| h3 pitch | 14.00 pt | total line pitch; type size 10.3 pt |
| h2 separation above | 32 pt | preceding block to heading |
| h3 separation above | 25 pt | preceding block to heading |

Measured rhythm facts from the verification harness: body pitch 15.30 pt and
paragraph gap 20.70 pt are asserted on rendered pages, and h2/h3 separation is checked
as a baseline delta plus a white band, not as a single number.

## Disposable A2 composition proof (fixed rule recorded; Q2 open)

`build/design/a2/` holds a two-page A4 proof of two flowing text columns with an
optional figure embedded in the right column and continuation on page 2. It uses the
baseline values above unchanged and the user-supplied numerical heading path
`Chapter 2 → 2. → 2.1 → 2.1 a–c → 2.1.1 → 2.1.1.1`.

Fixed heading-clearance rule recorded by the proof: every heading (chapter, section,
subsection) is followed by at least one visibly blank body line. The proof uses
15.30 pt (one body line pitch) as the reserved white band; the rendered 300 dpi
measurement is 15.60 pt minimum. It is evidence only: Q2 (column count) remains open,
and no product template, theme, or numbering code is changed.

## Brainstorm questions

All open. Answer in the decisions log below, or mark up a page.

| ID | Question | Why it matters | User decision |
| --- | --- | --- | --- |
| Q1 | Measure and characters per line: how wide is the text block, and how many characters should a line hold? | Sets reading comfort and how much content fits per page; current measure is 475.28 pt. | *open* |
| Q2 | Column count: one column throughout, or two anywhere in the body? | Changes the grid, figure widths, and every text block's measure. | *open* |
| Q3 | Paragraph separation: first-line indent, space between paragraphs, or both? How large? | Determines whether the 20.70 pt gap is kept, reduced, or replaced. | *open* |
| Q4 | Running head: present at all? If present, which pages and which side? | Affects the top margin, the text block height, and whether pages look book-like. | *open* |
| Q5 | Folio: where does the page number sit — foot, head, outer margin, centred? | Interacts with Q4 and with the bottom margin. | *open* |
| Q6 | Section start behaviour: does every section start a new page, or do sections run on? | Sets page count, whitespace, and how B6 must behave. | *open* |
| Q7 | Keep or change the measured rhythm? Is 10.1/15.3 with a 20.70 pt gap confirmed as the baseline to build on? | The safest interpretation of the current build; still the user's call. | *open* |

## Decisions log

One row per decision. Leave blank until the user decides. A decision is only
effective when it names the value it replaces (or says "keep").

| ID | Date | Decision | Replaces / evidence | Status |
| --- | --- | --- | --- | --- |
| Q1 | | | | `open` |
| Q2 | | | | `open` |
| Q3 | | | | `open` |
| Q4 | | | | `open` |
| Q5 | | | | `open` |
| Q6 | | | | `open` |
| Q7 | | | | `open` |

Accepted handover forms for an entry: an annotated A4 page (marks plus a short note)
or a filled spec table row. A sketch of a grid drawn to scale is also usable if it
states the measurements.

## Annotated pages

Drop annotated pages and drawn grids here:

```
docs/design/a1/
  page-annotated-01.pdf     # marked-up A4 page
  grid-notes.md             # measurements read off the marks
  grid.svg                  # optional to-scale grid
```

Naming: `page-annotated-NN.pdf`, numbered in the order the user judges them. Annotate
on top of a real rendered page, not a blank sheet, so the mark sits against real text.
A mark must say what it changes: a measurement, or "keep" / "remove".

## Open

- No decision has been recorded for A1.
- No annotated page has been supplied.
- Until Q1–Q7 are answered, layout work stays at the measured baseline and the AI
  makes no visual change.
