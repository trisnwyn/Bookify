"""Rendered descriptions: every chart, diagram, photograph, table and equation caption line is centred.

The check reads line bounding boxes from `pdftotext -bbox-layout`. It groups
caption lines by their printed label and expected text, so a Poppler block
split after a wrapped line does not hide the continuation.
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from bookify import pdf_measure
from bookify.errors import BookifyError
from bookify.design import tokens
from bookify.manuscript import model
from bookify.publish import normalize
from bookify.verify.checks import Check, failed, passed

TOLERANCE_PT = 2.0
FIGURE_KINDS = ("chart", "diagram", "illustration")
SIDE_PRESETS = ("side-left", "side-right")
HTML_NS = "http://www.w3.org/1999/xhtml"

LineBox = pdf_measure.LineBox


@dataclass(frozen=True)
class CaptionSpec:
    block_id: str
    kind: str
    label: str
    text: str
    preset: str = "full"
    credit: str | None = None
    # An authored two-column chapter (A2): the caption centres in the column it
    # occupies, not on the page.
    columns: int = 1


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


def column_bounds(index: int, page_width: float) -> tuple[float, float]:
    """One equal column of an authored two-column page, in page points."""
    from bookify.design import tokens as design_tokens

    margin = page_margin(page_width)
    width = design_tokens.COLUMN_WIDTH_PT
    gutter = design_tokens.SIDE_GUTTER_PT
    if index == 0:
        return margin, margin + width
    return margin + width + gutter, margin + width + gutter + width


def column_index(line: "LineBox", page_width: float) -> int:
    margin = page_margin(page_width)
    return 1 if line.x_min >= margin + tokens.BODY_MEASURE_PT / 2 else 0


def _in_column(index: int, line: "LineBox", page_width: float) -> bool:
    left, right = column_bounds(index, page_width)
    return line.x_min >= left - TOLERANCE_PT and line.x_max <= right + TOLERANCE_PT


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
    return pdf_measure.for_pdf(pdf).line_boxes(error_code="VERIFY_FAILED")


def expected_captions(manuscript: model.Manuscript) -> tuple[CaptionSpec, ...]:
    """The exact printed descriptions, labels and appended wording for this manuscript."""
    figure_paths = {
        block["id"]: "unused.svg"
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    }
    raw_by_id = {
        block["id"]: block
        for section in manuscript.sections
        for block in section["blocks"]
    }
    document = normalize.build(manuscript, figure_paths, draft=True)
    specs: list[CaptionSpec] = []
    columns_by_section = model.effective_columns(document.data["sections"])
    for index, section in enumerate(document.data["sections"]):
        for block in section["blocks"]:
            kind = block["type"]
            if kind in FIGURE_KINDS:
                # D5: the provenance line shares the centred caption block, so
                # the expected rendered text is description + note. Credits stay
                # separate and are measured on their own left edge.
                text = block["caption"]
                if block.get("note"):
                    text = f"{text} {block['note']}"
                specs.append(
                    CaptionSpec(
                        block_id=block["id"],
                        kind=kind,
                        label=block["label"],
                        text=text,
                        preset=block.get("composition", "full"),
                        credit=block.get("credit") if kind == "illustration" else None,
                        columns=columns_by_section[index],
                    )
                )
            elif kind == "table" and raw_by_id.get(block["id"], {}).get("caption"):
                specs.append(
                    CaptionSpec(
                        block_id=block["id"],
                        kind="table",
                        label=block["label"],
                        text=block["caption"],
                        preset="full",
                        credit=None,
                        columns=columns_by_section[index],
                    )
                )
            elif kind == "equation" and raw_by_id.get(block["id"], {}).get("caption"):
                specs.append(
                    CaptionSpec(
                        block_id=block["id"],
                        kind="equation",
                        label=block["id"],
                        text=block["caption"],
                        preset="full",
                        credit=None,
                        columns=columns_by_section[index],
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


def _measure_column(spec: CaptionSpec, lines: tuple[LineBox, ...]) -> CaptionMeasurement | str:
    """Isolate a caption inside one column of a two-column chapter (A2)."""
    candidates = [
        index
        for index, line in enumerate(lines)
        if line.text.startswith(f"{spec.label}.")
        and (_in_column(0, line, line.page_width) or _in_column(1, line, line.page_width))
    ]
    if not candidates:
        return f"{spec.label}: caption label not found in either column"
    if len(candidates) > 1:
        return f"{spec.label}: caption could not be isolated; label appears more than once"

    start_index = candidates[0]
    start = lines[start_index]
    column = column_index(start, start.page_width)
    left, right = column_bounds(column, start.page_width)
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
        if not _in_column(column, line, start.page_width):
            # Interleaved prose from the adjacent column is allowed.
            continue
        line_stream = _stream(line.text)
        if line_stream == expected[consumed : consumed + len(line_stream)]:
            collected.append(line)
            consumed += len(line_stream)

    if consumed < len(expected):
        return f"{spec.label}: caption could not be isolated in its column; expected text ended early"

    return CaptionMeasurement(
        block_id=spec.block_id,
        kind=spec.kind,
        label=spec.label,
        page=start.page,
        lines=tuple(collected),
        preset=spec.preset,
        target_centre_pt=(left + right) / 2,
    )


def _measure_equation(spec: CaptionSpec, lines: tuple[LineBox, ...]) -> CaptionMeasurement | str:
    expected = _stream(spec.text)
    if not expected:
        return f"{spec.label}: empty equation caption"
    candidates = [
        index
        for index, line in enumerate(lines)
        if _stream(line.text) and expected.startswith(_stream(line.text))
    ]
    if not candidates:
        return f"{spec.label}: equation caption not found on any page"
    last_error = f"{spec.label}: equation caption could not be isolated"
    for start_index in candidates:
        start = lines[start_index]
        collected = [start]
        consumed = len(_stream(start.text))
        matched = True
        while consumed < len(expected):
            next_index = start_index + len(collected)
            if next_index >= len(lines):
                last_error = f"{spec.label}: equation caption could not be isolated; expected text ended early"
                matched = False
                break
            line = lines[next_index]
            if line.page != start.page:
                last_error = f"{spec.label}: equation caption crosses a page boundary"
                matched = False
                break
            line_stream = _stream(line.text)
            if line_stream != expected[consumed : consumed + len(line_stream)]:
                last_error = f"{spec.label}: equation caption could not be isolated; unexpected line {line.text!r}"
                matched = False
                break
            collected.append(line)
            consumed += len(line_stream)
        if matched and consumed == len(expected):
            if spec.columns == 2:
                col = column_index(start, start.page_width)
                left, right = column_bounds(col, start.page_width)
                target = (left + right) / 2
            else:
                target = declared_centre(spec.preset, start.page_width)
            return CaptionMeasurement(
                block_id=spec.block_id,
                kind=spec.kind,
                label=spec.label,
                page=start.page,
                lines=tuple(collected),
                preset=spec.preset,
                target_centre_pt=target,
            )
    return last_error


def measure(spec: CaptionSpec, lines: tuple[LineBox, ...]) -> CaptionMeasurement | str:
    """Isolate one caption; full captions keep consecutive lines, side captions allow prose."""
    if spec.kind == "equation":
        return _measure_equation(spec, lines)
    if spec.columns == 2 and spec.preset not in SIDE_PRESETS:
        return _measure_column(spec, lines)
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
        page_width = measurement.lines[0].page_width
        column = image_column(spec.preset, page_width)
        if column is None and spec.columns == 2:
            # A column caption's credit is left-aligned in that same column.
            column = column_bounds(column_index(measurement.lines[0], page_width), page_width)
        edge = column[0] if column is not None else credit_edge(spec.preset, page_width)
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
        if measurement.kind in groups:
            shape = "single" if len(measurement.lines) == 1 else "wrapped"
            groups[measurement.kind][shape] += 1

    if require_coverage:
        # D5 merges the provenance line into the centred caption, so a chart or
        # diagram with a source note is never a single-line caption. Coverage
        # still requires both rendered shapes across the figure set.
        totals = {
            shape: sum(groups[kind][shape] for kind in FIGURE_KINDS)
            for shape in ("single", "wrapped")
        }
        missing = [shape for shape, count in totals.items() if count == 0]
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
