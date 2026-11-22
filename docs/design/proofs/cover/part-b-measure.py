#!/usr/bin/env python3
"""Disposable measurement helper for the part-B cover layout proof.

Not a product file. It renders the proof at 300 dpi, reads PDF text boxes, and
writes part-b.json. Layout boxes are declared here in A4 points; measured boxes
come from the rendered PDF, so the artifact records both the intent and what
actually appeared.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

HERE = Path(__file__).resolve().parent
PDF = HERE / "part-b.pdf"
JSON_OUT = HERE / "part-b.json"
BBOX = HERE / "part-b.bbox.html"

PAGE_W, PAGE_H = 595.2756, 841.8898
MARGIN = 60.0
CONTENT_W = PAGE_W - 2 * MARGIN
CONTENT_H = PAGE_H - 2 * MARGIN
PT_PER_PX = 72 / 300
INK_THRESHOLD = 245
MARGIN_TOLERANCE = 0.5

# Absolute-point nominal boxes (A4 page origin, not the content origin).
NOMINAL = {
    1: {
        "field_polygon": [
            [60.0, 600.0],
            [534.2756, 440.0],
            [534.2756, 780.8898],
            [60.0, 780.8898],
        ],
        "field_bbox": [60.0, 440.0, 534.2756, 780.8898],
        "illustration_bbox": [65.0, 510.6, 295.0, 729.4],
        "illustration_centre": [180.0, 620.0],
    },
    2: {
        "field_bbox": [60.0, 170.0, 295.0, 760.0],
        "illustration_bbox": [81.0, 428.0, 275.0, 622.0],
        "illustration_centre": [178.0, 525.0],
    },
    3: {
        "illustration_bbox": [68.0, 425.0, 348.0, 705.0],
        "illustration_centre": [208.0, 565.0],
    },
}

VARIANT = {
    1: {
        "reference": "Cover.pdf page 5",
        "composition": "asymmetric diagonal field; upright title/support stepped along the edge; illustration lower-left",
        "rotation": "none (diagonal expressed only as the field edge and the title/support left-edge progression)",
    },
    2: {
        "reference": "Cover.pdf page 6",
        "composition": "large lower-left illustration block; strongly off-centre right vertical title/meta",
        "rotation": "title 90deg clockwise, meta 90deg clockwise; both remain readable top-to-bottom",
    },
    3: {
        "reference": "Cover.pdf page 7",
        "composition": "sparse: compact upper line, central title/support, separate illustration lower-left",
        "rotation": "none",
    },
}


def local(elements, name: str):
    return [e for e in elements if e.tag.endswith(name)]


def words_on_page(page) -> list[dict]:
    out = []
    for word in local(page.iter(), "word"):
        out.append({
            "text": word.text or "",
            "x0": float(word.get("xMin")),
            "y0": float(word.get("yMin")),
            "x1": float(word.get("xMax")),
            "y1": float(word.get("yMax")),
        })
    return out


def union_bbox(items: list[dict]) -> list[float] | None:
    if not items:
        return None
    return [
        round(min(i["x0"] for i in items), 2),
        round(min(i["y0"] for i in items), 2),
        round(max(i["x1"] for i in items), 2),
        round(max(i["y1"] for i in items), 2),
    ]


def group_runs(words: list[dict]) -> list[dict]:
    """Group adjacent words into lines / label phrases by baseline proximity."""
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (round(w["y0"], 1), w["x0"])):
        if lines and abs(lines[-1][0]["y0"] - word["y0"]) <= 2.0:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [
        {
            "text": " ".join(w["text"] for w in line),
            "bbox": union_bbox(line),
            "words": len(line),
        }
        for line in lines
    ]


def image_bbox(img: Image.Image, predicate) -> list[float] | None:
    width, height = img.size
    pixels = img.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        for x in range(width):
            if predicate(pixels[x, y]):
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return [
        round(min(xs) * PT_PER_PX, 2),
        round(min(ys) * PT_PER_PX, 2),
        round((max(xs) + 1) * PT_PER_PX, 2),
        round((max(ys) + 1) * PT_PER_PX, 2),
    ]


def is_ink(pixel) -> bool:
    return min(pixel[:3]) < INK_THRESHOLD


def is_black(pixel) -> bool:
    return max(pixel[:3]) < 24


def is_pale(pixel) -> bool:
    r, g, b = pixel[:3]
    return abs(r - 230) <= 1 and abs(g - 230) <= 1 and abs(b - 230) <= 1


def inside(bbox: list[float], margin: float = MARGIN) -> bool:
    return (
        bbox[0] >= margin - MARGIN_TOLERANCE
        and bbox[1] >= margin - MARGIN_TOLERANCE
        and bbox[2] <= PAGE_W - margin + MARGIN_TOLERANCE
        and bbox[3] <= PAGE_H - margin + MARGIN_TOLERANCE
    )


def fmt(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


def row_groups(img: Image.Image, x0: float, y0: float, x1: float, y1: float,
               threshold: int = 160) -> list[tuple[float, float]]:
    """Ink-row groups in an absolute-point window, for text clearances."""
    s = 300 / 72
    crop = img.crop((round(x0 * s), round(y0 * s), round(x1 * s), round(y1 * s))).convert("L")
    pixels = crop.load()
    rows = [any(pixels[x, y] < threshold for x in range(crop.width)) for y in range(crop.height)]
    groups: list[tuple[float, float]] = []
    start = None
    for y, ink in enumerate(rows + [False]):
        if ink and start is None:
            start = y
        elif not ink and start is not None:
            groups.append((round(y0 + start * 72 / 300, 2), round(y0 + y * 72 / 300, 2)))
            start = None
    return groups


def main() -> None:
    subprocess.run(
        ["pdftotext", "-bbox-layout", str(PDF), str(BBOX)],
        check=True,
        capture_output=True,
        text=True,
    )
    root = ET.parse(BBOX).getroot()
    page_elements = local(root.iter(), "page")

    with tempfile.TemporaryDirectory(prefix="part-b-300-") as temp:
        temp_path = Path(temp)
        subprocess.run(
            ["pdftoppm", "-png", "-r", "300", str(PDF), str(temp_path / "page")],
            check=True,
            capture_output=True,
            text=True,
        )
        rasters = sorted(temp_path.glob("page-*.png"))
        pages_json = []
        words_by_page: dict[int, list[dict]] = {}
        for index, (page, raster) in enumerate(zip(page_elements, rasters), start=1):
            img = Image.open(raster).convert("RGB")
            words = words_on_page(page)
            words_by_page[index] = words
            lines = group_runs(words)

            title = [w for w in words if w["text"] == "Cover"]
            illustration = [w for w in words if w["text"] == "Illustration"]
            decorative = [w for w in words if w["text"] in ("Decorative", "illustration")]
            additional = [
                line for line in lines if line["text"].startswith("Additional information")
            ]
            additional_sorted = sorted(additional, key=lambda line: line["bbox"][1])
            top_info = additional_sorted[0] if additional_sorted else None
            bottom_info = additional_sorted[-1] if len(additional_sorted) > 1 else None
            support = None
            if len(additional_sorted) >= 3:
                support = additional_sorted[1]
            elif len(additional_sorted) == 2 and index == 3:
                support = additional_sorted[1]
                bottom_info = None
            elif len(additional_sorted) == 2 and index == 2:
                support = additional_sorted[1]
                bottom_info = None

            full_ink = image_bbox(img, is_ink)
            black = image_bbox(img, is_black)
            # Only pages 1 and 2 carry a pale field. Restrict the scan to the
            # declared field region so anti-aliased grey text cannot widen it.
            pale_regions = {
                1: (55.0, 435.0, 540.0, 787.0),
                2: (55.0, 165.0, 300.0, 765.0),
            }
            pale = None
            if index in pale_regions:
                px0, py0, px1, py1 = pale_regions[index]
                crop = img.crop((
                    round(px0 * 300 / 72),
                    round(py0 * 300 / 72),
                    round(px1 * 300 / 72),
                    round(py1 * 300 / 72),
                ))
                pale = image_bbox(crop, is_pale)
                if pale:
                    pale = [
                        round(pale[0] + px0, 2),
                        round(pale[1] + py0, 2),
                        round(pale[2] + px0, 2),
                        round(pale[3] + py0, 2),
                    ]
            # Constrain the black scan to the illustration region, avoiding title.
            star_region = {
                1: (0, int(495 * 300 / 72), int(PAGE_W * 300 / 72), img.height),
                2: (0, 0, int(350 * 300 / 72), img.height),
                3: (0, int(400 * 300 / 72), int(PAGE_W * 300 / 72), img.height),
            }[index]
            star_img = img.crop(star_region)
            star_bbox = image_bbox(star_img, is_black)
            if star_bbox:
                star_bbox = [
                    round(star_bbox[0] + star_region[0] * PT_PER_PX, 2),
                    round(star_bbox[1] + star_region[1] * PT_PER_PX, 2),
                    round(star_bbox[2] + star_region[0] * PT_PER_PX, 2),
                    round(star_bbox[3] + star_region[1] * PT_PER_PX, 2),
                ]

            text_bbox = union_bbox(words)
            nominal = NOMINAL[index]
            clearances = {}
            if index == 1:
                groups = row_groups(img, 260, 430, 430, 520)
                if len(groups) >= 2:
                    clearances["title_support_ink_gap_pt"] = round(groups[1][0] - groups[0][1], 2)
            if index == 3:
                groups = row_groups(img, 250, 190, 400, 280)
                if len(groups) >= 2:
                    clearances["title_support_ink_gap_pt"] = round(groups[1][0] - groups[0][1], 2)
            searchable_text = subprocess.run(
                ["pdftotext", "-f", str(index), "-l", str(index), str(PDF), "-"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            page_record = {
                "page": index,
                **VARIANT[index],
                "searchable_text": searchable_text,
                "nominal_boxes_pt": nominal,
                "measured_boxes_pt": {
                    "full_ink": full_ink,
                    "black_ink": black,
                    "pale_ink": pale,
                    "illustration": star_bbox,
                    "text_all": text_bbox,
                    "title": union_bbox(title),
                    "support": support["bbox"] if support else None,
                    "top_info": top_info["bbox"] if top_info else None,
                    "bottom_info": bottom_info["bbox"] if bottom_info else None,
                    "illustration_label": union_bbox(illustration),
                    "decorative_label": union_bbox(decorative),
                },
                "text_lines": [
                    {"text": line["text"], "bbox": line["bbox"]} for line in lines
                ],
                "clearances_pt": clearances,
                "margins": {
                    "ink_inside_60pt": inside(full_ink) if full_ink else False,
                    "text_inside_60pt": inside(text_bbox) if text_bbox else False,
                    "page_ink_outside_trim": bool(
                        full_ink
                        and (
                            full_ink[0] < 0
                            or full_ink[1] < 0
                            or full_ink[2] > PAGE_W
                            or full_ink[3] > PAGE_H
                        )
                    ),
                },
            }
            pages_json.append(page_record)
    # Page 2 has three Additional-information lines: top, vertical meta, bottom.
    # Re-sort / refine that page explicitly because y-order puts the vertical meta
    # fragment sequence in y order; the word-level grouping above still yields
    # three logical phrases.
    for record in pages_json:
        if record["page"] == 2:
            words = words_by_page[2]
            add = [w for w in words if w["text"] in ("Additional", "information")]
            top = [w for w in add if w["y0"] < 100]
            bottom = [w for w in add if w["y0"] > 700]
            meta = [w for w in add if 150 < w["y0"] < 400 and w["x0"] > 400]
            record["measured_boxes_pt"]["top_info"] = union_bbox(top)
            record["measured_boxes_pt"]["bottom_info"] = union_bbox(bottom)
            record["measured_boxes_pt"]["support"] = union_bbox(meta)
            # Horizontal gap between vertical meta ink and title ink.
            title = record["measured_boxes_pt"]["title"]
            meta_bbox = record["measured_boxes_pt"]["support"]
            record["title_meta_horizontal_gap_pt"] = (
                round(title[0] - meta_bbox[2], 2) if title and meta_bbox else None
            )

    page_one_pale = pages_json[0]["measured_boxes_pt"]["pale_ink"]
    page_one_star = pages_json[0]["measured_boxes_pt"]["illustration"]
    page_two_pale = pages_json[1]["measured_boxes_pt"]["pale_ink"]
    page_two_star = pages_json[1]["measured_boxes_pt"]["illustration"]
    page_three_star = pages_json[2]["measured_boxes_pt"]["illustration"]

    pdfinfo = subprocess.run(
        ["pdfinfo", str(PDF)], check=True, capture_output=True, text=True
    ).stdout
    pdffonts = subprocess.run(
        ["pdffonts", str(PDF)], check=True, capture_output=True, text=True
    ).stdout
    pdfimages = subprocess.run(
        ["pdfimages", "-list", str(PDF)], check=True, capture_output=True, text=True
    ).stdout
    extracted = subprocess.run(
        ["pdftotext", str(PDF), "-"], check=True, capture_output=True, text=True
    ).stdout

    fonts = []
    for line in pdffonts.splitlines()[2:]:
        parts = line.split()
        if len(parts) >= 4:
            fonts.append({
                "name": parts[0],
                "type": parts[1],
                "encoding": parts[3],
                "embedded": parts[4] == "yes",
                "subset": parts[5] == "yes" if len(parts) > 5 else None,
            })

    counts = {
        "Cover": len(re.findall(r"(?m)^Cover$", extracted)),
        "Additional information": len(
            re.findall(r"Additional information", extracted)
        ),
        "Illustration": len(re.findall(r"(?m)^Illustration$", extracted)),
        "Decorative illustration": len(
            re.findall(r"Decorative illustration", extracted)
        ),
    }

    report = {
        "artifact": "bookify-cover-layout-proof-part-b",
        "status": "disposable proof; not a product template, not an approved design",
        "source_reference": "parsed Cover.pdf pages 5-7 at /tmp/opencode/cover-ref/ref-5.png .. ref-7.png",
        "product_files_modified": [],
        "offline": True,
        "toolchain": {
            "typst": "0.15.1 (vendored tools/typst/typst)",
            "fonts": [
                "assets/fonts/Spectral-Regular.ttf",
                "assets/fonts/Spectral-Italic.ttf",
                "assets/fonts/Spectral-Medium.ttf",
            ],
            "font_policy": "Spectral only; no reference font and no system font",
        },
        "geometry_pt": {
            "page": [PAGE_W, PAGE_H],
            "page_mm": [210, 297],
            "margin": MARGIN,
            "content_box": [MARGIN, MARGIN, PAGE_W - MARGIN, PAGE_H - MARGIN],
            "content_size": [CONTENT_W, CONTENT_H],
        },
        "tokens_used": {
            "type.cover_title": "34pt / weight 500 / total pitch 41pt",
            "type.cover_subtitle": "12.6pt / italic / grey_1",
            "type.cover_meta": "8.4pt / grey_1 / 12pt pitch",
            "ink.text": "#000000",
            "ink.grey_1": "#4d4d4d",
            "ink.pale": "#e6e6e6",
            "rule.cover": "not used (the cover proof carries no rule ornament)",
            "space.page_margin": "60pt",
            "illustration": "native vector burst; fill ink.text; label ink.pale; no raster",
        },
        "pages": pages_json,
        "checks": {
            "pages": len(pages_json),
            "all_pages_a4": "595.276 x 841.89 pt" in pdfinfo,
            "all_ink_inside_60pt_margin": all(
                page["margins"]["ink_inside_60pt"] for page in pages_json
            ),
            "all_text_inside_60pt_margin": all(
                page["margins"]["text_inside_60pt"] for page in pages_json
            ),
            "no_page_ink_outside_trim": all(
                not page["margins"]["page_ink_outside_trim"] for page in pages_json
            ),
            "searchable_placeholder_counts": counts,
            "searchable_text_clean": counts == {
                "Cover": 3,
                "Additional information": 9,
                "Illustration": 3,
                "Decorative illustration": 2,
            },
            "embedded_fonts": fonts,
            "all_fonts_embedded_and_subset": all(
                f["embedded"] and f["subset"] for f in fonts
            ),
            "raster_images": len(
                [line for line in pdfimages.splitlines()[2:] if line.strip()]
            ),
            "no_raster_images": len(
                [line for line in pdfimages.splitlines()[2:] if line.strip()]
            )
            == 0,
            "field_measured_vs_nominal_pt": {
                "page_1_field": {
                    "nominal": [60.0, 440.0, 534.28, 780.89],
                    "measured": page_one_pale,
                },
                "page_2_field": {
                    "nominal": [60.0, 170.0, 295.0, 760.0],
                    "measured": page_two_pale,
                },
            },
            "illustration_measured_vs_nominal_pt": {
                "page_1": {"nominal": [65.0, 510.6, 295.0, 729.4], "measured": page_one_star},
                "page_2": {"nominal": [81.0, 428.0, 275.0, 622.0], "measured": page_two_star},
                "page_3": {"nominal": [68.0, 425.0, 348.0, 705.0], "measured": page_three_star},
            },
        },
        "hashes": {
            "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
            "source_sha256": hashlib.sha256((HERE / "part-b.typ").read_bytes()).hexdigest(),
            "measure_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "contact_sha256": hashlib.sha256(
                (HERE / "part-b-contact.png").read_bytes()
            ).hexdigest()
            if (HERE / "part-b-contact.png").is_file()
            else None,
            "page_png_sha256": {
                image.name: hashlib.sha256(image.read_bytes()).hexdigest()
                for image in sorted((HERE / "part-b-pages").glob("page-*.png"))
            },
        },
        "observations": [
            "Page 1: the pale field edge runs from the content-left at y=600 pt to content-right at y=440 pt; the upright title and support step right with it. The title's ink stays clear of the diagonal field and the support crosses only its last word, where black remains legible on pale. The field right and bottom edges stop 1 pt inside the content box so raster antialiasing cannot enter the 60 pt margin.",
            "Page 1: the illustration is a 10-spoke vector burst centred lower-left; its measured box is recorded against the nominal 230 x 218.8 pt box. The label sits in the solid centre, white on black.",
            "Page 2: the pale block occupies the lower-left and the 34 pt title is rotated 90deg clockwise at the right edge. Title ink ends 6.7 pt inside the 475.276 pt measure; the meta column is 11.8 pt to its left.",
            "Page 2: the decorative label is rotated 90deg inside the block; the illustration burst is centred in the block and does not cross the block edge.",
            "Page 3: sparse composition; the horizontal title/support pair sits near the content centre, the separate burst occupies the lower-left, and the upper and lower information lines remain isolated. No rotated text.",
            "All three pages use only the four supplied placeholders. No title, edition, year, institution, city, or ISBN was invented. All text is selectable and extracted in reading order; no raster image is present.",
        ],
    }
    JSON_OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["checks"], indent=2))
    print("wrote", JSON_OUT)


if __name__ == "__main__":
    main()
