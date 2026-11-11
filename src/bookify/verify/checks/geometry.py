"""Rendered figure geometry: canvas, frame, visible ink and caption, measured.

Catalogue-scoped gate wired by `runner.run`. It reads Poppler text line boxes to
bound each figure band and a 200 dpi raster to locate the visible ink, following
the independent measurement method the catalogue review already used. Rows that
belong to prose, notes, credits or page numbers are excluded before the ink
bounding box is taken, and side compositions are measured inside the declared
image column. A band with no ink, or a caption that cannot be isolated, fails:
no figure passes on its declared canvas alone.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from bookify.design import tokens
from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks import captions as captions_check
from bookify.verify.checks.pages import pdf_info

INK_TOLERANCE_PT = captions_check.TOLERANCE_PT
CANVAS_TOLERANCE_PT = 1.0
CONTAIN_TOLERANCE_PT = 2.0
DPI = 200
SCALE = DPI / 72.0
INK_THRESHOLD = 245
FRAME_THRESHOLD = 200
FRAME_RULE_FRACTION = 0.5
BAND_GAP_PT = 2.0
HEADING_ZONE_PT = 45.0


@dataclass(frozen=True)
class Canvas:
    left: float
    right: float
    width: float
    centre: float
    expected_centre: float


@dataclass(frozen=True)
class FigureGeometry:
    spec: captions_check.CaptionSpec
    measurement: captions_check.CaptionMeasurement
    canvas: Canvas
    ink: tuple[float, float, float] | None
    frame: tuple[float, float, float] | None
    contained: bool


def _page_size(pdf: Path) -> tuple[float, float]:
    info = pdf_info(pdf)
    size = info.get("Page size", "")
    match = re.match(r"([0-9.]+) x ([0-9.]+) pts", size)
    if not match:
        raise BookifyError("VERIFY_FAILED", f"cannot read page size: {size}", str(pdf))
    return float(match.group(1)), float(match.group(2))


def _canvas(spec: captions_check.CaptionSpec, page_width: float) -> Canvas:
    margin = captions_check.page_margin(page_width)
    if spec.kind == "chart":
        width = tokens.BODY_MEASURE_PT * tokens.CHART_WIDTH_FRACTION
        expected = page_width / 2
        left = expected - width / 2
    elif spec.kind == "diagram":
        width = tokens.DIAGRAM_WIDTH_PT
        expected = page_width / 2
        left = expected - width / 2
    else:
        column = captions_check.image_column(spec.preset, page_width)
        if column is not None:
            left, right = column
            width = right - left
            expected = (left + right) / 2
            return Canvas(left, right, width, expected, expected)
        width = tokens.BODY_MEASURE_PT * tokens.ILLUSTRATION_WIDTH_FRACTION
        expected = page_width / 2
        left = expected - width / 2
    return Canvas(left, left + width, width, left + width / 2, expected)


def _raster(pdf: Path, page: int) -> np.ndarray:
    with tempfile.TemporaryDirectory() as directory:
        prefix = Path(directory) / f"page-{page:04d}"
        result = subprocess.run(
            [
                "pdftoppm", "-png", "-r", str(DPI), "-f", str(page), "-l", str(page),
                "-singlefile", str(pdf), str(prefix),
            ],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise BookifyError("VERIFY_FAILED", f"pdftoppm failed on page {page}", str(pdf))
        image = Path(f"{prefix}.png")
        if not image.is_file():
            raise BookifyError("VERIFY_FAILED", f"no raster for page {page}", str(pdf))
        with Image.open(image) as source:
            return np.asarray(source.convert("L"))


def _line_rows(line: captions_check.LineBox) -> tuple[int, int]:
    return int(line.y_min * SCALE), int(line.y_max * SCALE) + 1


def _measure_band(
    pdf: Path,
    page: int,
    top: float,
    bottom: float,
    canvas: Canvas,
    lines: tuple[captions_check.LineBox, ...],
    margin: float,
) -> tuple[tuple[float, float, float, bool] | None, tuple[float, float, float] | None]:
    if bottom - top < 2.0:
        return None, None
    grayscale = _raster(pdf, page)
    height = grayscale.shape[0]
    row_lo = max(0, int(top * SCALE))
    row_hi = min(height, int(bottom * SCALE))
    band = grayscale[row_lo:row_hi, :] < INK_THRESHOLD

    for line in lines:
        if line.page != page or line.y_max <= top or line.y_min >= bottom:
            continue
        text = line.text.strip()
        outside_canvas = (
            line.x_min < canvas.left - CONTAIN_TOLERANCE_PT
            or line.x_max > canvas.right + CONTAIN_TOLERANCE_PT
        )
        # Prose, notes, credits, headings and page numbers are not figure ink.
        if outside_canvas or line.x_min <= margin + 0.5 or re.fullmatch(r"\d+", text):
            start = max(0, _line_rows(line)[0] - row_lo - 1)
            end = min(band.shape[0], _line_rows(line)[1] - row_lo + 2)
            if end > start:
                band[start:end, :] = False

    columns = np.where(band.any(axis=0))[0]
    if columns.size == 0:
        return None, None
    x0 = float(columns[0]) / SCALE
    x1 = float(columns[-1]) / SCALE

    # Measure the symmetry on the ink inside the declared canvas: the prose
    # column is never part of a side figure's centre. Ink outside the canvas is
    # still reported by the containment check in `check`.
    canvas_lo = int(round(canvas.left * SCALE))
    canvas_hi = int(round(canvas.right * SCALE))
    inside = columns[(columns >= canvas_lo) & (columns <= canvas_hi)]
    if inside.size:
        centre = (float(inside[0]) + float(inside[-1])) / 2 / SCALE
    else:
        centre = (x0 + x1) / 2
    ink = (x0, x1, centre, bool(inside.size))

    left_index = columns[0]
    right_index = columns[-1]
    subtotal = band[:, left_index : right_index + 1]
    if subtotal.size == 0:
        return ink, None
    column_rules = np.where(subtotal.sum(axis=0) >= FRAME_RULE_FRACTION * subtotal.shape[0])[0]
    row_rules = np.where(subtotal.sum(axis=1) >= FRAME_RULE_FRACTION * subtotal.shape[1])[0]
    if (
        column_rules.size >= 2
        and row_rules.size >= 2
        and int(column_rules[-1]) - int(column_rules[0]) > 10
        and int(row_rules[-1]) - int(row_rules[0]) > 10
    ):
        frame_left = float(left_index + column_rules[0]) / SCALE
        frame_right = float(left_index + column_rules[-1]) / SCALE
        return ink, (frame_left, frame_right, (frame_left + frame_right) / 2)
    return ink, None


def _band_top(
    lines: tuple[captions_check.LineBox, ...],
    page: int,
    margin: float,
    previous: captions_check.CaptionMeasurement | None,
) -> float:
    if previous is not None:
        return previous.lines[-1].y_max + 1.0
    headings = [
        line
        for line in lines
        if line.page == page and line.x_min <= margin + 0.5 and line.y_max < margin + HEADING_ZONE_PT
    ]
    if headings:
        return max(line.y_max for line in headings) + 4.0
    return margin


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    """Measure every figure the manuscript declares; fail closed on any gap."""
    page_width, page_height = _page_size(pdf)
    del page_height
    margin = captions_check.page_margin(page_width)
    lines = captions_check.read_lines(pdf)
    specs = captions_check.expected_captions(manuscript)

    measurements: dict[str, captions_check.CaptionMeasurement] = {}
    problems: list[str] = []
    for spec in specs:
        outcome = captions_check.measure(spec, lines)
        if isinstance(outcome, str):
            problems.append(outcome)
        else:
            measurements[spec.block_id] = outcome
    if problems:
        return failed(
            "figure-geometry",
            "VERIFY_FAILED",
            "; ".join(problems[:4]),
            problems=problems,
        )

    by_page: dict[int, list[captions_check.CaptionMeasurement]] = {}
    for measurement in measurements.values():
        by_page.setdefault(measurement.page, []).append(measurement)
    for page in by_page:
        by_page[page].sort(key=lambda item: item.lines[0].y_min)

    figures: list[dict[str, object]] = []
    offending: list[dict[str, object]] = []
    max_ink_delta = 0.0
    max_caption_delta = 0.0
    for spec in specs:
        measurement = measurements[spec.block_id]
        canvas = _canvas(spec, page_width)
        page_measurements = by_page[measurement.page]
        position = page_measurements.index(measurement)
        previous = page_measurements[position - 1] if position > 0 else None
        top = _band_top(lines, measurement.page, margin, previous)
        bottom = measurement.lines[0].y_min - BAND_GAP_PT
        ink, frame = _measure_band(pdf, measurement.page, top, bottom, canvas, lines, margin)

        caption_delta = max(
            abs(line.delta_to(measurement.target_centre_pt)) for line in measurement.lines
        )
        max_caption_delta = max(max_caption_delta, caption_delta)
        if caption_delta > INK_TOLERANCE_PT:
            offending.append(
                {
                    "label": measurement.label,
                    "kind": spec.kind,
                    "preset": spec.preset,
                    "page": measurement.page,
                    "problem": "caption line off its declared centre",
                    "deltaPt": round(caption_delta, 2),
                }
            )

        if abs(canvas.centre - canvas.expected_centre) > CANVAS_TOLERANCE_PT:
            offending.append(
                {
                    "label": measurement.label,
                    "kind": spec.kind,
                    "page": measurement.page,
                    "problem": "declared canvas is not centred",
                }
            )

        if ink is None:
            offending.append(
                {
                    "label": measurement.label,
                    "kind": spec.kind,
                    "preset": spec.preset,
                    "page": measurement.page,
                    "problem": "figure band contains no ink",
                }
            )
            figures.append(
                {
                    "blockId": spec.block_id,
                    "label": measurement.label,
                    "kind": spec.kind,
                    "preset": spec.preset,
                    "page": measurement.page,
                    "canvas": _canvas_evidence(canvas),
                    "frame": None,
                    "ink": None,
                    "caption": _caption_evidence(measurement, caption_delta),
                }
            )
            continue

        ink_x0, ink_x1, ink_centre, inside_canvas = ink
        ink_delta = ink_centre - canvas.centre
        max_ink_delta = max(max_ink_delta, abs(ink_delta))
        contained = bool(
            inside_canvas
            and ink_x0 >= canvas.left - CONTAIN_TOLERANCE_PT
            and ink_x1 <= canvas.right + CONTAIN_TOLERANCE_PT
        )
        if abs(ink_delta) > INK_TOLERANCE_PT:
            offending.append(
                {
                    "label": measurement.label,
                    "kind": spec.kind,
                    "preset": spec.preset,
                    "page": measurement.page,
                    "problem": "visible ink off the declared canvas centre",
                    "deltaPt": round(ink_delta, 2),
                }
            )
        if not contained:
            offending.append(
                {
                    "label": measurement.label,
                    "kind": spec.kind,
                    "preset": spec.preset,
                    "page": measurement.page,
                    "problem": "visible ink leaves its declared canvas",
                    "inkLeftPt": round(ink_x0, 2),
                    "inkRightPt": round(ink_x1, 2),
                    "canvasLeftPt": round(canvas.left, 2),
                    "canvasRightPt": round(canvas.right, 2),
                }
            )

        figures.append(
            {
                "blockId": spec.block_id,
                "label": measurement.label,
                "kind": spec.kind,
                "preset": spec.preset,
                "page": measurement.page,
                "canvas": _canvas_evidence(canvas),
                "frame": None if frame is None else _interval(frame),
                "ink": {
                    "leftPt": round(ink_x0, 2),
                    "rightPt": round(ink_x1, 2),
                    "centrePt": round(ink_centre, 2),
                    "deltaPt": round(ink_delta, 2),
                    "contained": contained,
                },
                "caption": _caption_evidence(measurement, caption_delta),
            }
        )

    if offending:
        first = offending[0]
        return failed(
            "figure-geometry",
            "VERIFY_FAILED",
            f"{first['label']} on page {first['page']}: {first['problem']}",
            offending=offending,
            figures=figures,
        )

    kind_counts: dict[str, int] = {}
    for spec in specs:
        kind_counts[spec.kind] = kind_counts.get(spec.kind, 0) + 1
    return passed(
        "figure-geometry",
        f"{len(figures)} figure(s): visible ink within ±{INK_TOLERANCE_PT:g} pt of the declared centre",
        figures=figures,
        kinds=kind_counts,
        maxInkDeltaPt=round(max_ink_delta, 3),
        maxCaptionDeltaPt=round(max_caption_delta, 3),
    )


def _canvas_evidence(canvas: Canvas) -> dict[str, float]:
    return {
        "leftPt": round(canvas.left, 2),
        "rightPt": round(canvas.right, 2),
        "widthPt": round(canvas.width, 2),
        "centrePt": round(canvas.centre, 2),
        "deltaPt": round(canvas.centre - canvas.expected_centre, 2),
    }


def _interval(bounds: tuple[float, float, float]) -> dict[str, float]:
    return {
        "leftPt": round(bounds[0], 2),
        "rightPt": round(bounds[1], 2),
        "centrePt": round(bounds[2], 2),
    }


def _caption_evidence(
    measurement: captions_check.CaptionMeasurement, delta: float
) -> dict[str, object]:
    return {
        "centrePt": round(measurement.target_centre_pt, 2),
        "page": measurement.page,
        "lines": len(measurement.lines),
        "maxDeltaPt": round(delta, 3),
    }
