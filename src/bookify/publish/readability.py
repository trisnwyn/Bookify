"""D7: readability metrics and named bands, measured from the rendered book.

Density is evidence, not a target: a dense reference page may be correct and a
sparse plate page may be correct. Every metric here is reported with its pages
and band; verify turns an out-of-band value into a warning for review, never a
hard failure.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bookify import pdf_measure
from bookify.manuscript import model
from bookify.publish import normalize, report

WORD = re.compile(r"[^\s]+")
LABEL = re.compile(r"^(Figure|Table|Photograph) (\d+)\.")
PROSE_TYPES = ("paragraph", "lead", "quote", "definition")


def page_texts(pdf: Path) -> list[str]:
    return pdf_measure.for_pdf(pdf).page_texts(error_code="BUILD_FAILED")


def numbered_labels(texts: list[str]) -> dict[str, int]:
    labels: dict[str, int] = {}
    for page, text in enumerate(texts, start=1):
        for line in text.splitlines():
            match = LABEL.match(line.strip())
            if match:
                labels.setdefault(f"{match.group(1)} {match.group(2)}", page)
    return labels

BANDS = {
    "wordsPerPageMedian": (140.0, 650.0),
    "wordsPerPageFloor": 60.0,
    "wordsPerPageCeiling": 800.0,
    "tablesPerPageMax": 2,
    "paragraphWordsMedianMax": 150.0,
    "paragraphWordsMax": 240.0,
    "denseWords": 650.0,
    "denseRunMax": 3,
}


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def _words(text: str) -> int:
    return sum(1 for token in WORD.findall(text) if re.search(r"[0-9A-Za-z\u00c0-\u024f\u3040-\u30ff\u4e00-\u9fff]", token))


def _prose_words(document: dict[str, Any]) -> list[int]:
    counts: list[int] = []
    for section in document["sections"]:
        for block in section["blocks"]:
            if block["type"] not in PROSE_TYPES:
                continue
            if block["type"] == "definition":
                text = f"{block.get('term', '')} {block.get('definition', '')}"
            else:
                text = block.get("text", "")
            if text.strip():
                counts.append(_words(text))
    return counts


def exempt_pages(
    document: dict[str, Any],
    contents: set[int],
    plates: list[dict[str, Any]],
    total_pages: int | None = None,
) -> dict[int, str]:
    """Pages excluded from the thin-page warning, with the reason."""
    exemptions: dict[int, str] = {1: "cover"}
    for page in contents:
        exemptions[page] = "contents"
    ordered = [section for section in document["sections"] if section.get("page") is not None]
    for index, section in enumerate(ordered):
        if section.get("level", 1) != 1:
            continue
        start = section["page"]
        end = next(
            (
                later["page"]
                for later in ordered[index + 1 :]
                if later.get("level", 1) == 1 and later["page"] > start
            ),
            None,
        )
        reason = "chapter opener"
        exemptions[start] = reason
        if section.get("role") == "appendix":
            # The exemption is the whole appendix range, not only its opener.
            stop = end if end is not None else (total_pages or start) + 1
            for page in range(start, stop):
                exemptions[page] = "appendix"
    for plate in plates:
        page = plate.get("page")
        if page is not None:
            exemptions.setdefault(int(page), "plate page")
    return exemptions


def measure(pdf: Path, document: dict[str, Any]) -> dict[str, Any]:
    texts = page_texts(pdf)
    numbered = numbered_labels(texts)
    contents = report.contents_pages(texts)
    plates, _gaps, _visuals = report.plate_entries(pdf, document, numbered)

    # Recompute the section page map using the cached batch bbox lines without
    # mutating the caller's document dict.
    sections_with_pages: list[dict[str, Any]] = []
    for section in document["sections"]:
        page = next(
            (
                index
                for index in range(1, len(texts) + 1)
                if index != 1
                and index not in contents
                and any(
                    report.line_is_section(line, section)
                    for line in report.grouped_page_lines(pdf, index)
                )
            ),
            None,
        )
        sections_with_pages.append({**section, "page": page})

    exemptions = exempt_pages({"sections": sections_with_pages}, contents, plates, len(texts))
    tables_by_page: dict[int, int] = {}
    for page, text in enumerate(texts, start=1):
        tables_by_page[page] = len(re.findall(r"(?m)^Table \d+\.", text))

    body_pages = [
        page
        for page in range(1, len(texts) + 1)
        if page not in contents and page != 1
    ]
    words_by_page = {page: _words(texts[page - 1]) for page in body_pages}
    medians = _median([float(count) for count in words_by_page.values()])

    warnings: list[dict[str, Any]] = []
    if words_by_page and not (BANDS["wordsPerPageMedian"][0] <= medians <= BANDS["wordsPerPageMedian"][1]):
        warnings.append(
            {
                "id": "readability:wordsPerPage:median",
                "metric": "wordsPerPage",
                "value": medians,
                "band": list(BANDS["wordsPerPageMedian"]),
                "pages": sorted(words_by_page),
            }
        )
    for page, count in words_by_page.items():
        if page in exemptions:
            continue
        if count > BANDS["wordsPerPageCeiling"]:
            warnings.append(
                {
                    "id": f"readability:wordsPerPage:page={page}",
                    "metric": "wordsPerPage",
                    "value": count,
                    "band": [0, BANDS["wordsPerPageCeiling"]],
                    "pages": [page],
                }
            )
        elif count < BANDS["wordsPerPageFloor"]:
            warnings.append(
                {
                    "id": f"readability:wordsPerPage:page={page}",
                    "metric": "wordsPerPage",
                    "value": count,
                    "band": [BANDS["wordsPerPageFloor"], None],
                    "pages": [page],
                }
            )
    for page, count in tables_by_page.items():
        if count > BANDS["tablesPerPageMax"]:
            warnings.append(
                {
                    "id": f"readability:tablesPerPage:page={page}",
                    "metric": "tablesPerPage",
                    "value": count,
                    "band": [0, BANDS["tablesPerPageMax"]],
                    "pages": [page],
                }
            )

    paragraph_words = _prose_words(document)
    paragraph_median = _median([float(count) for count in paragraph_words])
    paragraph_max = max(paragraph_words, default=0)
    if paragraph_median > BANDS["paragraphWordsMedianMax"]:
        warnings.append(
            {
                "id": "readability:paragraphWords:median",
                "metric": "paragraphWords",
                "value": paragraph_median,
                "band": [0, BANDS["paragraphWordsMedianMax"]],
                "pages": [],
            }
        )
    if paragraph_max > BANDS["paragraphWordsMax"]:
        warnings.append(
            {
                "id": "readability:paragraphWords:max",
                "metric": "paragraphWords",
                "value": paragraph_max,
                "band": [0, BANDS["paragraphWordsMax"]],
                "pages": [],
            }
        )

    dense_pages = sorted(page for page, count in words_by_page.items() if count > BANDS["denseWords"])
    longest: list[int] = []
    run: list[int] = []
    for page in dense_pages:
        if run and page == run[-1] + 1:
            run.append(page)
        else:
            run = [page]
        if len(run) > len(longest):
            longest = list(run)
    if len(longest) > BANDS["denseRunMax"]:
        warnings.append(
            {
                "id": f"readability:consecutiveDensePages:run={longest[0]}-{longest[-1]}",
                "metric": "consecutiveDensePages",
                "value": len(longest),
                "band": [0, BANDS["denseRunMax"]],
                "pages": longest,
            }
        )

    return {
        "bands": BANDS,
        "wordsPerPage": {
            "median": medians,
            "count": len(words_by_page),
            "pages": {str(page): count for page, count in sorted(words_by_page.items())},
        },
        "tablesPerPage": {
            "max": max(tables_by_page.values(), default=0),
            "pages": {str(page): count for page, count in sorted(tables_by_page.items()) if count},
        },
        "paragraphWords": {
            "median": paragraph_median,
            "max": paragraph_max,
            "count": len(paragraph_words),
        },
        "consecutiveDensePages": {"longestRun": len(longest), "pages": longest},
        "exemptions": [
            {"page": page, "reason": reason} for page, reason in sorted(exemptions.items())
        ],
        "warnings": warnings,
    }


def measure_manuscript(pdf: Path, manuscript: model.Manuscript) -> dict[str, Any]:
    figure_paths = {
        block["id"]: "unused.svg"
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    }
    document = normalize.build(manuscript, figure_paths, draft=True)
    return measure(pdf, document.data)
