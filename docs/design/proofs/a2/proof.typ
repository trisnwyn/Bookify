// DISPOSABLE A2 LAYOUT PROOF. Not a product template.
// Composition reference: parsed pages A2 5-6 (two flowing text columns with an
// optional figure embedded in the right column; continuation on the next page).
// Values are imported from the live Bookify theme; no product file is modified.
#import "/typst/theme.typ": book_base, tokens, fonts, heading-below, ink_metrics
#import "/typst/blocks.typ": preset-paragraph, preset-standfirst, preset-chart

#set page(numbering: "1")
#show: book_base

// New fixed user rule: every heading is followed by at least one visible blank
// line. The value is one body line pitch (0.660 em + 8.63 pt = 15.30 pt),
// reserved as white space after the heading's descender and before the next
// line's ascender. Local to this disposable proof; the product theme is untouched.
#let blank-line = ink_metrics.line_box_em * tokens.type.body + tokens.leading_extra.body
#let heading-blank(size) = (
  ink_metrics.descent_em * size
  + (ink_metrics.ascent_em - ink_metrics.line_box_em) * tokens.type.lead
  + blank-line
  + tokens.space.heading_clearance
)

#let numbered-heading(level, body) = block(
  below: heading-blank(
    if level == 1 { tokens.type.h1 } else if level == 2 { tokens.type.h2 } else { tokens.type.h3 },
  ),
  heading(level: level, numbering: none, body),
)

// ---------------------------------------------------------------------------
// Neutral vector placeholder. No image file, no font, no data.
// ---------------------------------------------------------------------------
#let placeholder-figure() = block(width: 100%, {
  set par(leading: tokens.leading_extra.small, justify: false)
  block(width: 100%, below: tokens.space.after_caption, {
    set text(size: tokens.type.caption, weight: 600, fill: tokens.ink.grey_1)
    [VECTOR PLACEHOLDER · NO DATA]
  })
  block(width: 100%, height: 132pt, {
    // Three neutral guides, then the baseline.
    place(top + left, dy: 22pt, line(length: 100%, stroke: tokens.rule.cover_index + tokens.ink.pale))
    place(top + left, dy: 56pt, line(length: 100%, stroke: tokens.rule.cover_index + tokens.ink.pale))
    place(top + left, dy: 90pt, line(length: 100%, stroke: tokens.rule.cover_index + tokens.ink.pale))
    place(bottom + left, line(length: 100%, stroke: tokens.rule.figure_stroke))
    align(bottom, grid(
      columns: (1fr,) * 6,
      column-gutter: 6pt,
      align: bottom,
      ..(36pt, 62pt, 50pt, 96pt, 74pt, 84pt).map(height => rect(
        width: 100%,
        height: height,
        fill: tokens.ink.grey_3,
      )),
    ))
  })
  grid(
    columns: (1fr,) * 6,
    column-gutter: 6pt,
    align: center,
    ..("A", "B", "C", "D", "E", "F").map(label => text(
      size: tokens.type.small,
      fill: tokens.ink.grey_2,
      label,
    )),
  )
})

// ---------------------------------------------------------------------------
// Public-safe sample prose. Layout filler only; no factual content.
// ---------------------------------------------------------------------------
#let sample = (
  "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer posuere erat a ante venenatis dapibus posuere velit aliquet. Cras mattis consectetur purus sit amet fermentum. Donec ullamcorper nulla non metus auctor fringilla, sed posuere consectetur est at lobortis.",
  "Maecenas faucibus mollis interdum. Nullam quis risus eget urna mollis ornare vel eu leo. Aenean lacinia bibendum nulla sed consectetur. Vestibulum id ligula porta felis euismod semper, cum sociis natoque penatibus et magnis dis parturient montes.",
  "Curabitur blandit tempus porttitor. Etiam porta sem malesuada magna mollis euismod. Donec sed odio dui. Morbi leo risus, porta ac consectetur ac, vestibulum at eros. Praesent commodo cursus magna, vel scelerisque nisl consectetur et.",
  "Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentum nibh, ut fermentum massa justo sit amet risus. Nullam id dolor id nibh ultricies vehicula ut id elit. Duis mollis, est non commodo luctus, nisi erat porttitor ligula.",
  "Vivamus sagittis lacus vel augue laoreet rutrum faucibus dolor auctor. Aenean eu leo quam. Pellentesque ornare sem lacinia quam venenatis vestibulum. Sed posuere consectetur est at lobortis. Maecenas sed diam eget risus varius blandit sit amet non magna.",
  "Nullam quis risus eget urna mollis ornare vel eu leo. Cras justo odio, dapibus ac facilisis in, egestas eget quam. Donec id elit non mi porta gravida at eget metus. Nulla vitae elit libero, a pharetra augue. Integer posuere erat a ante venenatis dapibus.",
  "Etiam porta sem malesuada magna mollis euismod. Donec ullamcorper nulla non metus auctor fringilla. Aenean lacinia bibendum nulla sed consectetur. Cras mattis consectetur purus sit amet fermentum. Sed posuere consectetur est at lobortis.",
  "Donec sed odio dui. Cras justo odio, dapibus ac facilisis in, egestas eget quam. Nullam id dolor id nibh ultricies vehicula ut id elit. Maecenas faucibus mollis interdum. Integer posuere erat a ante venenatis dapibus posuere velit aliquet.",
  "Praesent commodo cursus magna, vel scelerisque nisl consectetur et. Vestibulum id ligula porta felis euismod semper. Duis mollis, est non commodo luctus, nisi erat porttitor ligula. Aenean eu leo quam. Pellentesque ornare sem lacinia quam venenatis vestibulum.",
  "Morbi leo risus, porta ac consectetur ac, vestibulum at eros. Nullam quis risus eget urna mollis ornare vel eu leo. Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentum nibh. Nulla vitae elit libero, a pharetra augue.",
  "Aenean lacinia bibendum nulla sed consectetur. Curabitur blandit tempus porttitor. Cum sociis natoque penatibus et magnis dis parturient montes. Donec id elit non mi porta gravida at eget metus. Vivamus sagittis lacus vel augue laoreet rutrum faucibus dolor auctor.",
  "Sed posuere consectetur est at lobortis. Etiam porta sem malesuada magna mollis euismod. Integer posuere erat a ante venenatis dapibus posuere velit aliquet. Cras mattis consectetur purus sit amet fermentum. Donec ullamcorper nulla non metus auctor fringilla.",
  "Vestibulum id ligula porta felis euismod semper. Cras mattis consectetur purus sit amet fermentum. Donec sed odio dui. Morbi leo risus, porta ac consectetur ac, vestibulum at eros. Nulla vitae elit libero, a pharetra augue.",
  "Integer posuere erat a ante venenatis dapibus posuere velit aliquet. Aenean lacinia bibendum nulla sed consectetur. Maecenas faucibus mollis interdum. Sed posuere consectetur est at lobortis. Cras justo odio, dapibus ac facilisis in.",
  "Duis mollis, est non commodo luctus, nisi erat porttitor ligula. Cum sociis natoque penatibus et magnis dis parturient montes. Etiam porta sem malesuada magna mollis euismod. Donec ullamcorper nulla non metus auctor fringilla.",
  "Curabitur blandit tempus porttitor. Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentum nibh. Aenean eu leo quam. Pellentesque ornare sem lacinia quam venenatis vestibulum. Vivamus sagittis lacus vel augue laoreet rutrum faucibus dolor auctor.",
  "Nullam quis risus eget urna mollis ornare vel eu leo. Donec id elit non mi porta gravida at eget metus. Praesent commodo cursus magna, vel scelerisque nisl consectetur et. Vestibulum id ligula porta felis euismod semper.",
  "Donec sed odio dui. Morbi leo risus, porta ac consectetur ac, vestibulum at eros. Integer posuere erat a ante venenatis dapibus posuere velit aliquet. Duis mollis, est non commodo luctus, nisi erat porttitor ligula.",
)

// ---------------------------------------------------------------------------
// Page 1 opening: A2 annotation, numbered chapter title, standfirst. Then the
// two columns. Every heading carries its full numerical path; no level skipped.
// ---------------------------------------------------------------------------
#block(below: tokens.space.after_block, {
  set text(size: tokens.type.small, fill: tokens.ink.grey_1)
  [A2 · COMPOSITION PROOF]
})
#numbered-heading(1)[Chapter 2: Two-Column Flow]
#preset-standfirst[
  A disposable layout proof: sample prose only, plus a neutral vector
  placeholder.
]

#columns(2, gutter: tokens.space.side_gutter, {
  numbered-heading(2)[2. Example 1]
  preset-paragraph(sample.at(0))
  preset-paragraph(sample.at(1))
  preset-paragraph(sample.at(2))
  preset-paragraph(sample.at(3))

  numbered-heading(3)[2.1 Example 2]
  preset-paragraph(sample.at(4))
  preset-paragraph(sample.at(5))
  preset-paragraph(sample.at(6))

  // Terminal branches: run-in labels at body size, bold face only.
  preset-paragraph([*2.1 a)* #sample.at(7)])
  preset-paragraph([*2.1 b)* #sample.at(8)])
  preset-paragraph([*2.1 c)* #sample.at(9)])

  preset-paragraph(sample.at(10))

  preset-chart(placeholder-figure(), caption: [
    Figure A2.1. Neutral vector placeholder; no data.
  ])

  preset-paragraph(sample.at(11))
  preset-paragraph(sample.at(12))

  // The same branch continues on page 2.
  numbered-heading(3)[2.1.1 Continuing Branch]
  preset-paragraph(sample.at(13))
  preset-paragraph(sample.at(14))
  preset-paragraph(sample.at(15))

  numbered-heading(3)[2.1.1.1 Deeper Branch]
  preset-paragraph(sample.at(16))
  preset-paragraph(sample.at(17))
  preset-paragraph(sample.at(0))
  preset-paragraph(sample.at(1))
  preset-paragraph(sample.at(2))
  preset-paragraph(sample.at(3))
  preset-paragraph(sample.at(4))
  preset-paragraph(sample.at(5))
  preset-paragraph(sample.at(6))
  preset-paragraph(sample.at(7))
  preset-paragraph(sample.at(8))
  preset-paragraph(sample.at(9))
})
