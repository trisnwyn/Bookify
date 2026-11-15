"""D1: definitions render inline, as one body paragraph, never as a label.

A definition is printed as `Term: definition` in body type. The check reads the
rendered rows, finds each term at body size and rejects an isolated term line at
a smaller (label/note/caption) size. A collated glossary is an ordinary table and
is outside this check.
"""

from __future__ import annotations

from pathlib import Path

from bookify.manuscript import model
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks import captions as captions_check
from bookify.verify.checks.plates import _rows

LINE_BOX_EM = 1.5217
BODY_SIZE_PT = 10.1
BODY_TOLERANCE_PT = 0.6


def _size(line: captions_check.LineBox) -> float:
    return (line.y_max - line.y_min) / LINE_BOX_EM


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    definitions = [
        (section["id"], block)
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "definition"
    ]
    if not definitions:
        return passed("definitions", "no definitions in this manuscript")

    lines = list(captions_check.read_lines(pdf))
    rows = [
        (page, _rows([line for line in lines if line.page == page]))
        for page in sorted({line.page for line in lines})
    ]

    problems: list[str] = []
    found = 0
    for _section_id, block in definitions:
        term = block["term"].strip()
        inline = [
            row
            for _page, page_rows in rows
            for row in page_rows
            if row[0].startswith(f"{term}:") or row[0].startswith(f"{term} :")
        ]
        if not inline:
            problems.append(f"{block['id']}: definition is not rendered inline as Term: definition")
            continue
        found += 1
        text, y_min, y_max = inline[0]
        size = (y_max - y_min) / LINE_BOX_EM
        if abs(size - BODY_SIZE_PT) > BODY_TOLERANCE_PT:
            problems.append(f"{block['id']}: definition renders at {size:.2f} pt, not body size")
        isolated = [
            row
            for _page, page_rows in rows
            for row in page_rows
            if row[0].strip() == term and (row[2] - row[1]) / LINE_BOX_EM < BODY_SIZE_PT - BODY_TOLERANCE_PT
        ]
        if isolated:
            problems.append(f"{block['id']}: isolated grey term label is still rendered")

    if problems:
        return failed("definitions", "VERIFY_FAILED", "; ".join(problems[:4]), problems=problems)
    return passed("definitions", f"{found} definition(s) inline at body size", count=found)
