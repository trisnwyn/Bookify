// CeTZ diagram dispatcher. Presets resolve to a named layout; an unknown
// preset is a named failure, never a fallback. Layouts live in layouts.typ.
#import "/typst/cetz/layouts.typ": layout-for

#let diagram(spec, width) = {
  let layout = layout-for(spec.preset)
  if layout == none {
    panic("unknown diagram preset: " + str(spec.preset))
  }
  layout(spec, width)
}
