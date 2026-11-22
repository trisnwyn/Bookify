#import "/typst/theme.typ": book_base, heading-below, tokens
#import "/typst/blocks.typ": *
#import "/typst/cover.typ": render-cover
#import "/typst/compositions.typ": block-width, illustration-width, section-columns
#import "/typst/cetz/diagram.typ": diagram

#let doc = json(sys.inputs.data)
#let chapters = doc.sections.filter(section => section.level == 1 and section.role == "chapter").len()

// The PDF carries the book's own identity. It comes from the manuscript and
// nowhere else: no field is invented, and no date is taken from the clock, so
// two builds of one manuscript still agree in every metadata field.
// `languages` is not wired here: Typst declares the document language through
// `text(lang:)`, which changes line breaking, so it stays with that work.
#let book-author = doc.metadata.at("author", default: none)
#let book-metadata = (title: doc.metadata.title)
// Typst rejects `author: none`, so the field is present only when the
// manuscript declares one; nothing is substituted.
#if book-author != none { book-metadata.insert("author", book-author) }
#set document(..book-metadata)

#set page(numbering: "1")
#show: body => book_base(body, chapter-count: chapters)

// D4 (superseded): the chapter heading is one h1 line in the form
// `Chapter 1: Title`; the numeral, rule and title stack is retired. The counter
// still numbers the contents list with the bare `1`, so the printed sentence
// form is added here only. Front-matter headings (the contents title) have no
// number and keep the plain level-1 treatment.
#show heading.where(level: 1): it => {
  block(above: tokens.space.before_heading, below: heading-below(tokens.type.h1), {
    set text(size: tokens.type.h1, weight: 500)
    par(leading: tokens.leading_extra.h1, justify: false, {
      if it.numbering != none {
        context {
          let printed = numbering(it.numbering, ..counter(heading).at(here()))
          let prefix = if printed.starts-with("Appendix") { printed + ":" } else { "Chapter " + printed + ":" }
          prefix + " " + it.body
        }
      } else {
        it.body
      }
    })
  })
}

// The selected cover composition draws the page; `doc.cover` records the
// selection (author or engine fallback) and the artwork state.
#page(numbering: none)[#render-cover(doc.metadata, doc.cover)]

// One section body. A pagebreak from illustration deferral is only legal in
// flowing content; a plate keep unit is moved whole instead. `column` tells the
// block renderer it is inside a two-column chapter, so a visual takes the column
// measure instead of the plate/figure measure.
#let render-blocks(section, allow-break: true, column: false) = {
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
    } else if block.type == "branch" {
      preset-branch(block.marker, block.text)
    } else if block.type == "list" {
      preset-list(block.items, ordered: block.ordered)
    } else if block.type == "table" {
      preset-table(block.header, block.rows, caption: block.caption, widths: block.widths)
    } else if block.type == "equation" {
      preset-equation(eval(block.typst, mode: "math"), caption: block.caption)
    } else if block.type == "chart" {
      preset-chart(image(block.path, width: 100%), caption: block.caption, note: if "note" in block { block.note } else { none })
    } else if block.type == "diagram" {
      preset-diagram(diagram(block.spec, block-width(column: column)), caption: block.caption, note: if "note" in block { block.note } else { none })
    } else if block.type == "unresolved" {
      preset-unresolved(block.note)
    } else if block.type == "illustration" {
      if allow-break and "pagebreak" in block and block.pagebreak {
        pagebreak()
      }
      let composition = if "composition" in block { block.composition } else { "full" }
      let width = illustration-width(composition, column: column)
      let companions = if "companions" in block {
        block.companions.map(entry => companion-content(entry))
      } else if "companion" in block {
        (companion-content(block.companion),)
      } else {
        ()
      }
      preset-illustration(
        image(block.path, width: width),
        caption: block.caption,
        credit: block.credit,
        composition: composition,
        companions: companions,
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

#let render-head(section) = {
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
}

#let render-section(section, allow-break: true, column: false) = {
  render-head(section)
  render-blocks(section, allow-break: allow-break, column: column)
}

// A pure-plate section is one keep unit. Typst drops an inner heading's `above`
// at the start of a block, so the keep block carries the gap itself.
#let keep-above(level) = if level == 1 {
  tokens.space.before_heading
} else if level == 2 {
  tokens.space.before_h2
} else {
  tokens.space.before_h3
}

// A chapter and its descendant sections are one authored unit: a two-column
// chapter sets all of them inside the same column flow, as the accepted A2
// composition does (heading and standfirst full measure, then columns).
#let groups = doc.sections.fold((), (acc, section) => {
  if section.level == 1 {
    acc.push((head: section, children: ()))
  } else {
    let last = acc.pop()
    last.children.push(section)
    acc.push(last)
  }
  acc
})

#outline(title: [Contents], depth: 5)
#pagebreak()

#for (group-index, group) in groups.enumerate() [
  #let section = group.head
  // The first body section never breaks, even if an explicit value says page.
  #if group-index > 0 and section.breakBefore == "page" [
    #pagebreak()
  ]
  #let keep = if "keepTogether" in section { section.keepTogether } else { false }
  #let two-column = "layout" in section and section.layout.columns == 2
  // A deferred plate moves as a whole: lift its one-illustration break outside
  // the keep container, where a pagebreak is legal.
  #if keep and not two-column and section.blocks.any(block => block.type == "illustration" and "pagebreak" in block and block.pagebreak) [
    #pagebreak()
  ]
  #if two-column [
    #render-head(section)
    #section-columns({
      render-blocks(section, column: true)
      for child in group.children [
        #if child.breakBefore == "page" { pagebreak() }
        #render-section(child, column: true)
      ]
    })
  ] else if keep [
    #block(above: keep-above(section.level), breakable: false, render-section(section, allow-break: false))
    #for child in group.children [
      #if child.breakBefore == "page" { pagebreak() }
      #render-section(child)
    ]
  ] else [
    #render-section(section)
    #for child in group.children [
      #if child.breakBefore == "page" { pagebreak() }
      #render-section(child)
    ]
  ]
]
