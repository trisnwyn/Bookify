// Block presets: one function per manuscript block type, tokens only.
//
// Space semantics are deliberate: `space.between_paragraphs` is prose rhythm
// (line pitch + 5.4 pt), while heading/role/lead/note gaps stay absolute.

#import "theme.typ": tokens, fonts

#let role-label(role, body) = block(
  above: tokens.space.before_role,
  below: tokens.space.after_block,
  {
    set text(size: tokens.type.small, fill: tokens.role.at(role), weight: 600)
    set par(leading: tokens.leading_extra.small)
    body
  },
)

#let preset-paragraph(body) = block(
  below: tokens.space.between_paragraphs,
  {
    set par(leading: tokens.leading_extra.body)
    body
  },
)

#let preset-lead(body, above: auto) = block(
  above: above,
  below: tokens.space.after_lead,
  {
    set text(size: tokens.type.lead, fill: tokens.ink.grey_1)
    set par(leading: tokens.leading_extra.lead, justify: false)
    body
  },
)

// A level-1 chapter deck: the chapter title needs a clear white gap before the
// standfirst or first lead. The token is additive because Typst maxes adjacent
// block spacing against the heading's after_heading.
#let preset-standfirst(body) = preset-lead(
  body,
  above: tokens.space.after_heading + tokens.space.before_standfirst,
)

#let preset-quote(body, attribution: none) = block(
  above: tokens.space.before_heading,
  below: tokens.leading_extra.quote + tokens.space.after_block,
  {
    set text(size: tokens.type.quote, style: "italic")
    set par(leading: tokens.leading_extra.quote, justify: false)
    body
    if attribution != none {
      linebreak()
      block({
        set text(size: tokens.type.small, fill: tokens.ink.grey_1, style: "normal")
        set par(leading: tokens.leading_extra.small)
        [— #attribution]
      })
    }
  },
)

// D1: one paragraph, bold term, colon, definition. No role label, no grey,
// no standalone term line. A collated glossary is an ordinary authored table.
#let preset-definition(term, definition) = block(
  below: tokens.space.between_paragraphs,
  {
    set par(leading: tokens.leading_extra.body)
    [*#term*: #definition]
  },
)

#let preset-example(title: none, body) = {
  role-label("example", if title != none { title } else { "Example" })
  block(below: tokens.space.between_paragraphs, {
    set par(leading: tokens.leading_extra.body)
    body
  })
}

#let preset-case(title: none, body) = {
  role-label("case", if title != none { title } else { "Case" })
  block(below: tokens.space.between_paragraphs, {
    set par(leading: tokens.leading_extra.body)
    body
  })
}

#let preset-assessment(title: none, body) = {
  role-label("assessment", if title != none { title } else { "Assessment" })
  block(below: tokens.space.between_paragraphs, {
    set par(leading: tokens.leading_extra.body)
    body
  })
}

#let preset-list(items, ordered: false) = block(
  below: tokens.space.between_paragraphs,
  {
    set par(leading: tokens.leading_extra.body)
    if ordered { enum(..items) } else { list(..items) }
  },
)

// A terminal branch (`1.1 a)`) is a run-in label at body size: the bold marker
// then the prose, in one paragraph and one body pitch. It is not a new block
// style, so it never enters the heading hierarchy.
#let preset-branch(marker, body) = block(
  below: tokens.space.between_paragraphs,
  {
    set par(leading: tokens.leading_extra.body)
    [*#marker* #body]
  },
)

#let preset-table(header, rows, caption: none, widths: none) = block(
  above: tokens.space.after_block,
  below: tokens.space.after_figure,
  {
    set text(size: tokens.type.table)
    set par(leading: tokens.leading_extra.table)
    let columns = header.len()
    let columns_spec = if widths == none { range(columns).map(_ => 1fr) } else { widths.map(w => w * 1fr) }
    let captions = if caption == none {
      ()
    } else {
      (table.footer(
        repeat: false,
        table.cell(colspan: columns, {
          set text(size: tokens.type.caption, fill: tokens.ink.grey_1, style: "italic")
          set par(leading: tokens.leading_extra.caption, justify: false)
          caption
        }),
      ),)
    }
    table(
      columns: columns_spec,
      align: left,
      stroke: none,
      table.hline(y: 0, stroke: tokens.rule.table_top),
      table.header(
        repeat: true,
        ..header.map(cell => text(weight: 600, size: tokens.type.table_head, cell)),
      ),
      table.hline(y: 1, stroke: tokens.rule.table_head),
      ..rows.flatten(),
      table.hline(y: rows.len() + 1, stroke: tokens.rule.table_bottom),
      ..captions,
    )
  },
)

#let preset-equation(body, caption: none) = block(
  above: tokens.space.after_block,
  below: tokens.space.after_figure,
  {
    align(center, body)
    if caption != none {
      block(above: tokens.space.after_caption, {
        set text(size: tokens.type.caption, fill: tokens.ink.grey_1, style: "italic")
        set par(leading: tokens.leading_extra.caption, justify: false)
        caption
      })
    }
  },
)

#let preset-note(note) = block(
  above: tokens.space.after_caption,
  below: tokens.space.after_block,
  {
    set text(size: tokens.type.note, fill: tokens.ink.grey_1, style: "italic")
    set par(leading: tokens.leading_extra.note, justify: false)
    note
  },
)

// D5: description and provenance share one centred caption block. A line break
// separates them; the size, alignment and centre are the caption's, never a
// separate note. Credits remain a separate left-aligned line at credit size.
#let preset-figure-caption(caption, note: none) = block(width: 100%, align(tokens.figure.caption_align, {
  set par(justify: false)
  set par(leading: tokens.leading_extra.caption)
  set text(size: tokens.type.caption, fill: tokens.ink.grey_1, style: "italic")
  caption
  if note != none {
    linebreak()
    note
  }
}))

#let preset-chart(figure, caption: none, note: none) = block(
  above: tokens.space.after_block,
  below: tokens.space.after_figure,
  breakable: false,
  {
    block(width: 100%, align(center, figure))
    if caption != none {
      block(above: tokens.space.after_caption, preset-figure-caption(caption, note: note))
    } else if note != none {
      preset-note(note)
    }
  },
)

#let preset-diagram(figure, caption: none, note: none) = preset-chart(figure, caption: caption, note: note)

// One image unit: image, then its centred caption, then its left credit.
// Used by the side branch; the full path below keeps its historical structure.
#let illustration-unit(figure, caption: none, credit: none, note: none) = {
  figure
  if caption != none {
    block(above: tokens.space.after_caption, preset-figure-caption(caption, note: note))
  } else if note != none {
    preset-note(note)
  }
  if credit != none {
    block(above: tokens.space.after_caption, {
      set text(size: tokens.type.credit, fill: tokens.ink.grey_1)
      credit
    })
  }
}

// A consumed companion renders through the same prose preset it would use in
// normal flow, including its role label and note.
#let companion-content(companion) = {
  let kind = companion.type
  if kind == "definition" {
    preset-definition(companion.term, companion.definition)
  } else if kind == "list" {
    preset-list(companion.items, ordered: companion.ordered)
  } else if kind == "example" {
    preset-example(title: if "title" in companion { companion.title } else { none }, companion.text)
  } else if kind == "case" {
    preset-case(title: if "title" in companion { companion.title } else { none }, companion.text)
  } else if kind == "assessment" {
    preset-assessment(title: if "title" in companion { companion.title } else { none }, companion.text)
  } else if kind == "quote" {
    preset-quote(companion.text, attribution: if "attribution" in companion { companion.attribution } else { none })
  } else if kind == "lead" {
    preset-lead(companion.text)
  } else {
    preset-paragraph(companion.text)
  }
  if "note" in companion {
    preset-note(companion.note)
  }
}

#let preset-illustration(
  figure,
  caption: none,
  credit: none,
  composition: "full",
  companions: (),
  companion: none,
  note: none,
) = {
  // The legacy single `companion` stays compatible; an authored group is
  // ordered and each block keeps its own prose preset.
  let group = if companions.len() > 0 {
    companions
  } else if companion != none {
    (companion,)
  } else {
    ()
  }
  if composition == "full" or composition == "centred" {
    block(
      above: tokens.space.after_block,
      below: tokens.space.after_figure,
      breakable: false,
      {
        block(width: 100%, align(center, figure))
        if caption != none {
          block(above: tokens.space.after_caption, preset-figure-caption(caption, note: note))
        } else if note != none {
          preset-note(note)
        }
        if credit != none {
          block(above: tokens.space.after_caption, {
            set text(size: tokens.type.credit, fill: tokens.ink.grey_1)
            credit
          })
        }
      },
    )
  } else {
    block(
      above: tokens.space.after_block,
      below: tokens.space.after_figure,
      width: 100%,
      breakable: false,
      {
        let image-column = illustration-unit(figure, caption: caption, credit: credit, note: note)
        let prose-column = { for item in group { item } }
        if composition == "side-left" {
          grid(
            columns: (tokens.measure.body * tokens.measure.side_fraction, 1fr),
            column-gutter: tokens.space.side_gutter,
            image-column,
            prose-column,
          )
        } else {
          grid(
            columns: (1fr, tokens.measure.body * tokens.measure.side_fraction),
            column-gutter: tokens.space.side_gutter,
            prose-column,
            image-column,
          )
        }
      },
    )
  }
}

#let preset-unresolved(note) = block(
  above: tokens.space.before_role,
  below: tokens.space.after_block,
  {
    set text(size: tokens.type.note, fill: tokens.ink.grey_1, style: "italic")
    set par(leading: tokens.leading_extra.note, justify: false)
    note
  },
)
