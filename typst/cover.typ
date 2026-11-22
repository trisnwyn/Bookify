// The seven accepted cover compositions (cover-1 .. cover-7).
//
// Composition is authored data (`metadata.cover.composition`); this module only
// draws the selected one. No composition is a house default: an absent selection
// reaches here as `cover-3`, the typographic composition, and the build report
// records it as `engine-fallback`, never as a user choice.
//
// Artwork is a rights-checked illustration record. When a composition has an
// illustration field and the record supplies none, the field stays empty and the
// report says `artwork: absent`. This module never draws a burst, panel label or
// placeholder word to fill the gap: a reserved field is blank paper.
//
// Every visual value comes from `tokens`; there are no point literals here.

#import "/typst/theme.typ": tokens

#let cover-block-height = tokens.measure.page_height - tokens.space.page_margin * 2
#let body-height = tokens.measure.page_height - 2 * tokens.space.page_margin

// In-flow cover text fills the measure; absolutely placed text is fitted to its
// own content (`fitted: true`), because a full-width block starting at an offset
// would run out of the text measure.
#let cover-title(body, alignment: center, fitted: false) = {
  let content = {
    set text(size: tokens.type.cover_title, weight: 500, fill: tokens.ink.text)
    set par(leading: tokens.leading_extra.cover_title, justify: false)
    body
  }
  if fitted { box(content) } else { block(width: 100%, { set align(alignment); content }) }
}

#let cover-subtitle(body, alignment: center, fitted: false) = {
  let content = {
    set text(size: tokens.type.cover_subtitle, style: "italic", fill: tokens.ink.grey_1)
    set par(leading: tokens.leading_extra.lead, justify: false)
    body
  }
  if fitted { box(content) } else { block(width: 100%, { set align(alignment); content }) }
}

#let cover-meta(body, alignment: center, fitted: false) = {
  let content = {
    set text(size: tokens.type.cover_meta, fill: tokens.ink.grey_1)
    set par(leading: tokens.leading_extra.small, justify: false)
    body
  }
  if fitted { box(content) } else { block(width: 100%, { set align(alignment); content }) }
}

// One A4 text-block-high page. The footer is pinned to the bottom of the text
// block and lifted by the after-block token, so its descender ink stays inside
// the 60 pt margin.
#let cover-page(body) = block(
  width: 100%,
  height: cover-block-height,
  {
    v(tokens.space.after_block)
    body
  },
)

#let cover-top-meta(metadata) = if "institution" in metadata {
  cover-meta(metadata.institution)
}

#let cover-title-block(metadata, alignment) = cover-title(metadata.title, alignment: alignment)

#let cover-subtitle-block(metadata, alignment) = if "subtitle" in metadata {
  cover-subtitle(metadata.subtitle, alignment: alignment)
}

#let cover-footer(metadata) = {
  if "course" in metadata { cover-meta(metadata.course) }
  if "author" in metadata { cover-meta(metadata.author) }
}

#let cover-footer-pin(metadata) = place(
  bottom,
  dy: -tokens.space.after_block,
  cover-footer(metadata),
)

// A reserved illustration field. With a rights-checked record it shows the
// artwork; without one it is an empty field of the same size, never a drawing.
#let art-field(width, height, path: none) = block(width: width, height: height, {
  if path != none {
    image(path, width: 100%, height: 100%, fit: "contain")
  }
})

#let cover-art(cover) = if "artwork" in cover and cover.artwork == "present" {
  cover.artworkPath
} else { none }

// ---------------------------------------------------------------------------
// cover-1 — right-offset illustration above a lower-left title block.
// ---------------------------------------------------------------------------
#let cover-1(metadata, cover) = {
  let t = tokens.cover.comp1
  cover-top-meta(metadata)
  v(t.meta_gap)
  block(width: 100%, {
    align(right, art-field(t.art_width, t.art_height, path: cover-art(cover)))
  })
  v(t.art_gap)
  cover-title-block(metadata, left)
  v(t.title_gap)
  if "subtitle" in metadata {
    cover-subtitle(metadata.subtitle, alignment: left)
    v(t.sub_gap)
  }
  cover-footer-pin(metadata)
}

// ---------------------------------------------------------------------------
// cover-2 — centred illustration, centred title and support, centred foot.
// ---------------------------------------------------------------------------
#let cover-2(metadata, cover) = {
  let t = tokens.cover.comp2
  cover-top-meta(metadata)
  v(t.meta_gap)
  block(width: 100%, {
    align(center, art-field(t.art_width, t.art_height, path: cover-art(cover)))
  })
  v(t.art_gap)
  cover-title-block(metadata, center)
  v(t.title_gap)
  cover-subtitle-block(metadata, center)
  cover-footer-pin(metadata)
}

// ---------------------------------------------------------------------------
// cover-3 — typographic only: title in the upper-middle, support under it, one
// quiet metadata line lower on the page. No illustration field exists.
// ---------------------------------------------------------------------------
#let cover-3(metadata, cover) = {
  let t = tokens.cover.comp3
  cover-top-meta(metadata)
  v(t.title_top)
  cover-title-block(metadata, center)
  v(t.title_gap)
  cover-subtitle-block(metadata, center)
  v(t.meta_gap)
  cover-footer-pin(metadata)
}

// ---------------------------------------------------------------------------
// cover-4 — title and support near the top, then a wide landscape field.
// ---------------------------------------------------------------------------
#let cover-4(metadata, cover) = {
  let t = tokens.cover.comp4
  cover-top-meta(metadata)
  v(t.meta_gap)
  cover-title-block(metadata, center)
  v(t.title_gap)
  cover-subtitle-block(metadata, center)
  v(t.art_gap)
  block(width: 100%, {
    align(center, art-field(
      tokens.measure.body - tokens.rule.figure_stroke,
      t.art_height,
      path: cover-art(cover),
    ))
  })
  cover-footer-pin(metadata)
}

// ---------------------------------------------------------------------------
// cover-5 — asymmetric diagonal field; upright title and support step right
// along the field edge; the illustration field sits opposite, lower-left.
// ---------------------------------------------------------------------------
#let cover-5(metadata, cover) = {
  let t = tokens.cover.comp5
  place(
    top + left,
    dx: tokens.cover.origin,
    dy: t.field_y,
    polygon(
      fill: tokens.ink.pale,
      (tokens.cover.origin, t.field_drop),
      (tokens.measure.body - t.field_inset, tokens.cover.origin),
      (tokens.measure.body - t.field_inset, body-height - t.field_y - t.field_inset),
      (tokens.cover.origin, body-height - t.field_y - t.field_inset),
    ),
  )
  if "institution" in metadata {
    place(top + center, dy: tokens.cover.meta_top, cover-meta(metadata.institution, fitted: true))
  }
  // The title block wraps inside the measured width and carries its support
  // directly beneath it, indented along the diagonal gesture. A fixed support
  // offset cannot know how many lines the title used.
  place(top + left, dx: t.title_x, dy: t.title_y, block(width: t.title_width, {
    cover-title(metadata.title, alignment: left)
    if "subtitle" in metadata {
      v(t.support_gap)
      pad(left: t.support_dx, cover-subtitle(metadata.subtitle, alignment: left))
    }
  }))
  place(
    top + left,
    dx: t.art_x,
    dy: t.art_y,
    art-field(t.art_size, t.art_size, path: cover-art(cover)),
  )
  place(bottom, dy: -tokens.space.after_block, cover-footer(metadata))
}

// ---------------------------------------------------------------------------
// cover-6 — tall pale field lower-left, strongly off-centre right column with a
// 90° clockwise (vertical) title and support. Title and support are one rotated
// stack, so the support always clears however many vertical lines the title uses.
// ---------------------------------------------------------------------------
#let cover-6(metadata, cover) = {
  let t = tokens.cover.comp6
  place(
    top + left,
    dx: tokens.cover.origin,
    dy: t.field_y,
    rect(width: t.field_width, height: t.field_height, fill: tokens.ink.pale),
  )
  if "institution" in metadata {
    place(top + center, dy: tokens.cover.meta_top, cover-meta(metadata.institution, fitted: true))
  }
  place(
    top + left,
    dx: t.title_x,
    dy: t.title_y,
    rotate(90deg, origin: top + left, block(width: t.title_height, {
      cover-title(metadata.title, alignment: left)
      if "subtitle" in metadata {
        v(t.support_gap)
        cover-subtitle(metadata.subtitle, alignment: left)
      }
    })),
  )
  place(
    top + left,
    dx: t.art_x,
    dy: t.art_y,
    art-field(t.art_size, t.art_size, path: cover-art(cover)),
  )
  place(bottom, dy: -tokens.space.after_block, cover-footer(metadata))
}

// ---------------------------------------------------------------------------
// cover-7 — sparse: a compact upper meta line, a centred title with its support,
// a separate illustration field lower-left, and a quiet foot.
// ---------------------------------------------------------------------------
#let cover-7(metadata, cover) = {
  let t = tokens.cover.comp7
  if "institution" in metadata {
    place(top + center, dy: tokens.cover.meta_top, cover-meta(metadata.institution, fitted: true))
  }
  place(top + center, dy: t.title_y, block(width: tokens.measure.body, {
    cover-title(metadata.title)
    if "subtitle" in metadata {
      v(t.support_gap)
      cover-subtitle(metadata.subtitle)
    }
  }))
  place(
    top + left,
    dx: t.art_x,
    dy: t.art_y,
    art-field(t.art_size, t.art_size, path: cover-art(cover)),
  )
  place(bottom, dy: -tokens.space.after_block, cover-footer(metadata))
}

#let compositions = (
  cover-1: cover-1,
  cover-2: cover-2,
  cover-3: cover-3,
  cover-4: cover-4,
  cover-5: cover-5,
  cover-6: cover-6,
  cover-7: cover-7,
)

// Dispatch the selected composition. `cover.composition` is validated by the
// manuscript schema; an unknown value is a build error, not a silent fallback.
#let render-cover(metadata, cover) = {
  let composition = cover.composition
  if composition not in compositions {
    panic("unknown cover composition: " + composition)
  }
  cover-page(compositions.at(composition)(metadata, cover))
}
