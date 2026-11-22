// DISPOSABLE COVER-LAYOUT PROOF — PART A. Not a product template.
//
// Composition references: parsed Cover.pdf pages 1–4. Only the topology
// (where the meta, illustration, title and supporting meta sit relative to
// each other) is taken from the references. Every visual value below is read
// from the current Bookify theme: A4, 60 pt margins, Spectral, cover type
// sizes/leading, ink tokens and hairline rules. No reference measurement,
// font, size, colour or asset is used.
//
// All copy is a neutral placeholder. No title, author, date, institution,
// course or ISBN is invented. The illustration is a local vector placeholder
// drawn with theme shapes; there is no image asset.
//
// Build from the repository root, offline and vendored:
//   tools/typst/typst compile \
//     --ignore-system-fonts --ignore-embedded-fonts \
//     --font-path assets/fonts \
//     --package-path vendor/typst --package-cache-path .cache/empty-pkg \
//     --creation-timestamp 1750000000 --root . \
//     build/design/cover/part-a.typ build/design/cover/part-a.pdf

#import "/typst/theme.typ": book_base, tokens

#set page(numbering: none)
#show: book_base

// The cover block occupies exactly the A4 text block: 297 mm less both 60 pt
// margins. page_height is the current cover token; page_margin is the current
// A4 grid token.
#let cover-block-height = tokens.measure.page_height - tokens.space.page_margin * 2

// ---------------------------------------------------------------------------
// Cover typography. Same tokens and emphasis as the current designed cover.
// ---------------------------------------------------------------------------
#let cover-title(body) = block(width: 100%, {
  set align(center)
  set text(size: tokens.type.cover_title, weight: 500, fill: tokens.ink.text)
  set par(leading: tokens.leading_extra.cover_title, justify: false)
  body
})

#let cover-title-left(body) = block(width: 100%, {
  set align(left)
  set text(size: tokens.type.cover_title, weight: 500, fill: tokens.ink.text)
  set par(leading: tokens.leading_extra.cover_title, justify: false)
  body
})

#let cover-subtitle-centred(body) = block(width: 100%, {
  set align(center)
  set text(size: tokens.type.cover_subtitle, style: "italic", fill: tokens.ink.grey_1)
  set par(leading: tokens.leading_extra.lead, justify: false)
  body
})

#let cover-subtitle-left(body) = block(width: 100%, {
  set align(left)
  set text(size: tokens.type.cover_subtitle, style: "italic", fill: tokens.ink.grey_1)
  set par(leading: tokens.leading_extra.lead, justify: false)
  body
})

#let cover-meta-centred(body) = block(width: 100%, {
  set align(center)
  set text(size: tokens.type.cover_meta, fill: tokens.ink.grey_1)
  set par(leading: tokens.leading_extra.small, justify: false)
  body
})

#let cover-meta-left(body) = block(width: 100%, {
  set align(left)
  set text(size: tokens.type.cover_meta, fill: tokens.ink.grey_1)
  set par(leading: tokens.leading_extra.small, justify: false)
  body
})

// ---------------------------------------------------------------------------
// Local proof-only vector illustration. A pale panel, a 0.55 pt figure stroke
// and two 0.4 pt diagonals, all existing theme values, with a searchable label
// on a white chip. No raster asset and no reference colour.
// ---------------------------------------------------------------------------
#let illustration(width, height) = block(width: width, height: height, {
  place(rect(
    width: 100%,
    height: 100%,
    fill: tokens.ink.pale,
    stroke: tokens.rule.figure_stroke + tokens.ink.grey_3,
  ))
  place(top + left, line(
    start: (0pt, 0pt),
    end: (width, height),
    stroke: tokens.rule.cover_index + tokens.ink.grey_3,
  ))
  place(top + left, line(
    start: (width, 0pt),
    end: (0pt, height),
    stroke: tokens.rule.cover_index + tokens.ink.grey_3,
  ))
  place(center + horizon, block(
    fill: white,
    stroke: tokens.rule.cover_index + tokens.ink.grey_3,
    inset: (x: 7pt, y: 3pt),
    {
      set text(size: tokens.type.cover_meta, fill: tokens.ink.grey_1)
      set par(leading: tokens.leading_extra.small, justify: false)
      [Decorative illustration]
    },
  ))
})

// One A4 text-block-high page. The footer is pinned to the bottom of the text
// block and lifted by the after-block token, so its descender ink stays inside
// the 60 pt margin. Nothing is absolutely positioned outside this block.
#let cover-page(body) = block(
  width: 100%,
  height: cover-block-height,
  {
    v(tokens.space.after_block)
    body
  },
)

#let footer() = place(
  bottom,
  dy: -(tokens.space.after_block + tokens.rule.cover_index),
  cover-meta-centred[Additional information],
)

// ---------------------------------------------------------------------------
// Reference composition 1: centred small metadata at the top; illustration
// above the title, offset to the right as in the reference; title and
// secondary metadata in the lower-left half; centred metadata at the foot.
// ---------------------------------------------------------------------------
#cover-page({
  cover-meta-centred[Additional information]
  v(40pt)

  // 0.72 of the current body measure, square-ish, right-aligned. Inset by the
  // 0.55 pt stroke half-width so the panel ink stays inside the text measure.
  block(width: 100%, {
    align(right, illustration(342.24pt, 352pt))
  })
  v(32pt)

  cover-title-left[Cover]
  v(10pt)
  cover-subtitle-left[Additional information]
  v(7pt)
  cover-meta-left[Additional information]

  footer()
})

#pagebreak()

// ---------------------------------------------------------------------------
// Reference composition 2: centred top metadata; centred illustration in the
// upper/middle; cover title and supporting metadata below it; centred foot
// metadata.
// ---------------------------------------------------------------------------
#cover-page({
  cover-meta-centred[Additional information]
  v(32pt)

  // 0.70 of the current body measure, square-ish, optically centred.
  block(width: 100%, {
    align(center, illustration(332.70pt, 340pt))
  })
  v(46pt)

  cover-title[Cover]
  v(10pt)
  cover-subtitle-centred[Additional information]

  footer()
})

#pagebreak()

// ---------------------------------------------------------------------------
// Reference composition 3: centred top metadata; title around the upper-middle
// with supporting metadata above and below; a second metadata line low on the
// page; centred foot metadata. The reference carries no illustration here.
// ---------------------------------------------------------------------------
#cover-page({
  cover-meta-centred[Additional information]
  v(92pt)

  cover-title[Cover]
  v(14pt)
  cover-subtitle-centred[Additional information]
  v(340pt)

  cover-meta-centred[Additional information]

  footer()
})

#pagebreak()

// ---------------------------------------------------------------------------
// Reference composition 4: centred top metadata; title and supporting metadata
// near the top; a wide illustration after the title; centred foot metadata.
// ---------------------------------------------------------------------------
#cover-page({
  cover-meta-centred[Additional information]
  v(24pt)

  cover-title[Cover]
  v(10pt)
  cover-subtitle-centred[Additional information]
  v(70pt)

  // Full current body measure less the 0.55 pt stroke, so its outer ink edge
  // is exactly the 60 pt text-block edge. Landscape, matching the reference
  // topology; height is not taken from the reference.
  block(width: 100%, {
    align(center, illustration(tokens.measure.body - tokens.rule.figure_stroke, 330pt))
  })

  footer()
})
