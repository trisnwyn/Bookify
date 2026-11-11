"""Rendered figure descriptions: every chart, diagram and photograph caption line is centred.

The check reads line bounding boxes from `pdftotext -bbox-layout`. It groups
caption lines by their printed label and expected text, so a Poppler block
split after a wrapped line does not hide the continuation. Table and equation
captions are deliberately outside this check.
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from bookify.errors import BookifyError
from bookify.design import tokens
from bookify.manuscript import model
from bookify.publish import normalize
from bookify.verify.checks import Check, failed, passed

TOLERANCE_PT = 2.0
FIGURE_KINDS = ("chart", "diagram", "illustration")
SIDE_PRESETS = ("side-left", "side-right")
HTML_NS = "http://www.w3.org/1999/xhtml"


@dataclass(frozen=True)
class LineBox:
    page: int
    page_width: float
    text: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def centre(self) -> float:
        return (self.x_min + self.x_max) / 2

    @property
    def delta_pt(self) -> float:
        return self.centre - self.page_width / 2

    def delta_to(self, centre: float) -> float:
        return self.centre - centre


@dataclass(frozen=True)
class CaptionSpec:
    block_id: str
    kind: str
    label: str
    text: str
    preset: str = "full"
    credit: str | None = None


@dataclass(frozen=True)
class CaptionMeasurement:
    block_id: str
    kind: str
    label: str
    page: int
    lines: tuple[LineBox, ...]
    preset: str = "full"
    target_centre_pt: float = 0.0

    @property
    def max_delta_pt(self) -> float:
        return max(abs(line.delta_to(self.target_centre_pt)) for line in self.lines)


def page_margin(page_width: float) -> float:
    """The side margins implied by the declared body measure on this page."""
    return (page_width - tokens.BODY_MEASURE_PT) / 2


def image_column(preset: str, page_width: float) -> tuple[float, float] | None:
    """The declared image column for a side preset, in page points."""
    if preset not in SIDE_PRESETS:
        return None
    margin = page_margin(page_width)
    width = tokens.BODY_MEASURE_PT * tokens.SIDE_FRACTION
    if preset == "side-left":
        return margin, margin + width
    return margin + tokens.BODY_MEASURE_PT - width, margin + tokens.BODY_MEASURE_PT


def declared_centre(preset: str, page_width: float) -> float:
    """The required caption centre: the image column, or the page for full measure."""
    column = image_column(preset, page_width)
    if column is None:
        return page_width / 2
    return (column[0] + column[1]) / 2


def credit_edge(preset: str, page_width: float) -> float:
    """The left edge a credit starts at: the image column, or the page margin."""
    column = image_column(preset, page_width)
    if column is None:
        return page_margin(page_width)
    return column[0]


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _stream(text: str) -> str:
    """Compare rendered text as characters: CJK wraps mid-token and Poppler adds spaces."""
    return re.sub(r"[\s\u00ad]", "", text)


def read_lines(pdf: Path) -> tuple[LineBox, ...]:
    """Read every rendered text line with its page width and bounding box."""
    result = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise BookifyError("VERIFY_FAILED", "pdftotext -bbox-layout failed", str(pdf))
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as error:
        raise BookifyError("VERIFY_FAILED", f"cannot parse PDF line boxes: {error}", str(pdf)) from error

    lines: list[LineBox] = []
    for page_index, page in enumerate(root.iter(f"{{{HTML_NS}}}page"), start=1):
        width = float(page.attrib.get("width", "0"))
        for line in page.iter(f"{{{HTML_NS}}}line"):
            words = [word.text or "" for word in line.iter(f"{{{HTML_NS}}}word")]
            text = _normalise(" ".join(words))
            if not text:
                continue
            lines.append(
                LineBox(
                    page=page_index,
                    page_width=width,
                    text=text,
                    x_min=float(line.attrib["xMin"]),
                    x_max=float(line.attrib["xMax"]),
                    y_min=float(line.attrib["yMin"]),
                    y_max=float(line.attrib["yMax"]),
                )
            )
    if not lines:
        raise BookifyError("VERIFY_FAILED", "no text lines found in the PDF", str(pdf))
    return tuple(lines)


def expected_captions(manuscript: model.Manuscript) -> tuple[CaptionSpec, ...]:
    """The exact printed descriptions, labels and appended wording for this manuscript."""
    figure_paths = {
        block["id"]: "unused.svg"
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    }
    document = normalize.build(manuscript, figure_paths, draft=True)
    specs: list[CaptionSpec] = []
    for section in document.data["sections"]:
        for block in section["blocks"]:
            if block["type"] in FIGURE_KINDS:
                specs.append(
                    CaptionSpec(
                        block_id=block["id"],
                        kind=block["type"],
                        label=block["label"],
                        text=block["caption"],
                        preset=block.get("composition", "full"),
                        credit=block.get("credit") if block["type"] == "illustration" else None,
                    )
                )
    return tuple(specs)


def _measure_full(spec: CaptionSpec, lines: tuple[LineBox, ...]) -> CaptionMeasurement | str:
    start_index = next(
        (index for index, line in enumerate(lines) if line.text.startswith(f"{spec.label}.")),
        None,
    )
    if start_index is None:
        return f"{spec.label}: caption label not found on any page"

    expected = _stream(spec.text)
    start = lines[start_index]
    start_stream = _stream(start.text)
    if start_stream != expected[: len(start_stream)]:
        return f"{spec.label}: caption could not be isolated; first line does not match the stored description"

    collected = [start]
    consumed = len(start_stream)
    while consumed < len(expected):
        next_index = start_index + len(collected)
        if next_index >= len(lines):
            return f"{spec.label}: caption could not be isolated; expected text ended early"
        line = lines[next_index]
        if line.page != start.page:
            return f"{spec.label}: caption crosses a page boundary"
        line_stream = _stream(line.text)
        if line_stream != expected[consumed : consumed + len(line_stream)]:
            return f"{spec.label}: caption could not be isolated; unexpected line {line.text!r}"
        collected.append(line)
        consumed += len(line_stream)

    return CaptionMeasurement(
        block_id=spec.block_id,
        kind=spec.kind,
        label=spec.label,
        page=start.page,
        lines=tuple(collected),
        preset=spec.preset,
        target_centre_pt=declared_centre(spec.preset, start.page_width),
    )


def _inside_image_column(spec: CaptionSpec, line: LineBox, page_width: float) -> bool:
    column = image_column(spec.preset, page_width)
    if column is None:
        return True
    return (
        line.x_min >= column[0] - TOLERANCE_PT
        and line.x_max <= column[1] + TOLERANCE_PT
    )


def _measure_side(spec: CaptionSpec, lines: tuple[LineBox, ...]) -> CaptionMeasurement | str:
    candidates = [
        index
        for index, line in enumerate(lines)
        if line.text.startswith(f"{spec.label}.")
        and _inside_image_column(spec, line, line.page_width)
    ]
    if not candidates:
        return f"{spec.label}: caption label not found in its declared image column"
    if len(candidates) > 1:
        return f"{spec.label}: caption could not be isolated; label appears more than once"

    start_index = candidates[0]
    start = lines[start_index]
    expected = _stream(spec.text)
    start_stream = _stream(start.text)
    if start_stream != expected[: len(start_stream)]:
        return f"{spec.label}: caption could not be isolated; first line does not match the stored description"

    collected = [start]
    consumed = len(start_stream)
    for line in lines[start_index + 1 :]:
        if consumed >= len(expected):
            break
        if line.page != start.page:
            return f"{spec.label}: caption crosses a page boundary"
        if not _inside_image_column(spec, line, start.page_width):
            # Interleaved prose from the adjacent column is allowed.
            continue
        line_stream = _stream(line.text)
        if line_stream == expected[consumed : consumed + len(line_stream)]:
            collected.append(line)
            consumed += len(line_stream)

    if consumed < len(expected):
        return f"{spec.label}: caption could not be isolated in its image column; expected text ended early"

    return CaptionMeasurement(
        block_id=spec.block_id,
        kind=spec.kind,
        label=spec.label,
        page=start.page,
        lines=tuple(collected),
        preset=spec.preset,
        target_centre_pt=declared_centre(spec.preset, start.page_width),
    )


def measure(spec: CaptionSpec, lines: tuple[LineBox, ...]) -> CaptionMeasurement | str:
    """Isolate one caption; full captions keep consecutive lines, side captions allow prose."""
    if spec.preset in SIDE_PRESETS:
        return _measure_side(spec, lines)
    return _measure_full(spec, lines)


def measure_credit(
    spec: CaptionSpec, lines: tuple[LineBox, ...], measurement: CaptionMeasurement
) -> tuple[LineBox, ...] | str:
    """Isolate an illustration credit in the same column as its caption."""
    if not spec.credit:
        return ()
    expected = _stream(spec.credit)
    page_lines = [line for line in lines if line.page == measurement.page]
    start_index = next(
        (
            index
            for index, line in enumerate(page_lines)
            if _stream(line.text) and expected.startswith(_stream(line.text))
        ),
        None,
    )
    if start_index is None:
        # The record credit is not on this page. Its presence is a text probe;
        # the geometry check only measures a credit it can actually see.
        return ()
    collected = [page_lines[start_index]]
    consumed = len(_stream(collected[0].text))
    if consumed > len(expected):
        return f"{spec.label}: credit could not be isolated"
    for line in page_lines[start_index + 1 :]:
        if consumed >= len(expected):
            break
        if spec.preset in SIDE_PRESETS and not _inside_image_column(spec, line, measurement.lines[0].page_width):
            continue
        line_stream = _stream(line.text)
        if line_stream == expected[consumed : consumed + len(line_stream)]:
            collected.append(line)
            consumed += len(line_stream)
    if consumed < len(expected):
        return f"{spec.label}: credit could not be isolated; expected text ended early"
    return tuple(collected)


def check(
    pdf: Path,
    manuscript: model.Manuscript,
    *,
    require_coverage: bool = False,
) -> Check:
    lines = read_lines(pdf)
    specs = expected_captions(manuscript)

    measurements: list[CaptionMeasurement] = []
    problems: list[str] = []
    for spec in specs:
        outcome = measure(spec, lines)
        if isinstance(outcome, str):
            problems.append(outcome)
        else:
            measurements.append(outcome)
    if problems:
        return failed(
            "captions",
            "VERIFY_FAILED",
            "; ".join(problems[:4]),
            problems=problems,
        )

    offending: list[dict[str, object]] = []
    deltas: list[float] = []
    for measurement in measurements:
        for line in measurement.lines:
            delta = line.delta_to(measurement.target_centre_pt)
            deltas.append(abs(delta))
            if abs(delta) > TOLERANCE_PT:
                offending.append(
                    {
                        "label": measurement.label,
                        "preset": measurement.preset,
                        "page": measurement.page,
                        "text": line.text,
                        "centre": round(line.centre, 2),
                        "targetCentre": round(measurement.target_centre_pt, 2),
                        "deltaPt": round(delta, 2),
                    }
                )
    if offending:
        first = offending[0]
        return failed(
            "captions",
            "VERIFY_FAILED",
            f"{first['label']} has a caption line off centre on page {first['page']}: {first['deltaPt']} pt",
            offending=offending,
        )

    by_label = {measurement.label: measurement for measurement in measurements}
    credit_offending: list[dict[str, object]] = []
    credit_deltas: list[float] = []
    for spec in specs:
        measurement = by_label.get(spec.label)
        if measurement is None or not spec.credit:
            continue
        outcome = measure_credit(spec, lines, measurement)
        if isinstance(outcome, str):
            problems.append(outcome)
            continue
        edge = credit_edge(spec.preset, measurement.lines[0].page_width)
        column = image_column(spec.preset, measurement.lines[0].page_width)
        book_page = abs(
            measurement.lines[0].page_width
            - (tokens.BODY_MEASURE_PT + 2 * tokens.PAGE_MARGIN_PT)
        ) <= 1.0
        for line in outcome:
            if column is not None and line.x_max > column[1] + TOLERANCE_PT:
                credit_offending.append(
                    {
                        "label": measurement.label,
                        "preset": measurement.preset,
                        "page": measurement.page,
                        "credit": line.text,
                        "xMax": round(line.x_max, 2),
                        "edge": round(column[1], 2),
                        "deltaPt": round(line.x_max - column[1], 2),
                    }
                )
                continue
            if spec.preset not in SIDE_PRESETS and not book_page:
                # A synthetic page wider/narrower than the book measure: the
                # declared 60 pt margin cannot be assumed. Keep the left rule.
                if line.x_min > line.page_width / 3:
                    credit_offending.append(
                        {
                            "label": measurement.label,
                            "preset": measurement.preset,
                            "page": measurement.page,
                            "credit": line.text,
                            "xMin": round(line.x_min, 2),
                            "edge": "left third",
                            "deltaPt": round(line.x_min - line.page_width / 3, 2),
                        }
                    )
                continue
            delta = line.x_min - edge
            credit_deltas.append(abs(delta))
            if abs(delta) > TOLERANCE_PT:
                credit_offending.append(
                    {
                        "label": measurement.label,
                        "preset": measurement.preset,
                        "page": measurement.page,
                        "credit": line.text,
                        "xMin": round(line.x_min, 2),
                        "edge": round(edge, 2),
                        "deltaPt": round(delta, 2),
                    }
                )
    if problems:
        return failed(
            "captions",
            "VERIFY_FAILED",
            "; ".join(problems[:4]),
            problems=problems,
        )
    if credit_offending:
        first = credit_offending[0]
        return failed(
            "captions",
            "VERIFY_FAILED",
            f"{first['label']} has a credit off its declared left edge on page {first['page']}: "
            f"{first['deltaPt']} pt",
            offending=credit_offending,
        )

    groups: dict[str, dict[str, int]] = {
        kind: {"single": 0, "wrapped": 0} for kind in FIGURE_KINDS
    }
    for measurement in measurements:
        shape = "single" if len(measurement.lines) == 1 else "wrapped"
        groups[measurement.kind][shape] += 1

    if require_coverage:
        missing = [
            f"{kind} {shape}"
            for kind in FIGURE_KINDS
            for shape in ("single", "wrapped")
            if groups[kind][shape] == 0
        ]
        if missing:
            return failed(
                "captions",
                "VERIFY_FAILED",
                f"caption coverage missing: {', '.join(missing)}",
                groups=groups,
            )

    max_delta = max(deltas, default=0.0)
    max_credit_delta = max(credit_deltas, default=0.0)
    return passed(
        "captions",
        f"{len(measurements)} figure caption(s) centred within ±{TOLERANCE_PT:g} pt",
        groups=groups,
        maxDeltaPt=round(max_delta, 3),
        maxCreditDeltaPt=round(max_credit_delta, 3),
        captions=[
            {
                "blockId": measurement.block_id,
                "kind": measurement.kind,
                "label": measurement.label,
                "preset": measurement.preset,
                "page": measurement.page,
                "lines": len(measurement.lines),
                "targetCentrePt": round(measurement.target_centre_pt, 3),
                "maxDeltaPt": round(measurement.max_delta_pt, 3),
            }
            for measurement in measurements
        ],
    )
