// Bookify design tokens. Visual values live here and nowhere else.
// Font selection is explicit per script; a missing glyph is a build error, not a fallback.
//
// Typst `par.leading` is the EXTRA space beyond the font's natural line height,
// not a total line pitch. The pinned faces measure 0.660 em (Spectral Latin and
// Vietnamese) and 0.729 em (Noto Serif CJK JP) at Typst 0.15.1. `leading_extra.*`
// is therefore `intended_total - 0.660em * type_size`; never pass a total here.

// Font ink metrics of the pinned Spectral faces (hhea, Typst 0.15.1). Typst
// ends a layout line at the baseline, so a line box is 0.660 em above it while
// the glyphs themselves reach 0.750 em above (plain ascenders) and 0.240 em
// below (p, g, y, ç, ý; the deepest mark, `|`, is 0.250 em). Block spacing is
// measured between layout line boxes only; a heading therefore has to reserve
// its own descender ink and the following line's ascender overhang, or the next
// line strikes its descenders (F1 specimen page 4). A stacked accent above a
// capital is taller still (up to 1.057 em); that case is caught by the rendered
// rhythm check rather than reserved here, because reserving it would move the
// level-2/3 spacing.
#let ink_metrics = (
  line_box_em: 0.660,
  ascent_em: 0.750,
  descent_em: 0.240,
)

#let leading_extra = (
  body: 8.63pt,    // 0.660*10.1 + 8.63 = 15.30 total
  lead: 9.40pt,    // 0.660*10.6 + 9.40 = 16.40 total
  h1: 13.5pt,      // 0.660*25.0 + 13.5 = 30.00 total
  h2: 8.18pt,      // 0.660*12.6 + 8.18 = 16.50 total
  h3: 7.20pt,      // 0.660*10.3 + 7.20 = 14.00 total
  caption: 5.79pt, // 0.660*8.2 + 5.79  = 11.20 total
  small: 6.46pt,   // 0.660*8.4 + 6.46  = 12.00 total
  table: 5.92pt,   // 0.660*8.6 + 5.92  = 11.60 total
  note: 7.53pt,    // 0.660*9.2 + 7.53  = 13.60 total
  quote: 8.67pt,   // 0.660*10.2 + 8.67 = 15.40 total
  // v2: total pitch minus the measured natural line height (0.660 em).
  cover_title: 18.56pt,    // 0.660*34.0 + 18.56 = 41.00 total
  cover_index: 5.924pt,    // 0.660*8.6 + 5.924  = 11.60 total
  opener_numeral: 21.60pt, // 0.660*40.0 + 21.60 = 48.00 total
)

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
    note: 9.2pt,
    quote: 10.2pt,
    // v2 designed cover and chapter opener (D2, D4).
    cover_title: 34pt,
    cover_subtitle: 12.6pt,
    cover_meta: 8.4pt,
    cover_index: 8.6pt,
    opener_numeral: 40pt,
  ),
  leading_extra: leading_extra,
  space: (
    page_margin: 60pt,
    before_heading: 17pt,
    // D6: level-2/3 headings separate from the preceding body text. Both must
    // exceed between_paragraphs for Typst's max() to have any effect.
    before_h2: 32pt,
    before_h3: 25pt,
    before_role: 18pt,
    after_heading: 4.5pt,
    // Smallest white gap kept between a heading's descender ink and the next
    // block's ascender ink. The rendered rhythm check fails below one 300-dpi
    // raster row (0.24 pt); this token leaves that row in hand.
    heading_clearance: 0.5pt,
    // Extra deck gap for the first standfirst/lead under a level-1 heading.
    // Typst combines adjacent block spacing with max(), so this is added to
    // after_heading (4.5 + 6 = 10.5 pt). That opens a measured 3.36 pt
    // full-width ink gap at 300 dpi and a 32.75 pt h1→standfirst baseline
    // delta, close to the 31.08 pt contents h1→entry spacing. Level-2/3
    // standfirsts keep the plain after_heading gap.
    before_standfirst: 6pt,
    after_block: 5.4pt,
    // Body prose rhythm: one line pitch plus the intentional extra gap.
    between_paragraphs: leading_extra.body + 5.4pt,
    after_lead: 12pt,
    after_figure: 14pt,
    after_caption: 8pt,
    side_gutter: 16pt,
    // D2 cover rhythm and D4 chapter-opener rhythm.
    opener_rule: 12pt,
    opener_title: 14pt,
    cover_rule: 12pt,
    cover_footer: 24pt,
  ),
  measure: (
    body: 475.28pt,
    // D4: a plate is one visual at the full text measure.
    plate: 475.28pt,
    // D2: A4 height, so the cover can fill the text block and pin its footer.
    page_height: 297mm,
    figure_width: 430pt,
    side_fraction: 0.46,
  ),
  rule: (
    table_top: 0.6pt,
    table_head: 0.4pt,
    table_bottom: 0.6pt,
    figure_stroke: 0.55pt,
    // D2/D4: the only ornament the house style allows.
    cover: 0.6pt,
    cover_index: 0.4pt,
    opener: 0.6pt,
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

// D3: appendix letters mirror `normalize.appendix_letter` (1 -> A, 27 -> AA).
#let appendix-name(index) = {
  let name = ""
  let value = index
  while value > 0 {
    value = value - 1
    name = str.from-unicode(65 + calc.rem(value, 26)) + name
    value = calc.floor(calc.quo(value, 26))
  }
  name
}

// D3: chapter headings print 1, 1.1, 1.1.1; appendices print Appendix A, A.1.
// `chapter-count` is the number of level-1 chapters before the appendices.
#let heading-numbering(chapter-count) = (..nums) => {
  let values = nums.pos()
  if values.len() == 0 { return "" }
  let first = values.first()
  let parents = values.slice(1)
  let back = chapter-count != none and first > chapter-count
  let head = if back { appendix-name(first - chapter-count) } else { str(first) }
  if parents.len() == 0 {
    if back { "Appendix " + head } else { head }
  } else {
    head + "." + parents.map(str).join(".")
  }
}

// The below gap for a heading at `size`. Descender ink reaches
// `descent_em * size` below the baseline the layout line ends at, and the next
// line's tallest ascenders rise `(ascent_em - line_box_em) * follow` above its
// own layout line. `follow` is the largest face the theme can place directly
// under a heading (the lead), so one rule is conservative for every block type.
#let heading-below(size, follow: tokens.type.lead) = calc.max(
  tokens.space.after_heading,
  ink_metrics.descent_em * size
    + (ink_metrics.ascent_em - ink_metrics.line_box_em) * follow
    + tokens.space.heading_clearance,
)

// Base rules: one serif family, local faces, explicit per-script selection.
#let book_base(body, chapter-count: none) = {
  set page(paper: "a4", margin: tokens.space.page_margin)
  set text(font: (fonts.latin, fonts.japanese), size: tokens.type.body, lang: "en", region: "GB")
  set par(justify: true, leading: tokens.leading_extra.body)
  show math.equation: set text(font: fonts.maths)
  show heading: set text(font: fonts.latin, weight: 600)
  show heading.where(level: 1): set text(size: tokens.type.h1, weight: 500)
  show heading.where(level: 1): set par(leading: tokens.leading_extra.h1)
  show heading.where(level: 1): set block(above: tokens.space.before_heading, below: heading-below(tokens.type.h1))
  show heading.where(level: 2): set text(size: tokens.type.h2, weight: 600)
  show heading.where(level: 2): set par(leading: tokens.leading_extra.h2)
  show heading.where(level: 2): set block(above: tokens.space.before_h2, below: heading-below(tokens.type.h2))
  show heading.where(level: 3): set text(size: tokens.type.h3, weight: 600)
  show heading.where(level: 3): set par(leading: tokens.leading_extra.h3)
  show heading.where(level: 3): set block(above: tokens.space.before_h3, below: heading-below(tokens.type.h3))
  set heading(numbering: heading-numbering(chapter-count))
  body
}
