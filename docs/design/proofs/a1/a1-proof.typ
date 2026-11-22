// A1 layout proof — disposable, four compositions, one page each.
//
// This file is NOT a product template. It imports the current Bookify theme
// read-only to render the current A4 grid, type size, leading and measure, and
// composes four A1 body-page arrangements from neutral lorem prose and simple
// vector placeholder boxes. No font face, size, margin or measure is taken
// from the reference; all of those come from /typst/theme.typ.
//
// Build (from the repository root, offline, vendored Typst):
//   tools/typst/typst compile \
//     --ignore-system-fonts --ignore-embedded-fonts \
//     --font-path assets/fonts \
//     --package-path vendor/typst --package-cache-path .cache/empty-pkg \
//     --creation-timestamp 1750000000 --root . \
//     build/design/a1/a1-proof.typ build/design/a1/a1-proof.pdf

#import "/typst/theme.typ": tokens, book_base

#set page(numbering: none)
#show: book_base

// Fixed A1 proof rule: every heading must clear its following content by at
// least one clearly visible body blank line (the body line pitch is 15.30 pt).
// The proof-local block below is 19.93 pt = current paragraph gap (14.03) +
// after_block (5.4) + heading_clearance (0.5); rendered ink clearance is
// measured in the README, not inferred from the token.
#let heading-content-gap = tokens.space.between_paragraphs + tokens.space.after_block + tokens.space.heading_clearance

// Keep the first line ascender ink inside the 60 pt text block.
#v(tokens.space.after_block)

// ---------------------------------------------------------------- samples ---
// Harmless lorem prose only. No factual claims about any source or subject.
#let p-a = [
  Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
  tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
  quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
  consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
  cillum dolore eu fugiat nulla pariatur.
]

#let p-b = [
  Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia
  deserunt mollit anim id est laborum. Sed ut perspiciatis unde omnis iste
  natus error sit voluptatem accusantium doloremque laudantium, totam rem
  aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto
  beatae vitae dicta sunt explicabo.
]

#let p-c = [
  Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit,
  sed quia consequuntur magni dolores eos qui ratione voluptatem sequi
  nesciunt. Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet,
  consectetur, adipisci velit, sed quia non numquam eius modi tempora
  incidunt ut labore et dolore magnam aliquam quaerat voluptatem.
]

#let p-d = [
  Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis
  suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur. Quis autem
  vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil
  molestiae consequatur, vel illum qui dolorem eum fugiat quo voluptas nulla
  pariatur.
]

// --------------------------------------------------------------- furniture ---
#let proof-label(index) = block(
  below: tokens.space.after_block,
  width: 100%,
  grid(
    columns: (1fr, auto),
    column-gutter: tokens.space.side_gutter,
    {
      set text(size: tokens.type.small, fill: tokens.ink.grey_1, weight: 600)
      set par(leading: tokens.leading_extra.small, justify: false)
      [A1 LAYOUT PROOF · COMPOSITION #index OF 4]
    },
    align(right, {
      set text(size: tokens.type.small, fill: tokens.ink.grey_2)
      set par(leading: tokens.leading_extra.small, justify: false)
      [A4 · current Bookify tokens · proof only]
    }),
  ),
)

// Heading blocks use the current theme type/leading tokens and a fixed below
// gap of 19.93 pt. They are deliberately local proof blocks, not an
// implementation of the product's heading counter.
#let proof-heading(body) = block(
  above: tokens.space.before_heading + tokens.space.after_block,
  below: heading-content-gap,
  {
    set text(size: tokens.type.h1, weight: 500)
    set par(leading: tokens.leading_extra.h1, justify: false)
    body
  },
)
#let section-heading(body) = block(
  above: tokens.space.before_h2,
  below: heading-content-gap,
  {
    set text(size: tokens.type.h2, weight: 600)
    set par(leading: tokens.leading_extra.h2, justify: false)
    body
  },
)
#let subsection-heading(body) = block(
  above: tokens.space.before_h3,
  below: heading-content-gap,
  {
    set text(size: tokens.type.h3, weight: 600)
    set par(leading: tokens.leading_extra.h3, justify: false)
    body
  },
)

#let para(body) = block(
  below: tokens.space.between_paragraphs,
  {
    set par(leading: tokens.leading_extra.body)
    body
  },
)

// A simple vector placeholder: one stroked pale box plus a short label.
#let placeholder-box(width, height, label) = block(
  width: width,
  height: height,
  fill: tokens.ink.pale,
  stroke: tokens.rule.figure_stroke,
  {
    align(center + horizon, {
      set text(size: tokens.type.small, fill: tokens.ink.grey_1, weight: 600)
      set par(leading: tokens.leading_extra.small, justify: false)
      align(center, label)
    })
  },
)

#let caption(note) = block(
  above: tokens.space.after_caption,
  width: 100%,
  align(tokens.figure.caption_align, {
    set text(size: tokens.type.caption, fill: tokens.ink.grey_1, style: "italic")
    set par(leading: tokens.leading_extra.caption, justify: false)
    note
  }),
)

// Centred visual at the requested width, with an optional caption.
#let centred-visual(width, height, label, note: none) = block(
  above: tokens.space.after_block,
  below: tokens.space.after_figure,
  breakable: false,
  width: 100%,
  {
    align(center, placeholder-box(width, height, label))
    if note != none {
      caption(note)
    }
  },
)

// Side-column visual; it fills its grid cell and carries its own caption.
#let side-visual(height, label, note: none) = block(
  width: 100%,
  breakable: false,
  {
    placeholder-box(100%, height, label)
    if note != none {
      caption(note)
    }
  },
)

// ----------------------------------------------------------- composition 1 ---
// Heading, full-width prose, a centred visual at the current figure_width,
// then full-width continuation. The visual is optional in the reference; here
// it is present so the composition can be inspected.
#proof-label(1)
#proof-heading[Chapter 1: Full-width prose with a centred visual]
#section-heading[1. Full-width opening]
#para(p-a)
#para(p-b)
#subsection-heading[1.1 Centred visual]
#centred-visual(
  tokens.measure.figure_width,
  150pt,
  [PLACEHOLDER · CENTRED VISUAL],
  note: [Placeholder vector box at figure_width: 430 pt wide. No asset; no factual claim.],
)
#subsection-heading[1.1.1 Full-width continuation]
#para(p-c)
#para(p-d)

#pagebreak()
#v(tokens.space.after_block)

// ----------------------------------------------------------- composition 2 ---
// The same sequence with the visual at the full text measure (plate token).
#proof-label(2)
#proof-heading[Chapter 2: The same sequence with a full-measure visual]
#section-heading[2. Full-width opening]
#para(p-b)
#para(p-c)
#subsection-heading[2.1 Full-measure visual]
#centred-visual(
  tokens.measure.plate,
  180pt,
  [PLACEHOLDER · FULL-MEASURE VISUAL],
  note: [Placeholder vector box at plate: 475.28 pt wide, the full text measure.],
)
#subsection-heading[2.1 a) Full-width continuation]
#para(p-a)
#para(p-d)

#pagebreak()
#v(tokens.space.after_block)

// ----------------------------------------------------------- composition 3 ---
// Full-width opening under the heading, then prose in the left region beside
// an image in the right region. Side column = 0.46 × measure.
#proof-label(3)
#proof-heading[Chapter 3: Full-width opening, then prose beside a right-hand visual]
#section-heading[3. Full-width opening]
#para(p-a)
#subsection-heading[3.1 Prose in the left region beside the right-hand visual]
#grid(
  columns: (1fr, tokens.measure.body * tokens.measure.side_fraction),
  column-gutter: tokens.space.side_gutter,
  align(top, {
    para(p-b)
    para(p-c)
    para(p-d)
  }),
  align(top, side-visual(
    240pt,
    [PLACEHOLDER · RIGHT VISUAL],
    note: [Side column 218.63 pt (0.46 × 475.28 pt). Placeholder only.],
  )),
)
#pagebreak()
#v(tokens.space.after_block)

// ----------------------------------------------------------- composition 4 ---
// Image left, prose right, then a full-width paragraph below both columns.
#proof-label(4)
#proof-heading[Chapter 4: Visual left, prose right, full-width paragraph below]
#section-heading[4. Visual and prose]
#subsection-heading[4.1 Prose in the right region beside the left-hand visual]
#grid(
  columns: (tokens.measure.body * tokens.measure.side_fraction, 1fr),
  column-gutter: tokens.space.side_gutter,
  align(top, side-visual(
    230pt,
    [PLACEHOLDER · LEFT VISUAL],
    note: [Side column 218.63 pt (0.46 × 475.28 pt). Placeholder only.],
  )),
  align(top, {
    para(p-c)
    para(p-d)
    para(p-b)
  }),
)
#section-heading[4.2 Full-width paragraph below]
#para(p-a)
#para(p-b)
