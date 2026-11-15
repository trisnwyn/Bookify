"""Contents folios, heading numbers and figure/table numbering."""

from __future__ import annotations

import re
from pathlib import Path

from bookify.manuscript import model
from bookify.publish import normalize
from bookify.publish.report import contents_pages, grouped_page_lines
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks.pages import numbered_labels, page_texts

CONTENTS_LINE = re.compile(r"^\s*(?P<title>.+?)\s+(?:\.\s*){2,}(?P<page>\d+)\s*$")
# A printed number at the start of a contents entry or body heading: `1`,
# `1.1.1`, `A.1` or `Appendix A`.
PRINTED = re.compile(r"^\s*(?P<number>Appendix [A-Z]+|\d+(?:\.\d+)*|[A-Z]+(?:\.\d+)*)\s+(?P<title>.*)$")
LABEL = re.compile(r"^(Figure|Table|Photograph) (\d+)\.")
REFERENCE = re.compile(r"§\s*(Appendix [A-Z]+|\d+(?:\.\d+)*|[A-Z]+(?:\.\d+)*)")


def _strip_printed(title: str) -> tuple[str | None, str]:
    """Split an optional printed number off a contents or heading line."""
    match = PRINTED.match(title)
    if not match:
        return None, title.strip()
    return match.group("number"), match.group("title").strip()


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    texts = page_texts(pdf)
    contents = contents_pages(texts)
    if not contents:
        return failed("xrefs", "XREF_MISSING", "contents page not found")

    numbers = normalize.section_numbers(manuscript)
    expected: dict[str, dict[str, str]] = {}
    for section, item in zip(manuscript.sections, numbers):
        expected[section["title"]] = item

    grouped_cache: dict[int, list[str]] = {}

    def page_grouped(index: int) -> list[str]:
        if index not in grouped_cache:
            grouped_cache[index] = grouped_page_lines(pdf, index)
        return grouped_cache[index]

    section_pages: dict[str, int] = {}
    for section in manuscript.sections:
        wanted = {section["title"]}
        printed = expected[section["title"]]["printed"]
        wanted.add(f"{printed} {section['title']}")
        section_pages[section["title"]] = next(
            (
                index
                for index in range(1, len(texts) + 1)
                if index != 1 and index not in contents
                and any(line.strip() in wanted for line in page_grouped(index))
            ),
            0,
        )

    problems: list[str] = []
    listed = 0
    for contents_page in sorted(contents):
        for line in texts[contents_page - 1].splitlines():
            line = line.replace("\u2060", "").replace("\u00a0", " ")
            match = CONTENTS_LINE.match(line)
            if not match:
                continue
            number, title = _strip_printed(match.group("title"))
            printed = int(match.group("page"))
            listed += 1
            actual = section_pages.get(title)
            if actual is None:
                problems.append(f"contents lists unknown section: {title}")
                continue
            if number is None:
                problems.append(f"contents entry is unnumbered: {title}")
            elif number != expected[title]["printed"]:
                problems.append(f"{title}: contents number {number}, expected {expected[title]['printed']}")
            if actual != printed:
                problems.append(f"{title}: contents says {printed}, printed on {actual}")
    if listed != len(section_pages):
        problems.append(f"contents lists {listed} sections, manuscript has {len(section_pages)}")

    # Body headings print the same number the contents lists.
    for section in manuscript.sections:
        page = section_pages.get(section["title"], 0)
        if not page:
            continue
        printed = expected[section["title"]]["printed"]
        pages = page_grouped(page)
        stripped = [line.strip() for line in pages]
        combined = f"{printed} {section['title']}"
        # A chapter opener prints the number and title on separate rows; a
        # level-2/3 heading prints them on one. In both cases the number must be
        # present — a bare title that lost its number is a defect.
        has_combined = any(line == combined for line in stripped)
        has_title = any(line == section["title"] for line in stripped)
        has_number = any(line == printed for line in stripped)
        if not (has_combined or (has_title and has_number)):
            problems.append(f"{section['title']}: printed heading has no number {printed}")

    labels = numbered_labels(texts)
    for prefix in ("Figure", "Table", "Photograph"):
        counts = sorted(int(label.split()[1]) for label in labels if label.startswith(prefix))
        if counts and counts != list(range(1, len(counts) + 1)):
            problems.append(f"{prefix} numbering is not sequential: {counts}")

    allowed = {item["number"] for item in numbers}
    body_text = "\n".join(texts)
    for reference in REFERENCE.finditer(body_text):
        if reference.group(1) not in allowed:
            problems.append(f"cross-reference prints an unknown number: §{reference.group(1)}")

    if problems:
        return failed("xrefs", "XREF_MISSING", "; ".join(problems), problems=problems)
    return passed("xrefs", f"{listed} numbered contents entries match pages; numbering sequential")
