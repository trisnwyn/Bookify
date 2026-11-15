"""D7: readability metrics and named bands, reported as warnings only.

Density is never a target and never a hard failure. Each out-of-band value is a
named warning with its measured value, band and pages; the review must answer
every warning. Exemptions (cover, contents, chapter openers, plate pages,
appendix pages) are listed with their reason, so a legitimately sparse reference
page is not counted against the book.
"""

from __future__ import annotations

from pathlib import Path

from bookify.manuscript import model
from bookify.publish import readability
from bookify.verify.checks import Check, passed, warned


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    metrics = readability.measure_manuscript(pdf, manuscript)
    warnings = metrics["warnings"]
    if warnings:
        return warned(
            "readability",
            f"{len(warnings)} readability warning(s); answer each in review notes",
            **metrics,
        )
    return passed(
        "readability",
        f"{metrics['wordsPerPage']['count']} body page(s); every density metric in band",
        **metrics,
    )
