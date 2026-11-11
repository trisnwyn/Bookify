#import "/typst/theme.typ": book_base, tokens
#import "/typst/blocks.typ": *
#import "/typst/cetz/diagram.typ": diagram

#let doc = json(sys.inputs.data)

#set page(numbering: "1")
#show: book_base

// Cover
#align(center)[
  #v(tokens.space.page_margin * 4)
  #if "institution" in doc.metadata [
    #text(size: tokens.type.small, fill: tokens.ink.grey_1, doc.metadata.institution)
    #v(tokens.space.after_lead)
  ]
  #text(size: tokens.type.h1, weight: 500, doc.metadata.title)
  #if "subtitle" in doc.metadata [
    #v(tokens.space.after_block)
    #text(size: tokens.type.lead, style: "italic", doc.metadata.subtitle)
  ]
]
#pagebreak()

#outline(title: [Contents], depth: 1)
#pagebreak()

#for (section-index, section) in doc.sections.enumerate() [
  #if section-index > 0 [
    #pagebreak()
  ]
  #if section.kicker != none [
    #text(size: tokens.type.small, fill: tokens.ink.grey_1, section.kicker)
    #parbreak()
  ]
  #heading(level: 1, section.title)
  #if section.standfirst != none [
    #preset-lead(section.standfirst)
  ]
  #for block in section.blocks [
    #if block.type == "paragraph" [
      #preset-paragraph(block.text)
    ]
    #if block.type == "lead" [
      #preset-lead(block.text)
    ]
    #if block.type == "quote" [
      #preset-quote(block.text, attribution: if "attribution" in block { block.attribution } else { none })
    ]
    #if block.type == "definition" [
      #preset-definition(block.term, block.definition)
    ]
    #if block.type == "example" [
      #preset-example(title: if "title" in block { block.title } else { none }, block.text)
    ]
    #if block.type == "case" [
      #preset-case(title: if "title" in block { block.title } else { none }, block.text)
    ]
    #if block.type == "assessment" [
      #preset-assessment(title: if "title" in block { block.title } else { none }, block.text)
    ]
    #if block.type == "list" [
      #preset-list(block.items, ordered: block.ordered)
    ]
    #if block.type == "table" [
      #preset-table(block.header, block.rows, caption: block.caption, widths: block.widths)
    ]
    #if block.type == "equation" [
      #preset-equation(eval(block.typst, mode: "math"), caption: block.caption)
    ]
    #if block.type == "chart" [
      #preset-chart(image(block.path, width: 72%), caption: block.caption, note: if "note" in block { block.note } else { none })
    ]
    #if block.type == "diagram" [
      #preset-diagram(diagram(block.spec, tokens.measure.figure_width), caption: block.caption, note: if "note" in block { block.note } else { none })
    ]
    #if block.type not in ("chart", "diagram", "unresolved", "illustration") and "note" in block [
      #preset-note(block.note)
    ]
    #if block.type == "unresolved" [
      #preset-unresolved(block.note)
    ]
    #if block.type == "illustration" [
      #if "pagebreak" in block and block.pagebreak [
        #pagebreak()
      ]
      #let composition = if "composition" in block { block.composition } else { "full" }
      #let companion = if "companion" in block { companion-content(block.companion) } else { none }
      #preset-illustration(
        image(block.path, width: if composition == "full" { 88% } else { 100% }),
        caption: block.caption,
        credit: block.credit,
        composition: composition,
        companion: companion,
      )
    ]
  ]
]
