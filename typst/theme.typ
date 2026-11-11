// Bookify design tokens. Visual values live here and nowhere else.
// Font selection is explicit per script; a missing glyph is a build error, not a fallback.

#let tokens = (
  type: (
    body: 10.1pt,
    lead: 10.6pt,
    h1: 25pt,
    h2: 12.6pt,
    h3: 10.3pt,
    caption: 8.2pt,
    small: 8.4pt,
    credit: 7.6pt,
    table: 8.6pt,
    table_head: 8.1pt,
  ),
  leading: (
    body: 1.515em,
    lead: 1.55em,
    heading: 1.2em,
  ),
  space: (
    page_margin: 60pt,
    before_heading: 17pt,
    before_role: 18pt,
    after_heading: 4.5pt,
    after_block: 5.4pt,
    after_lead: 12pt,
    after_figure: 14pt,
    after_caption: 8pt,
    side_gutter: 16pt,
  ),
  measure: (
    body: 475.28pt,
    figure_width: 430pt,
    side_fraction: 0.46,
  ),
  rule: (
    table_top: 0.6pt,
    table_head: 0.4pt,
    table_bottom: 0.6pt,
    figure_stroke: 0.55pt,
  ),
  ink: (
    text: rgb("#000000"),
    grey_1: rgb("#4d4d4d"),
    grey_2: rgb("#7a7a7a"),
    grey_3: rgb("#a8a8a8"),
    pale: rgb("#e6e6e6"),
  ),
  accent: (
    ink: rgb("#2f3e5c"),
    tint_1: rgb("#d6dbe2"),
    tint_2: rgb("#a9b2c2"),
    tint_3: rgb("#7c8aa2"),
  ),
  figure: (
    caption_align: center,
  ),
  diagram: (
    label: 8pt,
    label_weight: 600,
    sub: 6.6pt,
    feedback: 6.4pt,
    group_label: 6.4pt,
    stroke: 0.55pt,
    dash_stroke: 0.45pt,
    group_rule: 0.4pt,
    radius: 2pt,
    label_floor: 5.5pt,
    label_step: 0.5pt,
    label_pad: 3pt,
    edge_ink: rgb("#6e6e6e"),
    group_ink: rgb("#828282"),
  ),
  role: (
    definition: rgb("#2f3e5c"),
    example: rgb("#7c8aa2"),
    case: rgb("#4d4d4d"),
    assessment: rgb("#2f3e5c"),
  ),
)

#let fonts = (
  latin: "Spectral",
  japanese: "Noto Serif CJK JP",
  maths: "STIX Two Math",
)

// Base rules: one serif family, local faces, explicit per-script selection.
#let book_base(body) = {
  set page(paper: "a4", margin: tokens.space.page_margin)
  set text(font: (fonts.latin, fonts.japanese), size: tokens.type.body, lang: "en", region: "GB")
  set par(justify: true, leading: tokens.leading.body)
  show math.equation: set text(font: fonts.maths)
  show heading: set text(font: fonts.latin, weight: 600)
  show heading.where(level: 1): set text(size: tokens.type.h1, weight: 500)
  show heading.where(level: 2): set text(size: tokens.type.h2, weight: 600)
  show heading.where(level: 3): set text(size: tokens.type.h3, weight: 600)
  set heading(numbering: none)
  body
}
