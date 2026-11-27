// Block presets: one function per manuscript block type, tokens only.
//
// Space semantics are deliberate: `space.between_paragraphs` is prose rhythm
// (line pitch + 5.4 pt), while heading/role/lead/note gaps stay absolute.

#import "theme.typ": tokens, fonts

#let role-label(role, body) = block(
  above: tokens.space.before_role,
  below: tokens.space.after_block,
  sticky: true,
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

#let _response-label(label) = if label != none {
  block(below: tokens.space.after_block, {
    set text(size: tokens.type.credit, fill: tokens.ink.grey_2, style: "italic")
    label
  })
}

#let _write-lines(count, style: "dotted") = {
  let dash = if style == "ruled" { none } else { "dotted" }
  let stroke = (paint: tokens.ink.grey_2, thickness: tokens.workspace.line_stroke, dash: dash)
  for _ in range(count) {
    block(width: 100%, above: tokens.workspace.line_pitch, below: tokens.cover.origin, line(length: 100%, stroke: stroke))
  }
}

#let _render-response-space(spec) = {
  let kind = spec.kind
  let label = spec.at("label", default: none)
  block(width: 100%, above: tokens.space.after_caption, below: tokens.space.after_block, {
    if kind == "lines" {
      _response-label(label)
      let count = spec.at("lines", default: 4)
      let style = spec.at("lineStyle", default: "dotted")
      _write-lines(count, style: style)
    } else if kind == "blank" {
      let h = spec.at("heightPt", default: 110) * tokens.workspace.unit_pt
      block(
        width: 100%,
        height: h,
        inset: tokens.workspace.box_pad,
        radius: tokens.workspace.box_radius,
        stroke: tokens.workspace.box_stroke + tokens.ink.grey_3,
        _response-label(label),
      )
    } else if kind == "grid" {
      let h = spec.at("heightPt", default: 120) * tokens.workspace.unit_pt
      let step = tokens.workspace.grid_step
      let dot = tokens.workspace.dot_radius
      let dot-pat = tiling(size: (step, step), place(center + horizon, circle(radius: dot, fill: tokens.ink.grey_3)))
      block(
        width: 100%,
        height: h,
        inset: tokens.workspace.box_pad,
        radius: tokens.workspace.box_radius,
        fill: dot-pat,
        stroke: tokens.workspace.box_stroke + tokens.ink.grey_3,
        _response-label(label),
      )
    } else if kind == "coordinate" {
      let h = spec.at("heightPt", default: 140) * tokens.workspace.unit_pt
      let step = tokens.workspace.grid_step
      let grid-pat = tiling(
        size: (step, step),
        rect(width: step, height: step, stroke: tokens.workspace.table_grid_stroke + tokens.ink.pale),
      )
      _response-label(label)
      block(
        width: 100%,
        height: h,
        inset: tokens.workspace.axis_pad,
        radius: tokens.workspace.box_radius,
        fill: grid-pat,
        stroke: tokens.workspace.box_stroke + tokens.ink.grey_3,
        {
          place(horizon, line(length: 100%, stroke: tokens.workspace.axis_stroke + tokens.ink.grey_1))
          place(center, line(angle: 90deg, length: 100%, stroke: tokens.workspace.axis_stroke + tokens.ink.grey_1))
        },
      )
    } else if kind == "choices" {
      let choices = spec.at("choices", default: ())
      let lines = spec.at("lines", default: 3)
      let style = spec.at("lineStyle", default: "dotted")
      for choice in choices {
        block(width: 100%, below: tokens.workspace.choice_gap, {
          set par(leading: tokens.leading_extra.body)
          box(
            width: tokens.workspace.checkbox_size,
            height: tokens.workspace.checkbox_size,
            stroke: tokens.workspace.axis_stroke + tokens.ink.grey_1,
            baseline: tokens.cover.inset,
          )
          h(tokens.workspace.checkbox_gap)
          choice
        })
      }
      if lines > 0 {
        block(above: tokens.space.after_caption, {
          _response-label(if label != none { label } else { "Reasoning / revision space:" })
          _write-lines(lines, style: style)
        })
      }
    } else if kind == "trace" {
      let cols = spec.at("traceColumns", default: ("Step", "State", "Scratch"))
      let rows = spec.at("rows", default: 5)
      _response-label(label)
      set text(size: tokens.type.table)
      table(
        columns: range(cols.len()).map(_ => 1fr),
        inset: (x: tokens.workspace.cell_inset_x, y: tokens.workspace.cell_inset_y),
        stroke: tokens.workspace.table_grid_stroke + tokens.ink.grey_3,
        table.header(
          repeat: true,
          ..cols.map(cell => text(weight: 600, size: tokens.type.table_head, cell)),
        ),
        ..range(rows * cols.len()).map(_ => []),
      )
    }
  })
}

#let preset-assessment(title: none, body, response_space: none) = {
  let heading-text = if title != none { title } else { "Assessment" }
  let compact = response_space != none and (
    (response_space.kind == "lines" and response_space.at("lines", default: 4) <= 6)
      or (response_space.kind in ("blank", "grid", "coordinate") and response_space.at("heightPt", default: 110) * tokens.workspace.unit_pt <= tokens.workspace.compact_height_max)
      or (response_space.kind == "choices" and response_space.at("choices", default: ()).len() <= 5)
      or (response_space.kind == "trace" and response_space.at("rows", default: 5) <= 7)
  )
  if compact {
    block(width: 100%, breakable: false, below: tokens.space.between_paragraphs, {
      role-label("assessment", heading-text)
      block(below: tokens.space.after_block, {
        set par(leading: tokens.leading_extra.body)
        body
      })
      _render-response-space(response_space)
    })
  } else {
    role-label("assessment", heading-text)
    block(
      sticky: response_space != none,
      below: if response_space != none { tokens.space.after_block } else { tokens.space.between_paragraphs },
      {
        set par(leading: tokens.leading_extra.body)
        body
      },
    )
    if response_space != none {
      _render-response-space(response_space)
    }
  }
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

#let _table-align(value) = if value == "right" {
  right
} else if value == "center" {
  center
} else {
  left
}

#let preset-table(header, rows, caption: none, widths: none, align: none, fill_space: false, extra_rows: 0) = block(
  width: 100%,
  above: tokens.space.after_block,
  below: tokens.space.after_figure,
  {
    set text(size: tokens.type.table)
    set par(leading: tokens.leading_extra.table)
    let columns = header.len()
    let columns_spec = if widths == none { range(columns).map(_ => 1fr) } else { widths.map(w => w * 1fr) }
    let align_spec = if align == none { left } else { align.map(_table-align) }
    let padded_rows = rows + range(extra_rows).map(_ => range(columns).map(_ => ""))
    let captions = if caption == none {
      ()
    } else {
      (table.footer(
        repeat: false,
        table.cell(colspan: columns, align: tokens.figure.caption_align, stroke: none, {
          block(width: 100%, std.align(tokens.figure.caption_align, {
            set text(size: tokens.type.caption, fill: tokens.ink.grey_1, style: "italic")
            set par(leading: tokens.leading_extra.caption, justify: false)
            caption
          }))
        }),
      ),)
    }
    let table_extra = if fill_space {
      (inset: (x: tokens.workspace.cell_inset_x, y: tokens.workspace.cell_inset_y))
    } else {
      (:)
    }
    let cell_stroke = if fill_space {
      tokens.workspace.table_grid_stroke + tokens.ink.grey_3
    } else {
      none
    }
    table(
      columns: columns_spec,
      align: align_spec,
      ..table_extra,
      stroke: cell_stroke,
      table.hline(y: 0, stroke: tokens.rule.table_top),
      table.header(
        repeat: true,
        ..header.map(cell => text(weight: 600, size: tokens.type.table_head, cell)),
      ),
      table.hline(y: 1, stroke: tokens.rule.table_head),
      ..padded_rows.flatten(),
      table.hline(y: padded_rows.len() + 1, stroke: tokens.rule.table_bottom),
      ..captions,
    )
  },
)

#let preset-equation(body, caption: none) = block(
  width: 100%,
  above: tokens.space.after_block,
  below: tokens.space.after_figure,
  breakable: false,
  {
    block(width: 100%, align(center, if body.func() == math.equation {
      math.equation(block: true, body.body)
    } else {
      math.equation(block: true, body)
    }))
    if caption != none {
      block(width: 100%, above: tokens.space.after_caption, {
        block(width: 100%, align(tokens.figure.caption_align, {
          set text(size: tokens.type.caption, fill: tokens.ink.grey_1, style: "italic")
          set par(leading: tokens.leading_extra.caption, justify: false)
          caption
        }))
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
  width: 100%,
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
      width: 100%,
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
