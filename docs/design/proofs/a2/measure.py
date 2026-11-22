#!/usr/bin/env python3
"""Disposable measurement helper for the A2 layout proof (not a product file)."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
BBOX = HERE / "proof.bbox.html"
PAGES = sorted(HERE.joinpath("pages").glob("page-*.png"))

PT_PER_PX = 72 / 300
PAGE_W, PAGE_H = 595.2756, 841.8898
MARGIN = 60.0
COL_GUTTER = 16.0
MEASURE = 475.276
COL_W = (MEASURE - COL_GUTTER) / 2
COL1 = (MARGIN, MARGIN + COL_W)
COL2 = (MARGIN + COL_W + COL_GUTTER, MARGIN + MEASURE)


def local(elements, name):
    return [e for e in elements if e.tag.endswith(name)]


def words(page):
    for w in local(page.iter(), "word"):
        yield {
            "text": w.text or "",
            "x0": float(w.get("xMin")),
            "y0": float(w.get("yMin")),
            "x1": float(w.get("xMax")),
            "y1": float(w.get("yMax")),
        }


def bbox(items):
    if not items:
        return None
    return {
        "x0": round(min(i["x0"] for i in items), 2),
        "y0": round(min(i["y0"] for i in items), 2),
        "x1": round(max(i["x1"] for i in items), 2),
        "y1": round(max(i["y1"] for i in items), 2),
    }


def ink_bbox(img, box_px):
    crop = img.crop(box_px).convert("RGB")
    px = crop.load()
    xs, ys = [], []
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b = px[x, y]
            if min(r, g, b) < 245:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return {
        "x0": round(box_px[0] * PT_PER_PX + min(xs) * PT_PER_PX, 2),
        "y0": round(box_px[1] * PT_PER_PX + min(ys) * PT_PER_PX, 2),
        "x1": round(box_px[0] * PT_PER_PX + (max(xs) + 1) * PT_PER_PX, 2),
        "y1": round(box_px[1] * PT_PER_PX + (max(ys) + 1) * PT_PER_PX, 2),
    }


root = ET.parse(BBOX).getroot()
report = {
    "geometry_pt": {
        "page": [PAGE_W, PAGE_H],
        "text_block": [MARGIN, MARGIN, round(PAGE_W - MARGIN, 3), round(PAGE_H - MARGIN, 3)],
        "columns": {
            "one": [round(v, 3) for v in COL1],
            "two": [round(v, 3) for v in COL2],
            "width": round(COL_W, 3),
            "gutter": COL_GUTTER,
        },
    },
    "pages": [],
}

for pno, page in enumerate(local(root.iter(), "page"), start=1):
    ws = list(words(page))
    body = [w for w in ws if w["y0"] < PAGE_H - MARGIN + 2]
    folio = [w for w in ws if w["y0"] >= PAGE_H - MARGIN + 2]
    # Page 1 only carries the opening title block (kicker + h1 + standfirst).
    title = [w for w in body if pno == 1 and w["y0"] < 122.0]
    rest = [w for w in body if w not in title]
    c1 = [w for w in rest if w["x0"] >= COL1[0] - 0.5 and w["x0"] < COL1[1] + 4]
    c2 = [w for w in rest if w["x0"] >= COL2[0] - 0.5 and w["x0"] < COL2[1] + 4]
    c1 = [w for w in c1 if w["x0"] < COL1[1] + 4]
    c2 = [w for w in c2 if w["x0"] >= COL2[0] - 0.5]
    # Actual gutter crossing: a word that begins left of the gutter and ends
    # right of it. Hanging punctuation at a column edge is reported separately.
    cross = [w for w in rest if w["x0"] < COL2[0] - 0.01 and w["x1"] > COL2[0]]
    over1 = [w for w in c1 if w["x1"] > COL1[1] + 0.01]
    over2 = [w for w in c2 if w["x1"] > COL2[1] + 0.01]

    img = Image.open(PAGES[pno - 1])
    scale = 300 / 72
    body_px = (
        0,
        int(MARGIN * scale),
        int(PAGE_W * scale),
        int((PAGE_H - MARGIN) * scale),
    )
    body_ink = ink_bbox(img, body_px)
    page_ink = ink_bbox(img, (0, 0, int(PAGE_W * scale), int(PAGE_H * scale)))

    fig_words = [
        w for w in c2
        if any(s in w["text"] for s in ("VECTOR", "PLACEHOLDER", "DATA", "Figure", "A2.1"))
    ]
    fig_ink = None
    if fig_words:
        y0 = min(w["y0"] for w in fig_words)
        y1 = max(w["y1"] for w in fig_words)
        fig_px = (
            int(COL2[0] * scale),
            int(y0 * scale),
            int(COL2[1] * scale),
            int(y1 * scale),
        )
        fig_ink = ink_bbox(img, fig_px)

    clear_above = None
    clear_below = None
    if fig_words:
        fy0 = min(w["y0"] for w in fig_words)
        fy1 = max(w["y1"] for w in fig_words)
        above = [w for w in c2 if w["y1"] <= fy0]
        below = [w for w in c2 if w["y0"] >= fy1]
        if above:
            clear_above = round(fy0 - max(w["y1"] for w in above), 2)
        if below:
            clear_below = round(min(w["y0"] for w in below) - fy1, 2)

    report["pages"].append({
        "page": pno,
        "title_bbox": bbox(title),
        "col1_text_bbox": bbox(c1),
        "col2_text_bbox": bbox(c2),
        "words_in_columns": len(c1) + len(c2),
        "words_crossing_gutter": [w["text"] for w in cross],
        "right_edge_overhang": {
            "col1": {"count": len(over1), "max_x": round(max((w["x1"] for w in over1), default=0), 2)},
            "col2": {"count": len(over2), "max_x": round(max((w["x1"] for w in over2), default=0), 2)},
        },
        "folio_bbox": bbox(folio),
        "body_ink_bbox_px300": body_ink,
        "full_page_ink_bbox_px300": page_ink,
        "figure_unit_bbox_with_text": fig_ink,
        "figure_label_caption_bbox": bbox(fig_words),
        "figure_vertical_clearance": {"above": clear_above, "below": clear_below},
        "image_size_px": list(img.size),
    })

page1 = local(root.iter(), "page")[0]
ws = [
    w for w in words(page1)
    if COL1[0] - 0.5 <= w["x0"] and w["x0"] < COL1[1] + 4 and w["y0"] > 140
]
ys = sorted({round(w["y0"], 2) for w in ws})
deltas = [round(b - a, 2) for a, b in zip(ys, ys[1:]) if 14.8 < b - a < 15.8]
report["measured_line_pitch_pt"] = {
    "nominal": 15.30,
    "median": sorted(deltas)[len(deltas) // 2] if deltas else None,
    "min": min(deltas) if deltas else None,
    "max": max(deltas) if deltas else None,
    "samples": len(deltas),
}


# --- Heading clearance: ink-row scan at 300 dpi --------------------------------
# One white band per heading: last ink row of the heading to first ink row of the
# following content. Windows are in points and only bound the scan; the gap is
# read from rendered pixels, not from source spacing.
def row_groups(img, x0, y0, x1, y1, threshold=200):
    crop = img.crop((round(x0 * 300 / 72), round(y0 * 300 / 72),
                     round(x1 * 300 / 72), round(y1 * 300 / 72))).convert("L")
    px = crop.load()
    rows = [any(px[x, y] < threshold for x in range(crop.width)) for y in range(crop.height)]
    groups, start = [], None
    for y, ink in enumerate(rows + [False]):
        if ink and start is None:
            start = y
        elif not ink and start is not None:
            groups.append((start, y - 1))
            start = None
    merged = []
    for g in groups:
        if merged and g[0] - merged[-1][1] <= 3:
            merged[-1] = (merged[-1][0], g[1])
        else:
            merged.append(g)
    return [(round(y0 + g[0] * 72 / 300, 2), round(y0 + (g[1] + 1) * 72 / 300, 2)) for g in merged]


pages_img = [Image.open(p) for p in PAGES]
scans = [
    ("Chapter 2", 1, 60, 66, 535, 125),
    ("2. Example 1", 1, 60, 122, 291.8, 165),
    ("2.1 Example 2", 1, 60, 493, 291.8, 540),
    ("2.1.1 Continuing Branch", 2, 60, 135, 291.8, 180),
    ("2.1.1.1 Deeper Branch", 2, 60, 422, 291.8, 468),
]
gaps = {}
for label, page, x0, y0, x1, y1 in scans:
    groups = row_groups(pages_img[page - 1], x0, y0, x1, y1)
    if len(groups) >= 2:
        gaps[label] = {
            "heading_ink": list(groups[0]),
            "next_content_ink": list(groups[1]),
            "white_gap_pt": round(groups[1][0] - groups[0][1], 2),
        }
report["heading_gaps"] = gaps
print(json.dumps(report, indent=2))
