"""One place for the untrusted-PDF caps (SPEC-bookify-v2 §3.9).

The caps are shared by the extraction preflight, the OCR page planner and the
engine harness tests. They are enforced *before* work starts so an oversized
source fails with `INPUT_INVALID` rather than after minutes of extraction.
"""

from __future__ import annotations

CAP_PDF_BYTES = 512 * 1024 * 1024
CAP_PAGES = 1000
CAP_PAGE_PIXELS = 50_000_000
CAP_REGION_PIXELS = 40_000_000
CAP_REGIONS_PER_PAGE = 12
CAP_TSV_BYTES = 8 * 1024 * 1024
CAP_WORDS = 20_000
CAP_LINES = 5_000

__all__ = [
    "CAP_LINES",
    "CAP_PAGES",
    "CAP_PAGE_PIXELS",
    "CAP_PDF_BYTES",
    "CAP_REGIONS_PER_PAGE",
    "CAP_REGION_PIXELS",
    "CAP_TSV_BYTES",
    "CAP_WORDS",
]
