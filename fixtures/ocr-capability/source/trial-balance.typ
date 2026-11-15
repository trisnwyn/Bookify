// Synthetic raster source: trial balance image for the OCR capability fixture.
// Authored for this repository; no third-party content.
// Horizontal rules only, as in the cash journal: vertical rules are OCR noise
// and are not part of the capability being proved.
#set page(width: 17cm, height: auto, margin: 7mm)
#set text(font: "Spectral", size: 11pt, fill: rgb("#111111"))
#set par(leading: 0.55em)

#align(center)[
  #text(size: 12.5pt, weight: "semibold")[Trial balance as at 31 March 2026]
]

#v(2.5mm)

#table(
  columns: (1fr, 3.4cm, 3.4cm),
  align: (left, right, right),
  stroke: none,
  inset: (x: 5pt, y: 5pt),
  table.hline(stroke: 0.8pt + rgb("#111111")),
  table.header(
    [*Account*], [*Debit*], [*Credit*],
  ),
  table.hline(stroke: 0.4pt + rgb("#777777")),
  [Cash at bank], [12,480.00], [],
  [Accounts receivable], [8,215.50], [],
  [Office equipment], [24,000.00], [],
  [Accounts payable], [], [9,340.25],
  [Owner's capital], [], [31,205.75],
  [Loan payable], [], [6,000.00],
  [Revenue], [], [18,939.50],
  [Rent expense], [4,120.00], [],
  [Wages expense], [16,670.00], [],
  table.hline(stroke: 0.8pt + rgb("#111111")),
  [*Totals*], [*65,485.50*], [*65,485.50*],
)
