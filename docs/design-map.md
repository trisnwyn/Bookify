# Bookify design map

Progressive handover map for Bookify's visual design. Visual direction is owned by
the user. This file records what has been decided, what is still open, and in what
order work proceeds. It is the single index for design status; per-item detail lives
in `docs/design/`.

## Purpose and working agreement

- **The user designs.** Every visual choice — type, spacing, rules, colour, page
  furniture, figure styling — is the user's decision.
- **The AI encodes exactly.** No invented visuals, no "improvements", no
  taste-driven variants. If a decision is missing, stop and ask.
- **One component at a time.** Work moves through the list below in order. A
  component is finished before the next one starts.
- **Proof page per component.** Each component gets a rendered page (or page pair)
  showing it in isolation and in its real context, so the user judges a real
  artifact, not a description.
- **Approval before rebuilding books.** No full-book rebuild on design grounds
  until the user approves the proofs for the affected templates.
- **No design changes without user sign-off.** The AI may fix correctness
  (build, verification, text extraction, overlap, accessibility of the build), and
  must not change appearance while doing so.

## Status legend

| Status | Meaning |
| --- | --- |
| `todo` | Not started; no decision recorded. |
| `brainstorm` | Open questions being asked; no answer yet. |
| `specified` | The user has decided; written as a spec table or annotated page. |
| `encoded+proof` | Implemented exactly to spec; proof page rendered, awaiting judgement. |
| `approved` | The user has signed off the proof for this component. |
| `shipped` | Approved and in the default book build. |
| `blocked` | Cannot proceed; reason recorded on the item. |

Only the user changes a status to `approved` or `shipped`.

## Phases

Ordered. Foundations first: page templates and text blocks depend on them.
Item text is one line by design; detail belongs in `docs/design/`.

### A. Foundations

| ID | Item | Status | Decisions needed | Handover |
| --- | --- | --- | --- | --- |
| A1 | Textbook layout: body page grid, measure, margins, rhythm | `brainstorm` | Measure and characters per line; column count; indent vs space; running head; folio; section starts | Annotated A4 page + filled log in `docs/design/textbook-layout.md` |
| A2 | Type system: families, cuts, sizes, leading per role | `todo` | Which faces for which roles; size/leading table; fallback and script policy | Spec table + annotated page |
| A3 | Spacing scale | `todo` | The step scale; what each step is for; which gaps are tied to leading | Spec table |
| A4 | Ink and greys | `todo` | Black/grey ramp; whether an accent exists at all; contrast floor | Spec table with swatches |
| A5 | Rules and strokes | `todo` | Hairline weights; where rules appear; table and figure stroke consistency | Spec table |

> **A1 proof note (disposable, not approved):** `build/design/a1/` renders the four reference compositions at the current tokens. It applies the confirmed hierarchy (`Chapter 1: Title`, `1. …`, `1.1 …`, `1.1 a)`, `1.1.1 …`) and the fixed rule that every heading clears following content by at least one visible body blank line. Measured minimum: 15.84 pt against the 15.30 pt body line pitch. A1 remains `brainstorm`; this is not a decision or approval.

> **Disposable proof record (no status change).** `build/design/a2/` renders a
> two-page A4 A2 composition with the live baseline tokens and the user-supplied
> numerical heading path `Chapter 2 → 2. → 2.1 → 2.1 a–c → 2.1.1 → 2.1.1.1`. It
> applies the fixed rule that every heading is followed by at least one visibly
> blank body line (15.30 pt); the measured minimum in the render is 15.60 pt. It
> changes no product template and does not change any status above.

### B. Page templates

| ID | Item | Status | Decisions needed | Handover |
| --- | --- | --- | --- | --- |
| B1 | Cover | `todo` | Title block; subtitle/meta; any rule or mark; what is omitted | Annotated A4 page |
| B2 | Front matter | `todo` | Which pages exist; order; numbering before the body | Annotated page set + spec table |
| B3 | Contents | `todo` | Depth, numbering, leaders/dot leaders, multi-page behaviour | Annotated page + spec table |
| B4 | Chapter opener | `todo` | Numeral/title placement; deck; opening rule; whitespace budget | Annotated A4 page |
| B5 | Body page | `todo` | Text block position; running head content and position; folio | Annotated A4 page |
| B6 | Section within page | `todo` | Heading levels mid-page; clearance; no orphan headings | Annotated page + spec table |
| B7 | Back matter / appendix | `todo` | Appendix numbering; page numbering; contents treatment | Annotated page set |
| B8 | Intentional blank / deep-break page | `todo` | When a blank is allowed; whether it carries anything | Annotated page + spec table |

### C. Text blocks

| ID | Item | Status | Decisions needed | Handover |
| --- | --- | --- | --- | --- |
| C1 | Paragraph | `todo` | Indent or gap; first-line treatment after headings; widow/orphan policy | Annotated page + spec table |
| C2 | Lead / standfirst | `todo` | Size and leading; measure; relationship to the heading | Annotated page |
| C3 | Inline definition | `todo` | Inline form; term emphasis; whether a label exists | Annotated page + spec table |
| C4 | Example | `todo` | Distinction from body without a label or panel; indent; rule or none | Annotated page |
| C5 | Case | `todo` | Same as C4 plus how a case differs from an example | Annotated page |
| C6 | Assessment / check | `todo` | How a check reads as a check; placement; answer handling | Annotated page |
| C7 | Bullet list | `todo` | Marker; indent; spacing above/below; nested levels | Spec table + annotated page |
| C8 | Numbered list | `todo` | Numeral style; hanging indent; restart behaviour | Spec table + annotated page |
| C9 | Quote + attribution | `todo` | Indent or size change; quote marks; attribution form and alignment | Annotated page |
| C10 | Table: split header, caption, footnote | `todo` | Header repeat; rule weights; caption and footnote placement; column alignment | Annotated page + spec table |
| C11 | Equation | `todo` | Numbering; centring vs measure; display size; inline form | Annotated page |
| C12 | Note / aside | `todo` | Whether it is set apart at all; size; rule; placement in flow | Annotated page |
| C13 | Uncertainty / unresolved | `todo` | How unresolved content is marked for the reader; wording; visual weight | Annotated page + spec table |
| C14 | Key-terms table | `todo` | Table form vs list; column split; ordering | Annotated page |

### D. Figures

| ID | Item | Status | Decisions needed | Handover |
| --- | --- | --- | --- | --- |
| D1 | Chart language | `todo` | Palette in monochrome; axis and label style; tick and grid rules; annotation | SVG reference set + spec table |
| D2 | Diagram language | `todo` | Node and edge style; label sizes; hierarchy; arrowheads | SVG reference set + spec table |
| D3 | Illustration framing: full and side | `todo` | Full-measure vs side placement; caption and credit position in each | Annotated page pair |
| D4 | Plate / motif art | `todo` | Whether recurring ornament exists; where it may appear; how it is drawn | SVG + annotated page |

### E. Navigation

| ID | Item | Status | Decisions needed | Handover |
| --- | --- | --- | --- | --- |
| E1 | Numbering style | `todo` | Chapter, section, figure, table, example numbering schemes | Spec table |
| E2 | Cross-reference form | `todo` | In-text reference wording and abbreviation; link or plain print | Spec table with examples |
| E3 | Running-head content | `todo` | What appears on verso/recto; whether it changes within a chapter | Spec table + annotated page |
| E4 | Contents depth | `todo` | Levels listed; what is omitted; appendix and back-matter entries | Annotated contents page |
| E5 | Index / glossary conventions | `todo` | Whether they exist; sort order; locator style; term selection | Spec table + annotated page |

### F. Variant proofs

Full-page proofs that combine approved components. Each is judged as a whole page,
not as a component.

| ID | Item | Status | Decisions needed | Handover |
| --- | --- | --- | --- | --- |
| F1 | Chapter first page | `todo` | Combination check: opener + lead + first paragraphs + any figure | Annotated A4 page |
| F2 | Continuation page | `todo` | Combination check: running head + body + folio | Annotated A4 page |
| F3 | Full-width figure page | `todo` | Figure, caption, credit, surrounding text | Annotated A4 page |
| F4 | Side-illustration page | `todo` | Side placement, measure of the narrowed text, caption behaviour | Annotated A4 page |
| F5 | Dense table page | `todo` | Split header, footnotes, caption, page break inside a table | Annotated A4 page |
| F6 | Sparse page | `todo` | Short section, deliberate whitespace, no filler | Annotated A4 page |
| F7 | Unresolved-warning page | `todo` | How the warning reads on a real page without breaking the design | Annotated A4 page |
| F8 | Appendix page | `todo` | Appendix numbering and typography against body pages | Annotated A4 page |
| F9 | Multi-page contents | `todo` | Continuation of contents across pages | Annotated page pair |

## Hard constraints

Every design must satisfy all of these. They are correctness requirements, not style
preferences, and the AI enforces them during encoding.

1. **A4.** Trim is 210 × 297 mm (595.28 × 841.89 pt). No other trim.
2. **Real text.** Body text must remain extractable as text; no outline or image body
   pages. Verification reads the PDF text layer.
3. **Captions centred to their measure; credits separate, left.** A credit is its own
   line, left-aligned to the same measure, never merged into the caption.
4. **One illustration per final page.** No page carries two illustrations.
5. **Figure, caption and credit stay grouped.** They do not split across a page break.
6. **Minimum diagram label 5.5 pt.** No diagram text below this at final size.
7. **Latin-first.** Latin script sets the design; other scripts must fit without
   changing Latin geometry.
8. **Monochrome-safe.** The book reads correctly printed in greyscale; colour is
   never the only carrier of meaning.
9. **No invented template content.** Templates render only what the manuscript
   provides. No lorem, no placeholder headings, no decorative filler text.
10. **Heading clearance prevents overlap.** A heading's descender ink and the next
    line's ascenders never collide, at any heading level.
11. **Readable body rhythm.** Body leading and paragraph spacing must stay readable
    at the chosen measure; the measured rhythm checks must continue to pass.

## Current state

- The visual redesign of the catalogue was judged **worse** by the user. That
  direction is abandoned.
- Visual design is **frozen** pending the user's decisions. No new visual direction
  is proposed by the AI in the meantime.
- Only correctness fixes apply: build reliability, verification, text extraction,
  overlap prevention, and equal-or-better behaviour against the hard constraints.
- Nothing is `approved` or `shipped`. A1 is the current focus and is in
  `brainstorm`; every other item is `todo`.
- Existing rendered output is a baseline to measure against, not an approved design.
