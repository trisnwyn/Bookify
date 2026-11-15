#import "/typst/theme.typ": book_base, heading-below, tokens
#import "/typst/blocks.typ": *
#import "/typst/cetz/diagram.typ": diagram

#let doc = json(sys.inputs.data)
#let chapters = doc.sections.filter(section => section.level == 1 and section.role == "chapter").len()

#set page(numbering: "1")
#show: body => book_base(body, chapter-count: chapters)

// D4: every level-1 chapter opens with its printed number, a rule and the
// title; the authored standfirst keeps its own gap. Front-matter headings
// (the contents title) have no number and keep the plain level-1 treatment.
#show heading.where(level: 1): it => {
  if it.numbering == none {
    block(above: tokens.space.before_heading, below: heading-below(tokens.type.h1), {
      set text(size: tokens.type.h1, weight: 500)
      par(leading: tokens.leading_extra.h1, justify: false, it.body)
    })
  } else {
    context {
      let nums = counter(heading).at(here())
      block(above: tokens.space.before_heading, below: heading-below(tokens.type.h1), {
        block({
          set text(size: tokens.type.opener_numeral, weight: 500)
          set par(leading: tokens.leading_extra.opener_numeral, justify: false)
          numbering(it.numbering, ..nums)
        })
        v(tokens.space.opener_rule)
        line(length: 100%, stroke: tokens.rule.opener)
        v(tokens.space.opener_title)
        block({
          set text(size: tokens.type.h1, weight: 500)
          par(leading: tokens.leading_extra.h1, justify: false, it.body)
        })
      })
    }
  }
}

// D2: a typographic cover in the house style. Oversized left-aligned title,
// one full-measure rule, the real chapter index (or the ledger motif beyond
// twelve entries), and a footer line. No folio, no colour, no image.
#let cover-title(metadata) = block({
  set text(size: tokens.type.cover_title, weight: 500)
  set par(leading: tokens.leading_extra.cover_title, justify: false)
  metadata.title
})

#let cover-subtitle(metadata) = block({
  set text(size: tokens.type.cover_subtitle, style: "italic", fill: tokens.ink.grey_1)
  set par(leading: tokens.leading_extra.lead, justify: false)
  metadata.subtitle
})

#let cover-meta(body) = block({
  set text(size: tokens.type.cover_meta, fill: tokens.ink.grey_1)
  body
})

#let cover-index-entry(entry) = block(above: tokens.space.after_caption, below: tokens.space.after_caption, width: 100%, {
  grid(
    columns: (auto, 1fr),
    column-gutter: tokens.space.side_gutter,
    {
      set text(size: tokens.type.cover_index, fill: tokens.ink.grey_1)
      set par(leading: tokens.leading_extra.cover_index, justify: false)
      entry.number
    },
    {
      set text(size: tokens.type.cover_index)
      set par(leading: tokens.leading_extra.cover_index, justify: false)
      entry.title
    },
  )
})

#let cover-index(cover) = {
  if cover.indexMode == "list" {
    for (index, entry) in cover.index.enumerate() {
      cover-index-entry(entry)
      if index < cover.index.len() - 1 {
        line(length: 100%, stroke: tokens.rule.cover_index)
      }
    }
  } else {
    // Documented ledger motif: three thin rules of unequal measure, no list.
    line(length: 100%, stroke: tokens.rule.cover_index)
    v(tokens.space.cover_rule)
    line(length: 62%, stroke: tokens.rule.cover_index)
    v(tokens.space.cover_rule)
    line(length: 34%, stroke: tokens.rule.cover_index)
  }
}

#let cover-footer(metadata) = {
  line(length: 100%, stroke: tokens.rule.cover_index)
  v(tokens.space.cover_rule)
  if "author" in metadata {
    cover-meta(metadata.author)
  }
  if "course" in metadata {
    cover-meta(metadata.course)
  }
}

#let render-cover(metadata, cover) = block(width: 100%, height: tokens.measure.page_height - tokens.space.page_margin * 2, {
  // The first line's glyph box rises above the layout line at a large size; a
  // small token gap keeps every ink pixel inside the 60 pt margin.
  v(tokens.space.after_block)
  if "institution" in metadata {
    cover-meta(metadata.institution)
    v(tokens.space.cover_footer)
  }
  cover-title(metadata)
  if "subtitle" in metadata {
    v(tokens.space.cover_rule)
    cover-subtitle(metadata)
  }
  v(tokens.space.cover_rule)
  line(length: 100%, stroke: tokens.rule.cover)
  v(tokens.space.cover_rule)
  cover-index(cover)
  v(1fr)
  // Pinned to the bottom of the text block, lifted by the footer token plus
  // the block gap so the *ink* keeps the required 24 pt slack after the last
  // line's descent. Never floats into the margin.
  place(bottom, dy: -(tokens.space.cover_footer + tokens.space.after_block), cover-footer(metadata))
})

#page(numbering: none)[#render-cover(doc.metadata, doc.cover)]

// One section body. A pagebreak from illustration deferral is only legal in
// flowing content; a plate keep unit is moved whole instead.
#let render-section(section, allow-break: true) = {
  if section.kicker != none {
    block(sticky: true, {
      set text(size: tokens.type.small, fill: tokens.ink.grey_1)
      section.kicker
    })
    parbreak()
  }
  heading(level: section.level, section.title)
  if section.standfirst != none {
    if section.level == 1 {
      preset-standfirst(section.standfirst)
    } else {
      preset-lead(section.standfirst)
    }
  }
  for (block-index, block) in section.blocks.enumerate() {
    if block.type == "paragraph" {
      preset-paragraph(block.text)
    } else if block.type == "lead" {
      // Only a level-1 section whose first block is the lead gets the deck
      // gap; a lead that follows a standfirst or body prose keeps the plain
      // lead rhythm.
      if section.level == 1 and block-index == 0 and section.standfirst == none {
        preset-standfirst(block.text)
      } else {
        preset-lead(block.text)
      }
    } else if block.type == "quote" {
      preset-quote(block.text, attribution: if "attribution" in block { block.attribution } else { none })
    } else if block.type == "definition" {
      preset-definition(block.term, block.definition)
    } else if block.type == "example" {
      preset-example(title: if "title" in block { block.title } else { none }, block.text)
    } else if block.type == "case" {
      preset-case(title: if "title" in block { block.title } else { none }, block.text)
    } else if block.type == "assessment" {
      preset-assessment(title: if "title" in block { block.title } else { none }, block.text)
    } else if block.type == "list" {
      preset-list(block.items, ordered: block.ordered)
    } else if block.type == "table" {
      preset-table(block.header, block.rows, caption: block.caption, widths: block.widths)
    } else if block.type == "equation" {
      preset-equation(eval(block.typst, mode: "math"), caption: block.caption)
    } else if block.type == "chart" {
      preset-chart(image(block.path, width: 100%), caption: block.caption, note: if "note" in block { block.note } else { none })
    } else if block.type == "diagram" {
      preset-diagram(diagram(block.spec, tokens.measure.plate), caption: block.caption, note: if "note" in block { block.note } else { none })
    } else if block.type == "unresolved" {
      preset-unresolved(block.note)
    } else if block.type == "illustration" {
      if allow-break and "pagebreak" in block and block.pagebreak {
        pagebreak()
      }
      let composition = if "composition" in block { block.composition } else { "full" }
      let companion = if "companion" in block { companion-content(block.companion) } else { none }
      preset-illustration(
        image(block.path, width: 100%),
        caption: block.caption,
        credit: block.credit,
        composition: composition,
        companion: companion,
        note: if "note" in block { block.note } else { none },
      )
    }
    // A resolved note follows its block; chart/diagram carry theirs inside
    // the unbreakable figure unit, and unresolved uses its own preset.
    if block.type not in ("chart", "diagram", "unresolved", "illustration") and "note" in block {
      preset-note(block.note)
    }
  }
}

#outline(title: [Contents], depth: 3)
#pagebreak()

#for (section-index, section) in doc.sections.enumerate() [
  // A level-1 section defaults to `page`; levels 2/3 default to `auto`.
  // The first body section never breaks, even if an explicit value says page.
  #if section-index > 0 and section.breakBefore == "page" [
    #pagebreak()
  ]
  #let keep = if "keepTogether" in section { section.keepTogether } else { false }
  // A deferred plate moves as a whole: lift its one-illustration break outside
  // the keep container, where a pagebreak is legal.
  #if keep and section.blocks.any(block => block.type == "illustration" and "pagebreak" in block and block.pagebreak) [
    #pagebreak()
  ]
  // Ordinary chapters stay breakable. A pure plate section is one keep unit;
  // if it cannot fit, the build's unit-fit guard fails by block id.
  #if keep [
    #block(breakable: false, render-section(section, allow-break: false))
  ] else [
    #render-section(section)
  ]
]
