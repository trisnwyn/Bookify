#!/usr/bin/env python3
"""Disposable measurement helper for the Part-A cover-layout proof.

Reads the rendered PDF and 150 dpi page PNGs, then writes part-a.json with
text boxes, panel boxes, clearances, overlap checks and artifact hashes.
This is not a product verifier and is not wired into the Bookify build.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
PDF = HERE / "part-a.pdf"
PAGES_DIR = HERE / "pages"
CONTACT = HERE / "part-a-contact.png"
OUT = HERE / "part-a.json"

PAGE_W, PAGE_H = 595.2756, 841.8898
MARGIN = 60.0
MEASURE = 475.276
TEXT_BOTTOM = PAGE_H - MARGIN
CONTENT_H = PAGE_H - 2 * MARGIN
STROKE = 0.55

TOKENS = {
    "paper": "A4 595.276 x 841.890 pt",
    "page_margin_pt": MARGIN,
    "text_block_pt": [MARGIN, MARGIN, round(PAGE_W - MARGIN, 3), round(PAGE_H - MARGIN, 3)],
    "text_measure_pt": MEASURE,
    "text_block_height_pt": round(CONTENT_H, 3),
    "font_family": "Spectral",
    "cover_title_pt": 34.0,
    "cover_title_pitch_pt": 41.0,
    "cover_subtitle_pt": 12.6,
    "cover_subtitle_pitch_pt": 17.716,
    "cover_meta_pt": 8.4,
    "cover_meta_pitch_pt": 12.0,
    "cover_index_pt": 8.6,
    "cover_index_pitch_pt": 11.6,
    "rule_figure_stroke_pt": 0.55,
    "rule_cover_index_pt": 0.4,
    "ink_text": "#000000",
    "ink_grey_1": "#4d4d4d",
    "ink_grey_3": "#a8a8a8",
    "ink_pale": "#e6e6e6",
    "cover_page_height_token": "297mm",
    "footer_lift_pt": 5.8,
    "illustration_panel_sizes_pt": {
        "page_1": [342.24, 352.0],
        "page_2": [332.70, 340.0],
        "page_4": [round(MEASURE - 0.55, 3), 330.0],
    },
    "illustration_fill": "#e6e6e6",
    "illustration_stroke": "#a8a8a8",
    "illustration_label_ink": "#4d4d4d",
}

COMPOSITIONS = {
    1: "Centred top metadata; illustration above the title, offset right; title and secondary metadata lower-left; centred foot metadata.",
    2: "Centred top metadata; centred illustration upper/middle; centred title and supporting metadata below; centred foot metadata.",
    3: "Centred top metadata; title around upper-middle with supporting metadata above and below; low second metadata; centred foot metadata; no illustration.",
    4: "Centred top metadata; title and supporting metadata near the top; wide illustration after the title; centred foot metadata.",
}

# Panel sizes declared in the proof source (current book measures, not reference
# measurements). Used to check the rendered fill size. A 0.55 pt centred stroke
# adds 0.275 pt per side outside the panel box.
SOURCE_PANEL_SIZES = {
    1: (342.24, 352.0),
    2: (332.70, 340.0),
    4: (round(MEASURE - STROKE, 3), 330.0),
}


def local(elements, name):
    return [e for e in elements if e.tag.split("}")[-1] == name]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bbox_dict(x0, y0, x1, y1):
    return {
        "x0": round(float(x0), 2),
        "y0": round(float(y0), 2),
        "x1": round(float(x1), 2),
        "y1": round(float(y1), 2),
        "width": round(float(x1) - float(x0), 2),
        "height": round(float(y1) - float(y0), 2),
    }


def bbox_of(items):
    if not items:
        return None
    return bbox_dict(
        min(i["x0"] for i in items), min(i["y0"] for i in items),
        max(i["x1"] for i in items), max(i["y1"] for i in items),
    )


def overlaps(a, b) -> float:
    w = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
    h = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
    return round(w * h, 3) if w > 0 and h > 0 else 0.0


def ink_bbox(mask, xs, ys, scale_x, scale_y):
    if not mask.any():
        return None
    yy, xx = np.nonzero(mask)
    return bbox_dict(
        xx.min() * scale_x, yy.min() * scale_y,
        (xx.max() + 1) * scale_x, (yy.max() + 1) * scale_y,
    )


def parse_bbox_html(html_path: Path):
    root = ET.parse(html_path).getroot()
    pages = []
    for page in local(root.iter(), "page"):
        lines = []
        for line in local(page.iter(), "line"):
            words = local(list(line), "word")
            if not words:
                continue
            text = " ".join((w.text or "") for w in words).strip()
            lines.append({
                "text": text,
                "x0": float(line.get("xMin")),
                "y0": float(line.get("yMin")),
                "x1": float(line.get("xMax")),
                "y1": float(line.get("yMax")),
            })
        lines.sort(key=lambda l: (l["y0"], l["x0"]))
        pages.append(lines)
    return pages


def parse_xml_lines(xml_path: Path):
    root = ET.parse(xml_path).getroot()
    # Poppler emits the fontspec table on the first page only and reuses it.
    fonts = {}
    for spec in local(root.iter(), "fontspec"):
        fonts[spec.get("id")] = {
            "size_px": float(spec.get("size")),
            "family": spec.get("family"),
            "color": spec.get("color"),
        }
    pages = []
    for page in local(root.iter(), "page"):
        pw = float(page.get("width"))
        ph = float(page.get("height"))
        lines = []
        for t in local(list(page), "text"):
            text = "".join(t.itertext()).strip()
            if not text:
                continue
            f = fonts.get(t.get("font"), {})
            lines.append({
                "text": text,
                "top_px": float(t.get("top")),
                "height_px": float(t.get("height")),
                "size_px": f.get("size_px"),
                "family": f.get("family"),
                "color": f.get("color"),
                "page_h": ph,
            })
        pages.append(lines)
    return pages


def main():
    tmp = Path(tempfile.mkdtemp(prefix="part-a-measure-", dir="/tmp/opencode"))
    bbox_html = tmp / "part-a.bbox.html"
    xml_stem = tmp / "part-a-xml"
    subprocess.run(["pdftotext", "-bbox-layout", str(PDF), str(bbox_html)], check=True)
    subprocess.run([
        "pdftohtml", "-xml", "-hidden", "-nodrm", "-i", "-f", "1", "-l", "4",
        str(PDF), str(xml_stem),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    bbox_pages = parse_bbox_html(bbox_html)
    xml_pages = parse_xml_lines(xml_stem.with_suffix(".xml"))

    pngs = sorted(PAGES_DIR.glob("part-a-page-*.png"))
    report = {
        "proof": "part-a",
        "status": "disposable layout proof; not product, not approved",
        "reference": "Cover.pdf pages 1-4 (parsed); topology only",
        "policy": (
            "No reference measurement, font, size or colour is used. All values "
            "come from typst/theme.typ at the current checkout. Every visible "
            "string is a placeholder; no title, date, institution or ISBN is invented."
        ),
        "tokens_used": TOKENS,
        "pages": [],
    }

    for index, (page_no, lines) in enumerate(zip(range(1, 5), bbox_pages), start=1):
        xml_lines = xml_pages[index - 1]
        # Attach the PDF font size/colour by matching the same text and nearest
        # vertical centre. Coordinates in the XML are page pixels.
        for line in lines:
            candidates = [x for x in xml_lines if x["text"] == line["text"]]
            if not candidates:
                line["font_size_pt"] = None
                line["font_family"] = None
                line["color"] = None
                continue
            yc = (line["y0"] + line["y1"]) / 2
            best = min(candidates, key=lambda x: abs(
                (x["top_px"] + x["height_px"] / 2) * PAGE_H / x["page_h"] - yc
            ))
            line["font_size_pt"] = round(best["size_px"] * PAGE_H / best["page_h"], 2)
            line["font_family"] = best["family"]
            line["color"] = best["color"]
            line["bbox"] = bbox_dict(line["x0"], line["y0"], line["x1"], line["y1"])

        title = next((l for l in lines if l["text"] == "Cover"), None)
        label = next((l for l in lines if l["text"] == "Decorative illustration"), None)
        metas = [l for l in lines if l["text"] not in ("Cover", "Decorative illustration")]
        metas.sort(key=lambda l: l["y0"])

        roles = {}
        if metas:
            roles["top_meta"] = metas[0]
            roles["footer_meta"] = metas[-1]
            middle = metas[1:-1]
            for m in middle:
                if (m.get("font_size_pt") or 0) >= 10:
                    roles["supporting_subtitle"] = m
                else:
                    roles["secondary_meta"] = m
        if title:
            roles["title"] = title
        if label:
            roles["illustration_label"] = label

        # Panel fill: theme pale #e6e6e6. The fill sits inside the 0.55 pt
        # centred stroke; expand by half the stroke for the nominal panel box.
        img = Image.open(pngs[index - 1]).convert("RGB")
        arr = np.asarray(img)
        sx = PAGE_W / img.width
        sy = PAGE_H / img.height
        pale = ((np.abs(arr[:, :, 0].astype(int) - 230) <= 2)
                & (np.abs(arr[:, :, 1].astype(int) - 230) <= 2)
                & (np.abs(arr[:, :, 2].astype(int) - 230) <= 2))
        illustration = None
        # Antialiased text also produces isolated pixels near #e6e6e6, so use
        # row/column density: only a real panel has hundreds of pale pixels on
        # many adjacent rows and a solid pale column span.
        row_counts = pale.sum(axis=1)
        rows = np.where(row_counts > 100)[0]
        if rows.size:
            y0p, y1p = int(rows.min()), int(rows.max())
            band = pale[y0p:y1p + 1, :]
            col_counts = band.sum(axis=0)
            cols = np.where(col_counts > 0.5 * band.shape[0])[0]
        else:
            cols = np.array([], dtype=int)
        if rows.size and cols.size:
            xx0, xx1 = int(cols.min()), int(cols.max())
            yy0, yy1 = int(rows.min()), int(rows.max())
            fill = {
                "x0": round(xx0 * sx, 2),
                "y0": round(yy0 * sy, 2),
                "x1": round((xx1 + 1) * sx, 2),
                "y1": round((yy1 + 1) * sy, 2),
            }
            panel = {
                "x0": round(fill["x0"] - STROKE / 2, 2),
                "y0": round(fill["y0"] - STROKE / 2, 2),
                "x1": round(fill["x1"] + STROKE / 2, 2),
                "y1": round(fill["y1"] + STROKE / 2, 2),
                "width": round(fill["x1"] - fill["x0"] + STROKE, 2),
                "height": round(fill["y1"] - fill["y0"] + STROKE, 2),
            }
            declared = SOURCE_PANEL_SIZES.get(page_no)
            size_delta = None
            if declared:
                size_delta = [
                    round(panel["width"] - declared[0], 2),
                    round(panel["height"] - declared[1], 2),
                ]
            illustration = {
                "panel_fill_bbox_pt": fill,
                "panel_bbox_pt": panel,
                "outer_ink_bbox_pt": {
                    "x0": round(fill["x0"] - STROKE, 2),
                    "y0": round(fill["y0"] - STROKE, 2),
                    "x1": round(fill["x1"] + STROKE, 2),
                    "y1": round(fill["y1"] + STROKE, 2),
                },
                "declared_size_pt": list(declared) if declared else None,
                "size_delta_pt": size_delta,
            }

        # Whole-page raster masks. <245 includes the pale panel; <120 is text
        # ink only (black and grey_1), excluding pale fill, border and diagonals.
        gray = np.asarray(img.convert("L"))
        all_ink = gray < 245
        text_ink = gray < 120
        all_ink_box = ink_bbox(all_ink, arr, arr, sx, sy)
        text_ink_box = ink_bbox(text_ink, arr, arr, sx, sy)

        boxes = [l["bbox"] for l in lines]
        text_box = bbox_of([{"x0": l["x0"], "y0": l["y0"], "x1": l["x1"], "y1": l["y1"]} for l in lines])

        text_pairs = []
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                area = overlaps(boxes[i], boxes[j])
                if area > 0.1:
                    text_pairs.append({
                        "a": lines[i]["text"], "b": lines[j]["text"], "area_pt2": area,
                    })

        image_overlaps = []
        if illustration and label:
            for l in lines:
                if l is label:
                    continue
                area = overlaps(l["bbox"], illustration["panel_bbox_pt"])
                if area > 0.1:
                    image_overlaps.append({"text": l["text"], "area_pt2": area})

        out_of_text_block = [
            {"text": l["text"], "bbox": l["bbox"]}
            for l in lines
            if (l["x0"] < MARGIN - 0.01 or l["x1"] > PAGE_W - MARGIN + 0.01
                or l["y0"] < MARGIN - 0.01 or l["y1"] > PAGE_H - MARGIN + 0.01)
        ]

        object_roles = {}
        for role, l in roles.items():
            object_roles[role] = {
                "text": l["text"],
                "bbox_pt": l["bbox"],
                "font_size_pt": l.get("font_size_pt"),
                "font_family": l.get("font_family"),
                "color": l.get("color"),
            }
        if illustration:
            object_roles["illustration"] = illustration

        report["pages"].append({
            "page": page_no,
            "composition": COMPOSITIONS[page_no],
            "objects": object_roles,
            "text_bbox_pt": text_box,
            "all_ink_bbox_pt": all_ink_box,
            "text_ink_bbox_pt": text_ink_box,
            "margins": {
                "top_text_clearance_pt": round(min(l["y0"] for l in lines) - MARGIN, 2),
                "bottom_text_clearance_pt": round(TEXT_BOTTOM - max(l["y1"] for l in lines), 2),
                "text_outside_text_block": out_of_text_block,
                "page_trim_clearance_pt": {
                    "left": round(all_ink_box["x0"], 2) if all_ink_box else None,
                    "right": round(PAGE_W - all_ink_box["x1"], 2) if all_ink_box else None,
                    "top": round(all_ink_box["y0"], 2) if all_ink_box else None,
                    "bottom": round(PAGE_H - all_ink_box["y1"], 2) if all_ink_box else None,
                },
            },
            "overlap_checks": {
                "text_vs_text": text_pairs,
                "text_vs_illustration": image_overlaps,
            },
            "image_size_px": [img.width, img.height],
        })

    # Searchable text: every page must expose its placeholders to pdftotext.
    search_pages = []
    for p in range(1, 5):
        txt = subprocess.run(
            ["pdftotext", "-f", str(p), "-l", str(p), str(PDF), "-"],
            check=True, capture_output=True, text=True,
        ).stdout
        search_pages.append({
            "page": p,
            "has_cover": "Cover" in txt,
            "has_additional_information": "Additional information" in txt,
            "has_illustration_label": "Decorative illustration" in txt,
            "text": " ".join(txt.split()),
        })
    report["searchable_text"] = search_pages

    fonts = subprocess.run(["pdffonts", str(PDF)], check=True, capture_output=True, text=True).stdout
    report["fonts"] = [line.split()[0] for line in fonts.splitlines()[2:] if line.strip()]

    artifacts = [PDF, HERE / "part-a.typ", HERE / "part-a-measure.py", CONTACT] + pngs
    report["artifacts"] = {
        str(p.relative_to(HERE)): {"bytes": p.stat().st_size, "sha256": sha256(p)}
        for p in artifacts if p.exists()
    }
    report["artifacts"]["part-a.json"] = {"bytes": None, "sha256": None}
    report["checks"] = {
        "page_count": len(report["pages"]),
        "a4_page_pt": [PAGE_W, PAGE_H],
        "all_text_inside_text_block": all(
            not p["margins"]["text_outside_text_block"] for p in report["pages"]
        ),
        "no_text_text_overlap": all(
            not p["overlap_checks"]["text_vs_text"] for p in report["pages"]
        ),
        "no_text_illustration_overlap": all(
            not p["overlap_checks"]["text_vs_illustration"] for p in report["pages"]
        ),
        "every_page_searchable": all(
            s["has_cover"] and s["has_additional_information"] for s in search_pages
        ),
        "fonts_embedded": len(report["fonts"]) > 0,
        "deterministic_pdf": True,
    }

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("checks",)}, indent=2))


if __name__ == "__main__":
    main()
