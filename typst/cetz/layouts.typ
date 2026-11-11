// CeTZ diagram layouts. Pure functions of stored geometry and theme tokens.
// No layout decision is made in Python, and no label is clipped silently.
#import "@preview/cetz:0.5.3"
#import "/typst/theme.typ": tokens

#let pt-per-cm = 28.3465

// An omitted edge kind is an arrow; an explicit "line" stays a line.
// The catalogue build passes the raw diagram mapping, so this default is required.
#let edge-kind(edge) = edge.at("kind", default: "arrow")

#let is-cjk(codepoint) = (
  (0x2E80 <= codepoint and codepoint <= 0x9FFF)
    or (0xF900 <= codepoint and codepoint <= 0xFAFF)
    or (0xFF00 <= codepoint and codepoint <= 0xFFEF)
)

#let breakable-units(label) = {
  let units = ()
  for word in label.split(" ") {
    if word == "" { continue }
    let has-cjk = false
    for cluster in word.clusters() {
      if is-cjk(cluster.to-unicode()) { has-cjk = true }
    }
    if has-cjk {
      let current = ""
      for cluster in word.clusters() {
        if is-cjk(cluster.to-unicode()) {
          if current != "" {
            units.push(current)
            current = ""
          }
          units.push(cluster)
        } else {
          current += cluster
        }
      }
      if current != "" { units.push(current) }
    } else {
      units.push(word)
    }
  }
  units
}

#let label-fits(label, width, height, size) = {
  let inner-w = width - 2 * tokens.diagram.label_pad
  let inner-h = height - 2 * tokens.diagram.label_pad
  let zero = 0 * tokens.diagram.label_pad
  if inner-w <= zero or inner-h <= zero { return false }
  for unit in breakable-units(label) {
    if measure(text(size: size, unit)).width > inner-w { return false }
  }
  measure(block(width: inner-w, text(size: size, label))).height <= inner-h
}

// Deterministic stepwise fitting: 0.5pt down from the token start, floor 5.5pt.
#let fit-size(label, width, height, start: tokens.diagram.label, floor: tokens.diagram.label_floor, step: tokens.diagram.label_step) = {
  let size = start
  while size >= floor {
    if label-fits(label, width, height, size) { return size }
    size = size - step
  }
  panic("diagram label does not fit at the " + repr(tokens.diagram.label_floor) + " floor: " + label)
}

// Measurement needs a context; build the fitted text in one.
#let fitted(label, width, height, start: tokens.diagram.label, weight: "regular", style: "normal", fill: tokens.ink.text) = context {
  let size = fit-size(label, width, height, start: start)
  let inner-w = width - 2 * tokens.diagram.label_pad
  let body = text(size: size, weight: weight, style: style, fill: fill, label)
  if measure(body).width <= inner-w {
    align(center, body)
  } else {
    block(width: inner-w, align(center, body))
  }
}

#let process-model-layout(spec, width, model-layout) = {
  let nodes = spec.nodes
  let edges = spec.edges
  let count = nodes.len()
  let gap = 0.55
  let box_h = 1.05
  let total_w = width.pt() / pt-per-cm
  let box_w = if model-layout { total_w * 0.8 } else { (total_w - gap * (count - 1)) / count }
  let pos(index) = if model-layout {
    (0, -index * (box_h + gap))
  } else {
    (index * (box_w + gap), 0)
  }

  cetz.canvas({
    import cetz.draw: *
    for (index, node) in nodes.enumerate() {
      let (x, y) = pos(index)
      let width-pt = box_w * 1cm
      let height-pt = box_h * 1cm
      let has-sub = "sub" in node and node.sub != none
      rect((x, y), (x + box_w, y + box_h), radius: tokens.diagram.radius, stroke: tokens.diagram.stroke)
      content((x + box_w / 2, y + box_h - 0.28), fitted(node.label, width-pt, height-pt * (if has-sub { 0.55 } else { 1 }), weight: tokens.diagram.label_weight))
      if has-sub {
        content((x + box_w / 2, y + 0.24), fitted(node.sub, width-pt, height-pt * 0.55, start: tokens.diagram.sub, style: "italic", fill: tokens.diagram.edge_ink))
      }
    }

    for edge in edges {
      let from_i = nodes.position(n => n.id == edge.from)
      let to_i = nodes.position(n => n.id == edge.to)
      let kind = edge-kind(edge)
      let mark = if kind == "line" { none } else { (end: ">", fill: tokens.ink.text, scale: 0.55) }
      let (fx, fy) = pos(from_i)
      let (tx, ty) = pos(to_i)
      if model-layout {
        if to_i == from_i + 1 {
          line((fx + box_w / 2, fy), (tx + box_w / 2, ty + box_h), stroke: tokens.diagram.stroke, mark: mark)
        } else if to_i > from_i + 1 {
          let x = box_w + 0.35
          line(
            (fx + box_w, fy + box_h / 2), (x, fy + box_h / 2),
            (x, ty + box_h / 2), (tx + box_w - 0.02, ty + box_h / 2),
            stroke: tokens.diagram.stroke, mark: mark,
          )
        } else {
          let x = -0.35
          line(
            (fx, fy + box_h / 2), (x, fy + box_h / 2),
            (x, ty + box_h / 2), (tx + 0.02, ty + box_h / 2),
            stroke: (paint: tokens.diagram.edge_ink, dash: "dashed", thickness: tokens.diagram.dash_stroke), mark: mark,
          )
        }
      } else {
        if to_i == from_i + 1 {
          line((fx + box_w, fy + box_h / 2), (tx - 0.02, ty + box_h / 2), stroke: tokens.diagram.stroke, mark: mark)
        } else if to_i > from_i + 1 {
          let y = fy + box_h + 0.35
          line(
            (fx + box_w / 2, fy + box_h), (fx + box_w / 2, y),
            (tx + box_w / 2, y), (tx + box_w / 2, ty + box_h + 0.02),
            stroke: tokens.diagram.stroke, mark: mark,
          )
        } else {
          let y = -0.5
          line(
            (fx + box_w / 2, fy), (fx + box_w / 2, y),
            (tx + box_w / 2, y), (tx + box_w / 2, ty - 0.02),
            stroke: (paint: tokens.diagram.edge_ink, dash: "dashed", thickness: tokens.diagram.dash_stroke), mark: mark,
          )
          if from_i == count - 1 and to_i == 0 {
            content(((fx + tx) / 2 + box_w / 2, y - 0.22), align(center, text(size: tokens.diagram.feedback, fill: tokens.diagram.edge_ink, "feedback")))
          }
        }
      }
    }

    if "groups" in spec and spec.groups.len() > 0 {
      for (group_index, group) in spec.groups.enumerate() {
        let members = group.nodes.map(node => nodes.position(n => n.id == node))
        if model-layout {
          let ys = members.map(index => pos(index).at(1))
          let low_y = calc.min(..ys)
          let high_y = calc.max(..ys) + box_h
          let x = box_w + 0.6 + group_index * 0.45
          for y in ys {
            line((x, y), (x, y + box_h), stroke: tokens.diagram.group_rule)
          }
          content((x + 0.12, (low_y + high_y) / 2), align(left, text(size: tokens.diagram.group_label, fill: tokens.diagram.group_ink, group.label)))
        } else {
          let xs = members.map(index => pos(index).at(0))
          let low_x = calc.min(..xs)
          let high_x = calc.max(..xs) + box_w
          let line_y = -0.95 - group_index * 0.38
          for x in xs {
            line((x, line_y), (x + box_w, line_y), stroke: tokens.diagram.group_rule)
          }
          content(((low_x + high_x) / 2, line_y - 0.18), align(center, text(size: tokens.diagram.group_label, fill: tokens.diagram.group_ink, group.label)))
        }
      }
    }
  })
}

#let process-layout(spec, width) = process-model-layout(spec, width, false)
#let model-layout(spec, width) = process-model-layout(spec, width, true)

// Shared catalogue geometry. Layouts consume these and never read Python state.
#let node-width = 2.55
#let node-height = 0.95
#let edge-gap = 0.06

#let rect-border(center, toward, w, h) = {
  let dx = toward.at(0) - center.at(0)
  let dy = toward.at(1) - center.at(1)
  if dx == 0 and dy == 0 { return center }
  let tx = if dx == 0 { 1e9 } else { (w / 2) / calc.abs(dx) }
  let ty = if dy == 0 { 1e9 } else { (h / 2) / calc.abs(dy) }
  let t = calc.min(tx, ty)
  (center.at(0) + dx * t, center.at(1) + dy * t)
}

#let draw-edge(a, b, w, h, kind: "arrow", dashed: false) = {
  let start = rect-border(a, b, w + 2 * edge-gap, h + 2 * edge-gap)
  let end = rect-border(b, a, w + 2 * edge-gap, h + 2 * edge-gap)
  let mark = if kind == "line" { none } else { (end: ">", fill: tokens.ink.text, scale: 0.55) }
  let stroke = if dashed {
    (paint: tokens.diagram.edge_ink, dash: "dashed", thickness: tokens.diagram.dash_stroke)
  } else {
    tokens.diagram.stroke
  }
  cetz.draw.line(..(start, end), stroke: stroke, mark: mark)
}

#let xy(point) = (point.x, point.y)

#let draw-node(node, at, w: node-width, h: node-height) = {
  let (cx, cy) = at
  let width-pt = w * 1cm
  let height-pt = h * 1cm
  let has-sub = "sub" in node and node.sub != none
  cetz.draw.rect((cx - w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), radius: tokens.diagram.radius, stroke: tokens.diagram.stroke)
  if has-sub {
    cetz.draw.content((cx, cy + 0.16), fitted(node.sub, width-pt, height-pt * 0.55, start: tokens.diagram.sub, style: "italic", fill: tokens.diagram.edge_ink))
    cetz.draw.content((cx, cy - 0.12), fitted(node.label, width-pt, height-pt * 0.55, weight: tokens.diagram.label_weight))
  } else {
    cetz.draw.content((cx, cy), fitted(node.label, width-pt, height-pt, weight: tokens.diagram.label_weight))
  }
}

#let ring-center(index, count, total-w) = {
  let rx = total-w / 2 - node-width / 2 - 0.15
  let ry = calc.max(1.15, rx * 0.52)
  let angle = (-90 + index * 360 / count) * 1deg
  (rx * calc.cos(angle), ry * calc.sin(angle))
}

#let cycle-layout(spec, width) = {
  let nodes = spec.nodes
  let edges = spec.edges
  let count = nodes.len()
  let total-w = width.pt() / pt-per-cm
  cetz.canvas({
    import cetz.draw: *
    for edge in edges {
      let from-i = nodes.position(n => n.id == edge.from)
      let to-i = nodes.position(n => n.id == edge.to)
      draw-edge(ring-center(from-i, count, total-w), ring-center(to-i, count, total-w), node-width, node-height, kind: edge-kind(edge))
    }
    for (index, node) in nodes.enumerate() {
      draw-node(node, ring-center(index, count, total-w))
    }
  })
}

#let tree-positions(spec, total-w) = {
  let nodes = spec.nodes
  let children = (:)
  for node in nodes { children.insert(node.id, ()) }
  let incoming = (:)
  for edge in spec.edges {
    children.insert(edge.from, children.at(edge.from) + (edge.to,))
    incoming.insert(edge.to, true)
  }
  let root = nodes.find(n => not incoming.at(n.id, default: false)).id
  let leaf-count = nodes.filter(n => children.at(n.id).len() == 0).len()
  let slot = if leaf-count > 1 { (total-w - node-width) / (leaf-count - 1) } else { 0 }
  let level-gap = node-height + 0.72
  let place(id, depth, positions, cursor) = {
    let kids = children.at(id)
    if kids.len() == 0 {
      let x = node-width / 2 + cursor * slot
      positions.insert(id, (x: x, y: -depth * level-gap))
      (positions, cursor + 1)
    } else {
      let first-x = 0
      let last-x = 0
      let next-positions = positions
      let next-cursor = cursor
      for (index, kid) in kids.enumerate() {
        let placed = place(kid, depth + 1, next-positions, next-cursor)
        next-positions = placed.at(0)
        next-cursor = placed.at(1)
        let kx = next-positions.at(kid).x
        if index == 0 { first-x = kx }
        last-x = kx
      }
      let y = -depth * level-gap
      next-positions.insert(id, (x: (first-x + last-x) / 2, y: y))
      (next-positions, next-cursor)
    }
  }
  let (positions, _cursor) = place(root, 0, (:), 0)
  (positions: positions, root: root)
}

#let hierarchy-layout(spec, width) = {
  let total-w = width.pt() / pt-per-cm
  let positions = tree-positions(spec, total-w).positions
  cetz.canvas({
    import cetz.draw: *
    for edge in spec.edges {
      draw-edge(xy(positions.at(edge.from)), xy(positions.at(edge.to)), node-width, node-height, kind: edge-kind(edge))
    }
    for node in spec.nodes {
      draw-node(node, xy(positions.at(node.id)))
    }
  })
}

#let draw-edge-label(label, a, b, w, h) = {
  let start = rect-border(a, b, w, h)
  let end = rect-border(b, a, w, h)
  let mx = (start.at(0) + end.at(0)) / 2
  let my = (start.at(1) + end.at(1)) / 2
  let dx = end.at(0) - start.at(0)
  let dy = end.at(1) - start.at(1)
  let length = calc.sqrt(dx * dx + dy * dy)
  let nx = if length == 0 { 0 } else { -dy / length }
  let ny = if length == 0 { 0 } else { dx / length }
  cetz.draw.content((mx + nx * 0.26, my + ny * 0.26), fitted(label, 2.2 * 1cm, 0.7 * 1cm, start: tokens.diagram.feedback, fill: tokens.diagram.edge_ink))
}

#let decision-tree-layout(spec, width) = {
  let total-w = width.pt() / pt-per-cm
  let positions = tree-positions(spec, total-w).positions
  cetz.canvas({
    import cetz.draw: *
    for edge in spec.edges {
      let a = xy(positions.at(edge.from))
      let b = xy(positions.at(edge.to))
      draw-edge(a, b, node-width, node-height, kind: edge-kind(edge))
      if "label" in edge and edge.label != none {
        draw-edge-label(edge.label, a, b, node-width, node-height)
      }
    }
    for node in spec.nodes {
      draw-node(node, xy(positions.at(node.id)))
    }
  })
}

#let network-layout(spec, width) = {
  let nodes = spec.nodes
  let count = nodes.len()
  let total-w = width.pt() / pt-per-cm
  cetz.canvas({
    import cetz.draw: *
    for edge in spec.edges {
      let from-i = nodes.position(n => n.id == edge.from)
      let to-i = nodes.position(n => n.id == edge.to)
      draw-edge(ring-center(from-i, count, total-w), ring-center(to-i, count, total-w), node-width, node-height, kind: edge-kind(edge))
    }
    for (index, node) in nodes.enumerate() {
      draw-node(node, ring-center(index, count, total-w))
    }
  })
}

#let timeline-layout(spec, width) = {
  let events = spec.events
  let count = events.len()
  let total-w = width.pt() / pt-per-cm
  let margin = 0.75
  let spacing = if count > 1 { (total-w - 2 * margin) / (count - 1) } else { 0 }
  let event-x(index) = margin + index * spacing
  cetz.canvas({
    import cetz.draw: *
    line((margin - 0.2, 0), (total-w - margin + 0.2, 0), stroke: tokens.diagram.group_rule)
    for (index, event) in events.enumerate() {
      let x = event-x(index)
      let dir = if calc.even(index) { 1 } else { -1 }
      line((x, -0.06 * dir), (x, 0.32 * dir), stroke: tokens.diagram.stroke)
      circle((x, 0), radius: 0.055, fill: tokens.ink.text, stroke: none)
      let slot-w = if spacing > 0.4 { spacing - 0.2 } else { total-w - 2 * margin }
      cetz.draw.content((x, 0.52 * dir), fitted(event.when, slot-w * 1cm, 0.6 * 1cm, start: tokens.diagram.feedback, fill: tokens.diagram.edge_ink))
      cetz.draw.content((x, 0.88 * dir), fitted(event.label, slot-w * 1cm, 0.75 * 1cm, weight: tokens.diagram.label_weight))
      if "sub" in event and event.sub != none {
        cetz.draw.content((x, 1.15 * dir), fitted(event.sub, slot-w * 1cm, 0.6 * 1cm, start: tokens.diagram.sub, style: "italic", fill: tokens.diagram.edge_ink))
      }
    }
  })
}

#let matrix-layout(spec, width) = {
  let rows = spec.rows
  let columns = spec.columns
  let cells = spec.cells
  let total-w = width.pt() / pt-per-cm
  let label-w = 2.5
  let cell-w = (total-w - label-w) / columns.len()
  let row-h = 1.05
  let header-h = 0.8
  cetz.canvas({
    import cetz.draw: *
    for (column-index, column) in columns.enumerate() {
      let x = label-w + column-index * cell-w
      rect((x, -header-h), (x + cell-w, 0), stroke: tokens.diagram.group_rule)
      cetz.draw.content((x + cell-w / 2, -header-h / 2), fitted(column, cell-w * 1cm, header-h * 1cm, start: tokens.diagram.feedback, weight: tokens.diagram.label_weight))
    }
    for (row-index, row) in rows.enumerate() {
      let y = -header-h - row-index * row-h
      rect((0, y), (label-w, y + row-h), stroke: tokens.diagram.group_rule)
      cetz.draw.content((label-w / 2, y + row-h / 2), fitted(row, label-w * 1cm, row-h * 1cm, start: tokens.diagram.feedback, weight: tokens.diagram.label_weight))
      for (column-index, cell) in cells.at(row-index).enumerate() {
        let x = label-w + column-index * cell-w
        rect((x, y), (x + cell-w, y + row-h), stroke: tokens.diagram.group_rule)
        cetz.draw.content((x + cell-w / 2, y + row-h / 2), fitted(cell, cell-w * 1cm, row-h * 1cm, start: tokens.diagram.feedback))
      }
    }
  })
}

#let venn-geometry(count, total-w) = {
  let cx = total-w / 2
  let radius = if count == 2 { 2.3 } else { 2.35 }
  let centers = if count == 2 {
    ((cx - 1.35, 0), (cx + 1.35, 0))
  } else {
    ((cx, 1.25), (cx - 1.5, -0.9), (cx + 1.5, -0.9))
  }
  (centers: centers, radius: radius, cx: cx)
}

#let venn-layout(spec, width) = {
  let sets = spec.sets
  let overlaps = if "overlaps" in spec and spec.overlaps != none { spec.overlaps } else { () }
  let total-w = width.pt() / pt-per-cm
  let geometry = venn-geometry(sets.len(), total-w)
  let centers = geometry.centers
  let radius = geometry.radius
  let cx = geometry.cx
  let label-positions = if sets.len() == 2 {
    ((cx - 1.35, radius + 0.35), (cx + 1.35, radius + 0.35))
  } else {
    ((cx, 1.25 + radius + 0.35), (cx - 1.5 - 0.9, -0.9 - radius - 0.2), (cx + 1.5 + 0.9, -0.9 - radius - 0.2))
  }
  cetz.canvas({
    import cetz.draw: *
    for center in centers {
      circle(center, radius: radius, stroke: tokens.diagram.stroke)
    }
    let set-label-w = if sets.len() == 2 { 2.4 } else { 3.0 }
    for (index, entry) in sets.enumerate() {
      cetz.draw.content(label-positions.at(index), fitted(entry.label, set-label-w * 1cm, 0.55 * 1cm, start: tokens.diagram.feedback, weight: tokens.diagram.label_weight))
    }
    for overlap in overlaps {
      let members = overlap.sets
      if members.len() > 0 {
        let xs = members.map(id => centers.at(sets.position(entry => entry.id == id)).at(0))
        let ys = members.map(id => centers.at(sets.position(entry => entry.id == id)).at(1))
        let x = xs.sum() / xs.len()
        let y = ys.sum() / ys.len()
        cetz.draw.content((x, y), fitted(overlap.label, 1.8 * 1cm, 0.55 * 1cm, start: tokens.diagram.feedback, fill: tokens.ink.grey_1))
      }
    }
  })
}

#let swimlane-layout(spec, width) = {
  let lanes = spec.lanes
  let stages = spec.stages
  let nodes = spec.nodes
  let total-w = width.pt() / pt-per-cm
  let label-w = 2.3
  let cell-w = (total-w - label-w) / stages.len()
  let header-h = 0.8
  let cell-h = 1.0
  cetz.canvas({
    import cetz.draw: *
    for (stage-index, stage) in stages.enumerate() {
      let x = label-w + stage-index * cell-w
      rect((x, -header-h), (x + cell-w, 0), stroke: tokens.diagram.group_rule)
      cetz.draw.content((x + cell-w / 2, -header-h / 2), fitted(stage.label, cell-w * 1cm, header-h * 1cm, start: tokens.diagram.feedback, weight: tokens.diagram.label_weight))
    }
    for (lane-index, lane) in lanes.enumerate() {
      let y = -header-h - lane-index * cell-h
      rect((0, y), (label-w, y - cell-h), stroke: tokens.diagram.group_rule)
      cetz.draw.content((label-w / 2, y - cell-h / 2), fitted(lane.label, label-w * 1cm, cell-h * 1cm, start: tokens.diagram.feedback, weight: tokens.diagram.label_weight))
      for (stage-index, _stage) in stages.enumerate() {
        let x = label-w + stage-index * cell-w
        rect((x, y), (x + cell-w, y - cell-h), stroke: tokens.diagram.group_rule)
      }
    }
    for node in nodes {
      let lane-index = lanes.position(lane => lane.id == node.lane)
      let stage-index = stages.position(stage => stage.id == node.stage)
      let x = label-w + stage-index * cell-w + cell-w / 2
      let y = -header-h - lane-index * cell-h - cell-h / 2
      cetz.draw.content((x, y), fitted(node.label, cell-w * 1cm, cell-h * 1cm, weight: tokens.diagram.label_weight))
    }
  })
}

#let layouts = (
  process: process-layout,
  model: model-layout,
  cycle: cycle-layout,
  hierarchy: hierarchy-layout,
  decision_tree: decision-tree-layout,
  network: network-layout,
  timeline: timeline-layout,
  matrix: matrix-layout,
  venn: venn-layout,
  swimlane: swimlane-layout,
)

#let layout-for(preset) = layouts.at(preset, default: none)
