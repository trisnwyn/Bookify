// Synthetic raster source: cash receipts journal image for the OCR capability
// fixture. Authored for this repository; no third-party content.
// Horizontal rules only: vertical rules are known OCR noise on a clean page and
// would make the "clean image page" proof depend on a table-border artefact.
#set page(width: 17cm, height: auto, margin: 7mm)
#set text(font: "Spectral", size: 11pt, fill: rgb("#111111"))
#set par(leading: 0.55em)

#align(center)[
  #text(size: 12.5pt, weight: "semibold")[Cash receipts journal --- April 2026]
]

#v(2.5mm)

#table(
  columns: (2.4cm, 4.4cm, 3.4cm, 3.6cm),
  align: (left, left, left, right),
  stroke: none,
  inset: (x: 5pt, y: 5pt),
  table.hline(stroke: 0.8pt + rgb("#111111")),
  table.header(
    [*Date*], [*Received from*], [*Receipt no.*], [*Amount*],
  ),
  table.hline(stroke: 0.4pt + rgb("#777777")),
  [02 Apr], [R. Okafor], [CR-1001], [2,450.00],
  [05 Apr], [L. Nguyen], [CR-1002], [1,980.50],
  [09 Apr], [M. Silva], [CR-1003], [3,215.75],
  [14 Apr], [A. Haddad], [CR-1004], [875.00],
  [21 Apr], [S. Weber], [CR-1005], [4,120.25],
  [28 Apr], [T. Ito], [CR-1006], [2,640.00],
  table.hline(stroke: 0.8pt + rgb("#111111")),
  [*Total*], [], [], [*15,281.50*],
)
