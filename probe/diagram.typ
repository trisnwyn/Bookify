// Task 2 probe: CeTZ resolves from the vendored package path, offline.
#import "@preview/cetz:0.5.3"

#set document(title: "Bookify CeTZ probe")
#set page(width: 12cm, height: 6.5cm, margin: 0.6cm)
#set text(font: "Spectral", size: 9pt)
#show math.equation: set text(font: "STIX Two Math")

#cetz.canvas({
  import cetz.draw: *
  let step(x, y, w, h, label, sub) = {
    rect((x, y), (x + w, y + h), radius: 2pt)
    content((x + w / 2, y + h - 0.28), align(center, text(weight: "semibold", label)))
    if sub != none {
      content((x + w / 2, y + 0.22), align(center, text(size: 7pt, fill: luma(120), sub)))
    }
  }

  step(0, 1.6, 2.1, 0.9, "Plan", "definition")
  step(2.9, 1.6, 2.1, 0.9, "Act", "evidence")
  step(5.8, 1.6, 2.1, 0.9, "Review", "decision")

  line((2.1, 2.05), (2.9, 2.05), mark: (end: ">", fill: black))
  line((5.0, 2.05), (5.8, 2.05), mark: (end: ">", fill: black))
  line((6.85, 1.6), (6.85, 0.55), (1.05, 0.55), (1.05, 1.6),
    mark: (end: ">", fill: black), stroke: (dash: "dashed", paint: luma(110)))
  content((4.0, 0.38), text(size: 7pt, fill: luma(110), "feedback"))
})
