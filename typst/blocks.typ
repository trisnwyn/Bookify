// Block presets: one function per manuscript block type, tokens only.

#import "theme.typ": tokens, fonts

#let role-label(role, body) = block(
  above: tokens.space.before_role,
  below: tokens.space.after_block,
  {
    set text(size: tokens.type.small, fill: tokens.role.at(role), weight: 600)
    body
  },
)

#let preset-paragraph(body) = block(
  below: tokens.space.after_block,
  body,
)

#let preset-lead(body) = block(
  below: tokens.space.after_lead,
  {
    set text(size: tokens.type.lead, fill: tokens.ink.grey_1)
    set par(leading: tokens.leading.lead, justify: false)
    body
  },
)

#let preset-quote(body, attribution: none) = block(
  above: tokens.space.before_heading,
  below: tokens.space.after_block,
  {
    set text(size: tokens.type.lead, style: "italic")
    set par(leading: tokens.leading.lead, justify: false)
    body
    if attribution != none {
      linebreak()
      set text(size: tokens.type.small, fill: tokens.ink.grey_1, style: "normal")
      [— #attribution]
    }
  },
)

#let preset-definition(term, definition) = {
  role-label("definition", term)
  block(below: tokens.space.after_block, definition)
}

#let preset-example(title: none, body) = {
  role-label("example", if title != none { title } else { "Example" })
  block(below: tokens.space.after_block, body)
}

#let preset-case(title: none, body) = {
  role-label("case", if title != none { title } else { "Case" })
  block(below: tokens.space.after_block, body)
}

#let preset-assessment(title: none, body) = {
  role-label("assessment", if title != none { title } else { "Assessment" })
  block(below: tokens.space.after_block, body)
}

#let preset-list(items, ordered: false) = block(
  below: tokens.space.after_block,
  {
    if ordered { enum(..items) } else { list(..items) }
  },
)

#let preset-table(header, rows, caption: none, widths: none) = block(
  above: tokens.space.after_block,
  below: tokens.space.after_figure,
  {
    set text(size: tokens.type.table)
    let columns = header.len()
    let columns_spec = if widths == none { range(columns).map(_ => 1fr) } else { widths.map(w => w * 1fr) }
    table(
      columns: columns_spec,
      align: left,
      stroke: none,
      table.hline(y: 0, stroke: tokens.rule.table_top),
      table.hline(y: 1, stroke: tokens.rule.table_head),
      ..header.map(cell => text(weight: 600, size: tokens.type.table_head, cell)),
      ..rows.flatten(),
      table.hline(y: rows.len() + 1, stroke: tokens.rule.table_bottom),
    )
    if caption != none {
      block(above: tokens.space.after_caption, {
        set text(size: tokens.type.caption, fill: tokens.ink.grey_1, style: "italic")
        caption
      })
    }
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
        caption
      })
    }
  },
)

#let preset-note(note) = block(
  above: tokens.space.after_caption,
  below: tokens.space.after_block,
  {
    set text(size: tokens.type.small, fill: tokens.ink.grey_1, style: "italic")
    note
  },
)

#let preset-figure-caption(caption) = block(width: 100%, align(tokens.figure.caption_align, {
  set par(justify: false)
  set text(size: tokens.type.caption, fill: tokens.ink.grey_1, style: "italic")
  caption
}))

#let preset-chart(figure, caption: none, note: none) = block(
  above: tokens.space.after_block,
  below: tokens.space.after_figure,
  breakable: false,
  {
    block(width: 100%, align(center, figure))
    if caption != none {
      block(above: tokens.space.after_caption, preset-figure-caption(caption))
    }
    if note != none {
      preset-note(note)
    }
  },
)

#let preset-diagram(figure, caption: none, note: none) = preset-chart(figure, caption: caption, note: note)

// One image unit: image, then its centred caption, then its left credit.
// Used by the side branch; the full path below keeps its historical structure.
#let illustration-unit(figure, caption: none, credit: none) = {
  figure
  if caption != none {
    block(above: tokens.space.after_caption, preset-figure-caption(caption))
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
  companion: none,
) = {
  if composition == "full" {
    block(
      above: tokens.space.after_block,
      below: tokens.space.after_figure,
      breakable: false,
      {
        block(width: 100%, align(center, figure))
        if caption != none {
          block(above: tokens.space.after_caption, preset-figure-caption(caption))
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
        let image-column = illustration-unit(figure, caption: caption, credit: credit)
        if composition == "side-left" {
          grid(
            columns: (tokens.measure.body * tokens.measure.side_fraction, 1fr),
            column-gutter: tokens.space.side_gutter,
            image-column,
            companion,
          )
        } else {
          grid(
            columns: (1fr, tokens.measure.body * tokens.measure.side_fraction),
            column-gutter: tokens.space.side_gutter,
            companion,
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
    set text(size: tokens.type.small, fill: tokens.ink.grey_1, style: "italic")
    note
  },
)
