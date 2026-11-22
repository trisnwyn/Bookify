# Visual design and page inspection

The PDF is the product. A manuscript can validate, every glyph can exist, and the
book can still be poor: a split composition, an orphaned heading, a detached
caption, a cramped label, a monotonous page rhythm, a paragraph that says
nothing. This guide gives the visual judgement and the inspection that catches
those failures.

## House style (current engine)

- A4, single serif family (Spectral for Latin, Noto Serif CJK JP for Japanese,
  STIX Two Math for mathematics), black text on white, no colour decoration.
- Page margin 60 pt; body measure 475.28 pt; body 10.1 pt on a 15.3 pt total line
  pitch; lead 10.6/16.4; caption 8.2/11.2; table 8.6/11.6; note 9.2/13.6; small
  8.4/12; quote 10.2/15.4; credits 7.6 pt. The theme stores the Typst *extra*
  beyond the natural font height, because `par.leading` is not a total. Values
  live in `typst/theme.typ` and are not re-invented per book.
- Restrained hierarchy: level-1 titles at 25 pt / 30 pt pitch, level-2 at
  12.6 / 16.5 pt, level-3 at 10.3 / 14 pt, weight and spacing carrying the
  hierarchy more than size alone.
- Tables use hairline rules; figures use a single thin frame; nothing has a heavy
  drop shadow, gradient or ornamental panel.
- Do not rewrite the design system for a book. Choose within it: composition,
  figure selection, section rhythm, paragraph length, the moments where white
  space does the work.

## v2 defaults the engine applies (D1–D7)

These are generated defaults, not per-book switches. Do not hand-write cover,
opener, numbering or caption markup.

- **Cover (D2).** Seven accepted compositions (`cover-1` … `cover-7`), selected
  as data by `metadata.cover.composition`. There is no house default cover:
  absent a selection the engine renders `cover-3`, the typographic composition,
  and records `selection: engine-fallback`; it never presents that as the user's
  choice. `cover-3` has no illustration field. The other six reserve a field for
  an optional rights-checked `metadata.cover.artwork` (an illustration record
  id); with no artwork the field is blank and the report says `artwork: absent`.
  Never synthesize art, a burst, a stock image or a placeholder label. Every
  composition prints only supplied metadata, at 34/12.6/8.4 pt, monochrome, with
  no folio and no chapter index. A title that will not fit three lines fails the
  build with the `metadata.title` locator; it is never shrunk.
- **Numbering (D3).** A chapter heading prints `Chapter 1: Title` (appendix
  `Appendix A: Title`). Every body level carries its full path: `1.1` at level 2,
  `1.1.1` at level 3, `1.1.1.1` at level 4 and `1.1.1.1.1` at level 5. A terminal
  branch is a run-in body block that prints its own section number and a letter
  (`1.1 a)` in section `1.1`, `1.1.1 a)` in a subsection). Contents (depth 5)
  prints the same numbers and folios, and cross-references print exactly the
  heading's number (`§1`, `§1.1`, `§1.1.1`, `§A.1`). No number ends with a
  period, so `§1.1.` is section `1.1` followed by a full stop, never another
  section. Numbering is structural: never type a number into a title. Back
  matter is authored with `role: appendix`; a chapter after an appendix is
  refused.
- **Definitions (D1).** A definition is one body paragraph: bold term, colon,
  definition. There is no role label, no grey, no standalone term line. A
  glossary is a deliberate table the book collates with a caption, never a
  transform of every definition into a row.
- **Chapter headings (D4).** Each level-1 chapter is one h1 line, `Chapter n:
  Title`, followed by at least one visible body blank line before the standfirst,
  lead or first paragraph. The retired oversized numeral, opener rule and
  stacked title are not drawn. You supply the title and, where the material warrants one,
  the standfirst.
- **Plates and body compositions (D4).** A plate is one chart, diagram or full
  illustration at the full text measure (475.28 pt). A `centred` illustration
  keeps the 430 pt figure width; a side composition stays illustration-only in
  its 46 % column and may carry one prose companion or an ordered group of up to
  three (`companions`, 900 collapsed characters total). Each chapter with a
  visual should carry at least one plate where the material supports it. If it
  cannot, record a `no-plate` reason; the verify report warns and the review
  answers it. A chapter may be authored in two columns (`layout: {columns: 2}`);
  single column stays the default and no section switches silently. Never add a
  plate to fill space and never fabricate a visual.
- **Captions (D5).** For charts, diagrams and full illustrations, one centred
  caption at 8.2 pt carries the description *and* the provenance/source line
  (`Source: …`, `Synthetic data.`). Credits remain a separate left-aligned line
  at 7.6 pt. Table and equation captions keep their own treatment.
- **Heading rhythm (D6).** Body 15.30 pt pitch and the 20.70 pt paragraph gap are
  fixed. Level-2, level-3 and level-4 headings open explicit blank bands above
  the paragraph gap (32 pt and 25 pt before), so a heading never collides with
  the prose above it. Below *every* heading the engine reserves the face's
  descender ink, the next line's ascender overhang **and one whole body blank
  line** (15.30 pt), so a reader always sees white space; verify measures that
  band and fails anything below it. Do not add manual spacing. The level-1 title
  keeps its ≥ 32.7 pt deck gap.

## Typography and hierarchy

- One idea per paragraph; vary paragraph length but do not write walls.
- The paragraph gap is intentionally wider than the line pitch (about 5.4 pt
  beyond it). Do not add manual paragraph spacing on top; the preset owns it.
- Keep headings short and parallel. A heading that needs a full sentence usually
  belongs in the standfirst.
- Do not orphan a heading at the foot of a page. If it happens, revise the text
  flow or the section split rather than accepting it.
- Chapters and minor sections are different units. A level-1 chapter may start a
  fresh page; a level-2/3 section flows. Do not promote every source heading to a
  chapter, and do not force a page just because a heading exists. A full plate or
  a deliberate back-matter page may set `breakBefore: page`; that is a content
  decision, not a title-word heuristic.
- Keep a kicker with its heading, a heading with its first meaningful block, and
  a plate (heading, note, image, caption, credit) together. The engine does this;
  do not work around it with hand-inserted breaks.
- Use the lead paragraph for the chapter's opening claim, not a generic
  introduction.
- Let lists be lists: if the content is sequential, a numbered list; if it is a
  set, an unordered list. Avoid list-shaped paragraphs and paragraph-shaped
  lists.
- Check the widows and short last lines that look accidental. Typst adds spacing
  after `。`; that is a known engine behaviour, not a reason to hand-tune every
  page.

## White space and page rhythm

- White space is structure, not leftover space. A page with a single well-placed
  figure and a generous margin can be stronger than a full page.
- Vary the composition across the book: a full-measure page, a side composition,
  a table, a short chapter opener. Repetition of the same page shape for many
  pages reads as a template.
- Avoid an accidental near-empty page at a chapter boundary; either make the
  break deliberate or reflow the text.
- Do not fill space with a figure, a pull quote or a box. Every added element
  must do work.

## Compositions

Composition is authored data, not a runtime choice:

- `full` is the default full-measure figure.
- `centred` keeps the 430 pt figure width (`measure.figure_width`) and is
  page-centred; its caption is centred on the page and its credit stays left.
- `side-left` places the image column on the left; `side-right` on the right.
- A side preset requires the **immediately following** prose blocks in the same
  section: the legacy single `companion`, or an ordered `companions` group of up
  to three blocks whose total is at most 900 collapsed characters (each block
  also at most 520). Each block renders once with its own prose preset.
- `full` and `centred` forbid companions. Charts and diagrams carry no
  composition: they are plates at the text measure.
- There is no auto-pairing, alternation or model choice. Changing a composition
  is a manuscript edit.
- The composition is **unbreakable**: image, caption, credit and companion group
  share one page. If the unit does not fit, the whole unit defers; it never
  splits and no companion is silently dropped.
- Side captions are centred line by line in the image column; credits stay
  separate and left in that column. Charts, diagrams, centred and full-width
  illustrations are page-centred, and their descriptions are centred line by
  line to their measure.
- One illustration per final page. The build enforces and reports deferrals; do
  not work around it by shrinking an image to a thumbnail.
- The side grid is fixed (46 % image column, 16 pt gutter). There is no text wrap
  around an image and no runtime layout choice.
- A chapter may be authored in two equal columns (`layout: {columns: 2}`). The
  chapter heading and standfirst stay at the full measure and the body — the
  chapter's own blocks **and every descendant section** — runs in two 229.64 pt
  columns with the 16 pt gutter, continuing across pages. A chart, diagram or
  illustration inside the flow takes the column measure and its caption centres
  in that column. A side composition is refused inside a two-column chapter and
  in any descendant section, because a 46 % image column cannot sit inside a
  229.64 pt column. Single
  column is the default; a section is never switched silently.
- Long tables stay breakable: the header repeats after a split and the caption
  sits at the end with the final rows. Do not make every table unbreakable.
- A figure or plate unit that cannot fit the text block fails the build with its
  block id; it is never clipped or silently shrunk.

## Choosing a visual

| Visual | Use it when | Do not use it when |
| --- | --- | --- |
| Chart | A relationship, distribution, trend or comparison is the point and the source supplies or supports the values. | The numbers are decorative, unreadable or invented. |
| Diagram | Structure, sequence, hierarchy, a cycle or a decision is easier to see than to read. | A short paragraph is clearer; or the diagram merely repeats the text. |
| Illustration | Evidence, recognition, context, a place, an object or a documented event. | It is filler, a generic mood image, or its rights are unknown. |
| Table | Exact values need comparison in rows and columns. | The content is prose or two values. |
| Equation | The relationship itself is the content. | A sentence would be clearer. |

There is **no quota**. A book with zero illustrations is valid when the material
does not need one. Never add a figure to fill a page, and never evaluate a book
by counting figures. Charts must be labelled synthetic where they are synthetic;
diagrams illustrative where they are illustrative; reconstructions named as such.
Every illustration carries its rights record and credit. See
`source-and-provenance.md` for rights rules.

## Labels, captions and credits

- Fit labels to their boxes: no clipping, overlap, sub-readable type or labels
  that fall outside the frame. Shorten, wrap deliberately or choose a different
  chart form.
- A caption belongs to its figure and stays with it. The provenance/source line
  shares the centred caption; a credit is separate, left-aligned, and is not
  merged into the description.
- Alternative text describes the image without interpreting it.
- Cross-references must resolve: “see Figure 3” must point at a real figure.
- Do not let a caption describe a different figure after a late edit.

## Inspect every rendered page

Visual acceptance is not a figure count, a page count or a catalogue inventory.

1. Render every page at a readable resolution (for example
   `pdftoppm -png -r 110`).
2. Build a contact sheet for the whole book (for example
   `magick montage page-*.png -tile 4x contact.png`).
3. View every page, not only the contact sheet. Read the page as a reader.
4. Record a per-page result: pass, attention (with reason) or block. A blocking
   defect blocks delivery; an attention result carries a decision.
5. Check: material faithfulness, readability, design coherence, intentional
   hierarchy, white space, varied composition, typography, fitted labels,
   caption/credit integrity, one illustration per page, rights and
   cross-references.
6. Fix what you found, rebuild, and look again. Re-run the page inspection after
   the fix; a stale contact sheet is not evidence.

Record what you actually saw, with the page and the evidence path. This is agent
visual inspection, not human PDF sign-off, and it is not a claim of objective
aesthetic proof.

## Common failures to look for

- A side composition that split across pages, or lost its companion.
- A heading alone at a page bottom, or a chapter opening with no lead.
- A caption detached from its figure, or a credit inside the caption.
- A chart with unreadable axis labels or overlapping categories.
- A diagram whose labels overflow their nodes.
- A page with two illustrations, or an illustration that is only decorative.
- A near-empty page caused by a composition that did not fit.
- Many consecutive pages with the same shape.
- A paragraph that restates the heading without teaching anything.
- A grey definition label, an unnumbered heading, or a cover that is just a
  centred title.
- A provenance note left at note size under a figure instead of inside the
  caption.
- A heading that crowds the prose above it, or two headings with nothing
  between them.

## Readability judgement (D7)

Density is measured, reported and reviewed; it is never a target and never a
hard failure.

- Read the page rather than the number. A dense reference page can be correct; a
  sparse plate page can be correct. No minimum page, word, figure or table count
  exists.
- The verify report names each metric, its measured value, its band and its
  pages: words per page, tables per page, paragraph length, and runs of dense
  pages. Cover, contents, chapter-opener, plate and appendix pages are exempt
  from the thin-page warning, with the reason listed.
- Every warning id must be answered in the review notes file passed to verify.
  Answer with a reason ("deliberate reference spread", "checked; the list page
  needs the air") or fix the page. An unanswered warning fails the review check;
  the density itself never fails the gate.
- Per chapter, ask: can the reader follow the argument? Is a long paragraph a
  wall or a deliberate unit? Is a table or plate doing work? Are definitions
  usable inline? Is the dense run deliberate reference material or an accident?
- Never add filler to move a metric. Change the writing, the structure or the
  plate, and only when reading the page shows a real problem.
