// Body-page compositions that are not block presets: the authored chapter
// column container and the width a visual takes in its container.
//
// A chapter opens at the full measure; when `section.layout.columns` is 2 the
// chapter heading and standfirst stay full measure and the block flow — its own
// blocks and every descendant section — runs in two equal columns that continue
// across pages (A2). A visual inside a column takes that column's measure: a
// plate, a centred figure and a chart all size to the column, and their captions
// centre in it. On a single-column page `centred` keeps the figure-width token
// and `full` the plate token.

#import "/typst/theme.typ": tokens

#let section-columns(body) = columns(2, gutter: tokens.space.side_gutter, body)

#let block-width(column: false) = if column {
  tokens.measure.column
} else {
  tokens.measure.plate
}

#let illustration-width(composition, column: false) = if column {
  100%
} else if composition == "centred" {
  tokens.measure.figure_width
} else {
  100%
}
