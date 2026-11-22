"""Contents folios, heading numbers and figure/table numbering."""

from __future__ import annotations

import re
from pathlib import Path

from bookify.manuscript import model
from bookify.publish import normalize, report
from bookify.publish.report import contents_pages, grouped_page_lines
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks.pages import numbered_labels, page_texts

CONTENTS_LINE = re.compile(r"^\s*(?P<title>.+?)\s+(?:\.\s*){2,}(?P<page>\d+)\s*$")
# A printed number at the start of a contents entry or body heading: `1`,
# `1.1.1`, `A.1` or `Appendix A`.
PRINTED = re.compile(r"^\s*(?P<number>Appendix [A-Z]+|\d+(?:\.\d+)*\.?|[A-Z]+(?:\.\d+)*\.?)\s+(?P<title>.*)$")
LABEL = re.compile(r"^(Figure|Table|Photograph) (\d+)\.")
REFERENCE = re.compile(r"§\s*(Appendix [A-Z]+|\d+(?:\.\d+)*\.?|[A-Z]+(?:\.\d+)*\.?)")


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
        number = expected[section["title"]]
        document_section = {
            "printed": number["printed"],
            "level": number["level"],
            "role": number["role"],
            "title": section["title"],
            "heading": normalize.section_heading(number, section["title"]),
        }
        section_pages[section["title"]] = next(
            (
                index
                for index in range(1, len(texts) + 1)
                if index != 1 and index not in contents
                and any(report.line_is_section(line, document_section) for line in page_grouped(index))
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
        number = expected[section["title"]]
        printed = number["printed"]
        pages = page_grouped(page)
        stripped = [line.strip() for line in pages]
        # A chapter prints `Chapter 1: Title` on one line; a body heading prints
        # `1.1 Title`. A heading that wraps shows only its number on the first
        # row, so the printed number prefix is enough there. The bare retired
        # opener (number alone, then title) also still satisfies the rule, but a
        # title that lost its number is a defect.
        heading = normalize.section_heading(number, section["title"])
        document_section = {
            "printed": printed,
            "level": number["level"],
            "role": number["role"],
            "title": section["title"],
            "heading": heading,
        }
        prefix = report.section_prefix(document_section)
        has_combined = any(line == heading for line in stripped) or any(
            line == f"{printed} {section['title']}" for line in stripped
        )
        # A wrapped heading keeps both its number and its full title on the page,
        # split across rows; the stream comparison ignores the row break.
        joined = re.sub(r"[\s\u00ad]", "", " ".join(stripped))
        has_prefix = (
            bool(prefix)
            and any(line.startswith(prefix) for line in stripped)
            and re.sub(r"[\s\u00ad]", "", section["title"]) in joined
        )
        has_title = any(line == section["title"] for line in stripped)
        has_number = any(line == printed for line in stripped)
        if not (has_combined or has_prefix or (has_title and has_number)):
            problems.append(f"{section['title']}: printed heading has no number {printed}")

    labels = numbered_labels(texts)
    for prefix in ("Figure", "Table", "Photograph"):
        counts = sorted(int(label.split()[1]) for label in labels if label.startswith(prefix))
        if counts and counts != list(range(1, len(counts) + 1)):
            problems.append(f"{prefix} numbering is not sequential: {counts}")

    allowed = {item["number"] for item in numbers}
    body_text = "\n".join(texts)
    for reference in REFERENCE.finditer(body_text):
        raw = reference.group(1)
        # A reference may be followed by sentence punctuation. Numbers never end
        # with a period, so the exact form wins when it exists and the stripped
        # form is the same reference plus a full stop.
        candidates = [raw]
        if raw.endswith("."):
            candidates.append(raw[:-1])
        else:
            candidates.append(raw + ".")
        resolved = next((candidate for candidate in candidates if candidate in allowed), None)
        if resolved is None:
            problems.append(f"cross-reference prints an unknown number: §{raw}")

    if problems:
        return failed("xrefs", "XREF_MISSING", "; ".join(problems), problems=problems)
    return passed("xrefs", f"{listed} numbered contents entries match pages; numbering sequential")
