"""Canonical token names shared by the theme, the linter and the docs.

The accent model is one restrained hue (`accent.ink`) with three tints; the
four semantic roles point at tints or ink, never at four separate hues.
"""

from __future__ import annotations

LEAF_NAMES: tuple[str, ...] = (
    # type
    "body", "lead", "h1", "h2", "h3", "caption", "small", "credit", "table", "table_head",
    "note", "quote",
    # accepted cover compositions (cover-1 .. cover-7)
    "cover_title", "cover_subtitle", "cover_meta",
    # spacing
    "page_margin", "before_heading", "before_h2", "before_h3", "after_heading",
    "heading_clearance",
    "before_standfirst", "after_block", "between_paragraphs", "after_lead",
    "after_figure", "after_caption", "figure_width", "before_role", "side_gutter",
    # side composition
    "side_fraction",
    # measure (v2 plate = body measure, D4; cover block height, D2)
    "plate", "page_height",
    # rules
    "table_top", "table_head", "table_bottom", "figure_stroke",
    # figures
    "caption_align",
    # ink
    "text", "grey_1", "grey_2", "grey_3", "pale",
    # accent
    "ink", "tint_1", "tint_2", "tint_3",
    # roles
    "definition", "example", "case", "assessment",
)

MEASURE: tuple[str, ...] = ("body",)

# CeTZ diagram typography and ink. The values are the pre-tokenisation literals,
# so moving the process/model layout onto the theme cannot change its geometry.
DIAGRAM_TOKENS: dict[str, str] = {
    "label": "8pt",
    "label_weight": "600",
    "sub": "6.6pt",
    "feedback": "6.4pt",
    "group_label": "6.4pt",
    "stroke": "0.55pt",
    "dash_stroke": "0.45pt",
    "group_rule": "0.4pt",
    "radius": "2pt",
    "label_floor": "5.5pt",
    "label_step": "0.5pt",
    "label_pad": "3pt",
    "edge_ink": 'rgb("#6e6e6e")',
    "group_ink": 'rgb("#828282")',
}

DIAGRAM_EDGE_HEX = "#6e6e6e"
DIAGRAM_GROUP_HEX = "#828282"

ROLES: tuple[str, ...] = ("definition", "example", "case", "assessment")
ACCENT_TINTS: tuple[str, ...] = ("tint_1", "tint_2", "tint_3")
BLOCK_TYPES: tuple[str, ...] = (
    "paragraph",
    "lead",
    "quote",
    "definition",
    "example",
    "case",
    "assessment",
    "list",
    "table",
    "equation",
    "chart",
    "diagram",
    "illustration",
    "branch",
    "unresolved",
)

# Python mirrors used by the figure engine; tests assert these match theme.typ.
INK_HEX = "#000000"
GREY_1_HEX = "#4d4d4d"
GREY_3_HEX = "#a8a8a8"
ACCENT_HEX = "#2f3e5c"
ACCENT_TINT_1_HEX = "#d6dbe2"
ACCENT_TINT_2_HEX = "#a9b2c2"
ACCENT_TINT_3_HEX = "#7c8aa2"

# Numeric mirrors used by the rendered-geometry checks. The single source is
# typst/theme.typ; these names let verification derive a declared centre instead
# of rediscovering it from rendered output or repeating a magic number.
#
# Type, leading and ink metrics (theme.typ `ink_metrics`, `leading_extra`,
# `type`). The blank-line rule is derived, never restated: one body line pitch
# is the minimum white band below any heading.
INK_LINE_BOX_EM = 0.660
INK_ASCENT_EM = 0.750
INK_DESCENT_EM = 0.240
BODY_SIZE_PT = 10.1
LEAD_SIZE_PT = 10.6
H1_SIZE_PT = 25.0
H2_SIZE_PT = 12.6
H3_SIZE_PT = 10.3
BODY_LEADING_PT = 8.63
HEADING_CLEARANCE_PT = 0.5
BLANK_LINE_PT = round(INK_LINE_BOX_EM * BODY_SIZE_PT + BODY_LEADING_PT, 2)
PAGE_MARGIN_PT = 60.0
BODY_MEASURE_PT = 475.28
SIDE_FRACTION = 0.46
SIDE_GUTTER_PT = 16.0
# A2: one of two equal columns, (475.28 - 16) / 2.
COLUMN_WIDTH_PT = round((BODY_MEASURE_PT - SIDE_GUTTER_PT) / 2, 2)
CHART_WIDTH_FRACTION = 0.72
ILLUSTRATION_WIDTH_FRACTION = 0.88
DIAGRAM_WIDTH_PT = 430.0
# The centred body visual keeps `measure.figure_width`; a side visual takes
# `measure.side_fraction` of the measure.
FIGURE_WIDTH_PT = 430.0
# The selected cover never prints a chapter index; the title may wrap, but no
# cover composition carries more than this many title lines.
COVER_TITLE_MAX_LINES = 3
# Poppler's line box for a 34 pt title rises up to 4.65 pt above its glyph ink.
# The cover fit guard allows that box only; the raster gate checks real ink.
COVER_LINE_BOX_TOP_ALLOWANCE_PT = 8.0
# D4: a plate is one visual at the full text measure, ±1 pt.
PLATE_PT = BODY_MEASURE_PT
PLATE_TOLERANCE_PT = 1.0
