"""Two builds must share layout facts; bytes need not match."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks.pages import illustration_pages, numbered_labels, page_texts


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(first: Path, second: Path | None) -> Check:
    if second is None:
        return failed("determinism", "BUILD_FAILED", "no comparison build supplied")
    first_texts = page_texts(first)
    second_texts = page_texts(second)
    if len(first_texts) != len(second_texts):
        return failed(
            "determinism", "BUILD_FAILED",
            f"page count differs: {len(first_texts)} vs {len(second_texts)}",
            first=len(first_texts), second=len(second_texts),
        )
    if first_texts != second_texts:
        differing = [index for index, (a, b) in enumerate(zip(first_texts, second_texts), start=1) if a != b]
        return failed("determinism", "BUILD_FAILED", f"page text differs on {differing}", pages=differing)
    if illustration_pages(first_texts) != illustration_pages(second_texts):
        return failed("determinism", "BUILD_FAILED", "illustration page map differs")
    if numbered_labels(first_texts) != numbered_labels(second_texts):
        return failed("determinism", "BUILD_FAILED", "figure/table numbering differs")
    bytes_equal = _sha(first) == _sha(second)
    detail = "layout facts identical" + ("; bytes identical" if bytes_equal else "; bytes differ (allowed)")
    return passed("determinism", detail, bytesEqual=bytes_equal, pages=len(first_texts))
