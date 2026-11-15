// Bookify Phase 2 public-safe source fixture (Task 64).
//
// This is authored synthetic source material, not a lecture, book, dataset or
// external document. Every example and number is invented for the exercise.
// Page 6 is a deliberately unreadable image-only plate: it has no text layer,
// no label and no OCR. Do not invent a label or measurement for it.
//
// The plate is embedded as PNG bytes so the fixture is self-contained and the
// image-only page is a real raster image rather than painted vector shapes.
// The bytes were generated from a neutral geometric drawing by the fixture
// author; they contain no external imagery.
#let plate = bytes((137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82,0,0,0,72,0,0,0,48,8,0,0,0,0,151,247,99,55,0,0,1,9,73,68,65,84,120,156,237,215,187,13,194,48,16,128,225,63,40,35,164,98,50,139,25,92,184,140,24,0,165,76,145,25,144,71,99,12,10,228,188,252,138,229,19,32,132,171,83,138,79,119,23,159,157,52,15,100,214,73,200,145,131,90,160,175,86,6,225,140,96,168,50,122,190,178,217,181,144,118,65,43,195,212,65,26,38,9,72,175,152,35,144,2,192,38,211,201,67,10,140,11,214,214,158,201,65,202,184,200,128,154,37,159,201,64,139,3,96,156,164,125,38,13,109,29,39,133,210,73,67,123,7,140,178,17,38,5,249,14,24,213,133,153,242,17,137,57,111,24,218,80,101,96,212,231,50,250,67,121,200,142,161,167,163,119,156,184,181,217,217,183,37,188,150,102,180,29,145,139,11,238,165,78,188,52,221,5,106,139,87,22,133,52,147,223,165,132,19,157,254,9,176,187,49,73,57,233,215,191,205,41,233,100,206,108,59,31,254,99,224,34,41,128,176,209,235,168,16,58,66,188,150,240,135,22,0,154,115,249,62,244,161,232,245,80,156,81,21,179,234,81,165,35,221,236,250,47,109,185,140,154,223,253,169,121,2,61,9,53,207,78,185,192,172,0,0,0,0,73,69,78,68,174,66,96,130))

#set page(paper: "a4", margin: (x: 58pt, y: 56pt), numbering: none)
#set text(font: "Spectral", size: 10.8pt, lang: "en")
#set par(justify: true, leading: 0.72em)
#set heading(numbering: none)
#show heading.where(level: 1): set text(size: 15pt, weight: "semibold")
#show heading.where(level: 1): set block(above: 0pt, below: 10pt)
#show heading.where(level: 2): set text(size: 11.5pt, weight: "semibold")

#text(size: 21pt, weight: "semibold")[Notes on Reading a Sample]
#v(3pt)
#text(size: 10.5pt, style: "italic")[A synthetic source for the Bookify agent-skill fixture]
#v(12pt)

= A sample arrives

These notes describe one small synthetic case. They are written for a reading
exercise, not as a report of an observation.

A sample is a bounded piece of material selected for inspection. In this case,
a sample arrives with two labels. One label gives its place in a sequence; the
other gives a short name. The names disagree. Read alone, either label looks
like an error. Read in order, one label was written before the sample moved and
the other after. The difference is a change of place, not a contradiction.

#block(inset: (left: 10pt, top: 3pt, bottom: 3pt), stroke: (left: 1.2pt + rgb("#8d8d8d")))[
  *Case note.* The origin of the sample is not recorded. It remains unknown.
  These notes do not supply it.
]

The notes also turn to the record, to three levels of reading, and to the
point where the evidence stops.

#pagebreak()

= The record

A record keeps four fields together: label, time, place, and status. The status
says how firm the entry is.

#table(
  columns: (0.8fr, 1.35fr, 1.65fr),
  inset: 6pt,
  stroke: 0.5pt,
  [*Field*], [*Question*], [*Example entry (synthetic)*],
  [label], [What is it called?], [Two labels disagree],
  [time], [When was it recorded?], [Before the move; after the move],
  [place], [Where was it recorded?], [Shelf A; shelf B],
  [status], [How firm is the entry?], [Observed; unresolved origin],
)

Every entry in the table is invented for this exercise. The table is a
checklist, not a measurement.

If a field cannot be filled, write unresolved. An empty field is not a zero and
not a guess. The origin in the case stays unresolved because no record supplies
it.

#pagebreak()

= Three levels of reading

Three levels keep a description honest.

#block(inset: (left: 12pt))[
  *Detail.* What is visible without interpretation.\
  *Setting.* What the detail means in this place and sequence.\
  *Warrant.* The evidence that supports the reading.
]

The three levels answer different questions: What is here? What does it mean
here? Why should the reading be accepted?

A reading can be correct at one level and unsupported at another. A visible
detail is not yet a setting; a setting is not yet a warrant. In the case of the
two labels, the labels are details. The order of the labels is part of the
setting. The recorded order is the warrant for reading them as a sequence rather
than a contradiction.

These notes use the three terms throughout.

#pagebreak()

= Comparing counts

The record can be summarised as counts. The counts below are synthetic: they
exist to show a comparison, not to report an observation.

#table(
  columns: (1.6fr, 0.7fr, 0.7fr, 0.7fr),
  inset: 6pt,
  stroke: 0.5pt,
  [*Category*], [*First pass*], [*Second pass*], [*Change*],
  [Detail recorded], [12], [15], [+3],
  [Setting recorded], [7], [7], [0],
  [Warrant recorded], [4], [6], [+2],
)

The totals are small and invented. They show a relationship the prose can
state: a longer list of details does not by itself add warrants. The second pass
added details and warrants, but the setting count did not change.

Read the table as a question about coverage, not as evidence that the sample is
better understood. A count records how many entries were made, not how strong
they are.

#pagebreak()

= When the evidence stops

The unlabelled plate that closes these notes is part of the sample set, but
its content is not readable in this source. It is an image with no text layer.
No label, date, place or warrant is assigned to it. It remains unresolved.

This is not a gap to fill with a plausible name. The record marks the plate
unresolved, and these notes do not borrow a label from another page.

#block(inset: (left: 12pt, top: 6pt, bottom: 6pt), stroke: (left: 1.5pt + rgb("#7d7d7d")))[
  _A claim should carry its evidence._\
  #v(2pt)
  — Synthetic source note
]

A short check: which of the three levels can be recorded for the plate, and
which cannot? Answer using the vocabulary of the section on three levels.

The notes end where they began: keep the visible detail, its setting and its
warrant together, and mark the place where the evidence stops.

#pagebreak()

#image(plate, format: "png", width: 78%)
