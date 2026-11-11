"""Build report: pages, numbering, placements, hashes and warnings."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bookify.design import tokens
from bookify.errors import BookifyError

LABEL = re.compile(r"^(Figure|Table|Photograph) (\d+)\.")
HTML_NS = "http://www.w3.org/1999/xhtml"
SIDE_PRESETS = ("side-left", "side-right")
PAGE_NUMBER = re.compile(r"^\d+$")
# Poppler's line bbox includes glyph side bearings. A justified line set to the
# 475.28 pt measure measures ~2.0 pt wider at the final glyph. This allowance is
# for the build-time fit guard only; the caption and figure-geometry gates keep
# their independent 2.0 pt tolerance.
FIT_GLYPH_OVERHANG_PT = 3.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def composition_entries(document: dict[str, Any], numbered: dict[str, int]) -> list[dict[str, Any]]:
    """Evidence for every illustration that declared a composition."""
    entries: list[dict[str, Any]] = []
    for section in document["sections"]:
        for block in section["blocks"]:
            if block.get("type") != "illustration" or "composition" not in block:
                continue
            companion = block.get("companion")
            entries.append(
                {
                    "blockId": block["id"],
                    "preset": block["composition"],
                    "companionId": companion["id"] if companion else None,
                    "page": numbered.get(block.get("label", "")),
                    "deferred": bool(block.get("pagebreak")),
                }
            )
    return entries


def _text_pages(pdf: Path, count: int) -> list[str]:
    pages: list[str] = []
    for index in range(1, count + 1):
        result = subprocess.run(
            ["pdftotext", "-layout", "-f", str(index), "-l", str(index), str(pdf), "-"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise BookifyError("BUILD_FAILED", f"pdftotext failed on page {index}", str(pdf))
        pages.append(result.stdout)
    return pages


def _bbox_lines(pdf: Path, page: int) -> tuple[float, float, list[tuple[str, float, float, float, float]]]:
    """Rendered line boxes on one page: text, xMin, xMax, yMin, yMax."""
    result = subprocess.run(
        ["pdftotext", "-bbox-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise BookifyError("BUILD_FAILED", f"pdftotext -bbox-layout failed on page {page}", str(pdf))
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as error:
        raise BookifyError("BUILD_FAILED", f"cannot parse PDF line boxes: {error}", str(pdf)) from error
    lines: list[tuple[str, float, float, float, float]] = []
    for page_node in root.iter(f"{{{HTML_NS}}}page"):
        width = float(page_node.attrib.get("width", "0"))
        height = float(page_node.attrib.get("height", "0"))
        for line in page_node.iter(f"{{{HTML_NS}}}line"):
            words = [word.text or "" for word in line.iter(f"{{{HTML_NS}}}word")]
            text = " ".join(" ".join(words).split())
            if not text:
                continue
            lines.append(
                (
                    text,
                    float(line.attrib["xMin"]),
                    float(line.attrib["xMax"]),
                    float(line.attrib["yMin"]),
                    float(line.attrib["yMax"]),
                )
            )
        return width, height, lines
    return 0.0, 0.0, lines


def require_composition_fit(
    pdf: Path,
    document: dict[str, Any],
    numbered: dict[str, int],
    page_height: float,
) -> None:
    """A side composition must fit the text block; never clip or drop it silently."""
    margin = tokens.PAGE_MARGIN_PT
    measure_right = margin + tokens.BODY_MEASURE_PT
    cache: dict[int, list[tuple[str, float, float, float, float]]] = {}
    for section in document["sections"]:
        for block in section["blocks"]:
            if block.get("type") != "illustration" or block.get("composition") not in SIDE_PRESETS:
                continue
            page = numbered.get(block.get("label", ""))
            if page is None:
                continue
            if page not in cache:
                cache[page] = _bbox_lines(pdf, page)[2]
            for text, x_min, x_max, y_min, y_max in cache[page]:
                if PAGE_NUMBER.fullmatch(text):
                    continue
                if y_max > page_height - margin + 2.0:
                    raise BookifyError(
                        "BUILD_FAILED",
                        f"composition does not fit the text block: {block['id']}",
                        block["id"],
                    )
                if x_max > measure_right + FIT_GLYPH_OVERHANG_PT or x_min < margin - FIT_GLYPH_OVERHANG_PT:
                    raise BookifyError(
                        "BUILD_FAILED",
                        f"composition text leaves its column: {block['id']}",
                        block["id"],
                    )


def analyse(
    pdf: Path,
    document: dict[str, Any],
    figure_assets: list[dict[str, str]],
    offline: bool,
    draft: bool,
    manuscript_path: Path,
    network_attempts: int = 0,
) -> dict[str, Any]:
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    pages = int(next(line.split()[1] for line in info.splitlines() if line.startswith("Pages:")))
    size = next(line.split(":", 1)[1].strip() for line in info.splitlines() if line.startswith("Page size:"))
    texts = _text_pages(pdf, pages)
    height_match = re.search(r"x\s*([0-9.]+)\s*pts", size)
    if not height_match:
        raise BookifyError("BUILD_FAILED", f"cannot read page height: {size}", str(pdf))
    page_height = float(height_match.group(1))

    contents_page = next(
        (index for index, text in enumerate(texts, start=1) if "Contents" in text and "..." in text.replace(" ", "")),
        None,
    )
    sections: list[dict[str, Any]] = []
    for section in document["sections"]:
        page = next(
            (
                index
                for index, text in enumerate(texts, start=1)
                if index != 1 and index != contents_page
                and any(line.strip() == section["title"] for line in text.splitlines())
            ),
            None,
        )
        sections.append({"number": section["number"], "title": section["title"], "page": page})

    placements: list[dict[str, Any]] = []
    numbered: dict[str, int] = {}
    for index, text in enumerate(texts, start=1):
        for line in text.splitlines():
            match = LABEL.match(line.strip())
            if match:
                numbered.setdefault(f"{match.group(1)} {match.group(2)}", index)
    for illustration in document["illustrations"]:
        label = illustration.get("label")
        page = numbered.get(label) if label else None
        placements.append({"illustrationId": illustration["id"], "page": page, "caption": illustration["caption"]})

    compositions = composition_entries(document, numbered)
    require_composition_fit(pdf, document, numbered, page_height)

    warnings: list[str] = []
    for section in document["sections"]:
        for block in section["blocks"]:
            # Synthetic and inferred provenance are different claims. The
            # caption says it exactly; the machine-readable report must too.
            if block.get("synthetic"):
                detail = (
                    "synthetic data, not measurements"
                    if block["type"] == "chart"
                    else "illustrative diagram, not a reconstruction"
                )
            elif block.get("approximate"):
                detail = (
                    "values are approximate"
                    if block["type"] == "chart"
                    else "diagram inferred, not traced from a source"
                )
            else:
                continue
            warnings.append(f"{block['label']}: {detail} ({block['id']})")

    return {
        "schemaVersion": "1.0",
        "manuscript": {
            "path": str(manuscript_path),
            "revision": document["revision"],
            "sha256": _sha256(manuscript_path),
        },
        "pdf": {"path": str(pdf), "sha256": _sha256(pdf), "pages": pages, "pageSize": size},
        "offline": offline,
        "networkAttempts": network_attempts,
        "draft": draft,
        "figures": figure_assets,
        "sections": sections,
        "numbered": numbered,
        "placements": placements,
        "compositions": compositions,
        "warnings": warnings,
    }


def write(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
