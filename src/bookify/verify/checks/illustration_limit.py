"""The hard one-illustration-per-page limit, read from the PDF itself."""

from __future__ import annotations

from pathlib import Path

from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks.pages import illustration_pages, page_texts


def check(pdf: Path) -> Check:
    pages = illustration_pages(page_texts(pdf))
    offending = {page: labels for page, labels in pages.items() if len(labels) > 1}
    if offending:
        return failed(
            "illustration-limit", "ILLUSTRATION_LIMIT",
            f"pages with more than one illustration: {sorted(offending)}",
            offending=offending,
        )
    total = sum(len(labels) for labels in pages.values())
    return passed("illustration-limit", f"{total} illustration(s), at most one per page", pages=pages)
