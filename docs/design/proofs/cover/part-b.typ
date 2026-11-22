// DISPOSABLE COVER LAYOUT PROOF, PART B. Not a product template.
// Composition references: parsed Cover.pdf pages 5-7. Layout only; measurements
// and fonts are NOT copied from the references. Every visual value below is
// imported from the live Bookify theme, and the page is the live A4 text block
// (210 x 297 mm, 60 pt margins, 475.276 x 721.890 pt). No production file is
// read for writing or modified.
//
// Page order: 1 = reference 5, 2 = reference 6, 3 = reference 7.
// Text is limited to the four supplied placeholders. The illustration is a
// native vector placeholder with no data and no raster asset.
#import "/typst/theme.typ": tokens, fonts

#set document(
  title: "Bookify cover layout proof, part B (disposable)",
  author: "Bookify",
  keywords: ("cover", "layout proof", "disposable"),
)
#set page(paper: "a4", margin: tokens.space.page_margin, numbering: none)
#set text(
  font: (fonts.latin, fonts.japanese),
  size: tokens.type.body,
  lang: "en",
  region: "gb",
)
#set par(justify: false, leading: tokens.leading_extra.body)

// Live A4 text block. All coordinates below are relative to this block, so the
// 60 pt margin is structural: nothing can be positioned by page-edge accident.
#let W = 210mm - 2 * tokens.space.page_margin
#let H = 297mm - 2 * tokens.space.page_margin

#let stage(body) = block(width: 100%, height: H, body)

#let cover-title(body) = block({
  set text(size: tokens.type.cover_title, weight: 500, fill: tokens.ink.text)
  set par(leading: tokens.leading_extra.cover_title, justify: false)
  body
})

#let cover-support(body) = block({
  set text(size: tokens.type.cover_subtitle, style: "italic", fill: tokens.ink.grey_1)
  set par(leading: tokens.leading_extra.lead, justify: false)
  body
})

#let cover-meta(body) = block({
  set text(size: tokens.type.cover_meta, fill: tokens.ink.grey_1)
  set par(leading: tokens.leading_extra.small, justify: false)
  body
})

// Neutral proof-only vector illustration: a solid radial burst built as one
// polygon. `outer`/`inner` are the visible radii. Vertices are offset into a
// positive 2*outer square and the square is placed by its top-left corner; this
// avoids Typst shifting a shape that carries negative coordinates, which would
// silently push the illustration into the page margin.
#let burst(cx, cy, outer, inner, points: 8, phase: 0deg) = {
  let vertices = range(points * 2).map(i => {
    let r = if calc.rem(i, 2) == 0 { outer } else { inner }
    let angle = phase + i * 360deg / (points * 2)
    (outer + r * calc.cos(angle), outer + r * calc.sin(angle))
  })
  place(
    top + left,
    dx: cx - outer,
    dy: cy - outer,
    polygon(fill: tokens.ink.text, ..vertices),
  )
  // The label stays inside the solid central area, white on black.
  place(
    top + left,
    dx: cx - 42pt,
    dy: cy - 5pt,
    block(width: 84pt, align(center, text(
      size: tokens.type.cover_meta,
      fill: tokens.ink.pale,
    )[Illustration])),
  )
}

// ---------------------------------------------------------------------------
// Page 1 — reference 5. Asymmetric diagonal field; title and support run with
// the field edge; illustration anchors the opposite lower-left region.
// ---------------------------------------------------------------------------
#page[
  #stage({
    // Pale field: edge from content-left y=540 pt to content-right y=380 pt.
    // Drawn inside the text block; it touches the content edge, never the trim.
    place(
      top + left,
      dx: 0pt,
      dy: 380pt,
      polygon(
        fill: tokens.ink.pale,
        (0pt, 160pt),
        (W - 1pt, 0pt),
        (W - 1pt, H - 381pt),
        (0pt, H - 381pt),
      ),
    )

    place(top + center, dy: 8pt, cover-meta[Additional information])

    // The diagonal is an edge relation, not a copied angle. The title and its
    // support stay upright and step right along the field edge: the left edges
    // advance with the edge's rise, so the composition reads as one diagonal
    // gesture while every word remains horizontally searchable.
    place(top + left, dx: 205pt, dy: 395pt, cover-title[Cover])
    place(top + left, dx: 245pt, dy: 430pt, cover-support[Additional information])

    burst(120pt, 560pt, 115pt, 46pt, points: 10)

    place(top + left, dx: 310pt, dy: 645pt, cover-meta[Decorative illustration])

    place(top + center, dy: H - 18pt, cover-meta[Additional information])
  })
]

// ---------------------------------------------------------------------------
// Page 2 — reference 6. Strongly off-centre composition: a large lower-left
// illustration block and a right-hand vertical title/meta pair. The vertical
// arrangement is kept because the 34 pt title remains readable top-to-bottom.
// ---------------------------------------------------------------------------
#page[
  #stage({
    // Illustration block, inside the text block.
    place(
      top + left,
      dx: 0pt,
      dy: 110pt,
      rect(width: 235pt, height: 590pt, fill: tokens.ink.pale),
    )

    place(top + center, dy: 8pt, cover-meta[Additional information])

    burst(118pt, 465pt, 105pt, 42pt, points: 8, phase: 22.5deg)

    // Vertical label inside the block, top-to-bottom; clear of the burst.
    place(
      top + left,
      dx: 25pt,
      dy: 590pt,
      rotate(90deg, origin: top + left, cover-meta[Decorative illustration]),
    )

    // Title at the far right; meta to its left. Reading direction is
    // top-to-bottom (90deg clockwise), as in the reference. The title's ink
    // ends 6.7 pt inside the 475.276 pt content measure; no margin contact.
    place(
      top + left,
      dx: 455pt,
      dy: 155pt,
      rotate(90deg, origin: top + left, cover-title[Cover]),
    )
    place(
      top + left,
      dx: 400pt,
      dy: 155pt,
      rotate(90deg, origin: top + left, cover-support[Additional information]),
    )

    place(top + right, dx: -1pt, dy: 675pt, cover-meta[Additional information])
  })
]

// ---------------------------------------------------------------------------
// Page 3 — reference 7. Sparse, intentional: compact upper line, central-ish
// title with its support, one separate illustration lower-left, quiet footer.
// ---------------------------------------------------------------------------
#page[
  #stage({
    place(top + center, dy: 8pt, cover-meta[Additional information])

    place(top + left, dx: 190pt, dy: 150pt, cover-title[Cover])
    place(top + left, dx: 200pt, dy: 190pt, cover-support[Additional information])

    burst(148pt, 505pt, 140pt, 58pt, points: 8)

    place(top + center, dy: H - 18pt, cover-meta[Additional information])
  })
]
