"""Contents folios and figure/table numbering."""

from __future__ import annotations

import re
from pathlib import Path

from bookify.manuscript import model
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks.pages import numbered_labels, page_texts

CONTENTS_LINE = re.compile(r"^\s*(?P<title>.+?)\s+(?:\.\s*){2,}(?P<page>\d+)\s*$")
LABEL = re.compile(r"^(Figure|Table|Photograph) (\d+)\.")


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    texts = page_texts(pdf)
    contents_page = next(
        (index for index, text in enumerate(texts, start=1) if "Contents" in text and "..." in text.replace(" ", "")),
        None,
    )
    if contents_page is None:
        return failed("xrefs", "XREF_MISSING", "contents page not found")

    section_pages: dict[str, int] = {}
    for section in manuscript.sections:
        section_pages[section["title"]] = next(
            (
                index
                for index, text in enumerate(texts, start=1)
                if index != 1 and index != contents_page
                and any(line.strip() == section["title"] for line in text.splitlines())
            ),
            0,
        )

    problems: list[str] = []
    listed = 0
    for line in texts[contents_page - 1].splitlines():
        line = line.replace("\u2060", "").replace("\u00a0", " ")
        match = CONTENTS_LINE.match(line)
        if not match:
            continue
        title = match.group("title").strip()
        printed = int(match.group("page"))
        listed += 1
        actual = section_pages.get(title)
        if actual is None:
            problems.append(f"contents lists unknown section: {title}")
        elif actual != printed:
            problems.append(f"{title}: contents says {printed}, printed on {actual}")
    if listed != len(section_pages):
        problems.append(f"contents lists {listed} sections, manuscript has {len(section_pages)}")

    labels = numbered_labels(texts)
    for prefix in ("Figure", "Table", "Photograph"):
        numbers = sorted(int(label.split()[1]) for label in labels if label.startswith(prefix))
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            problems.append(f"{prefix} numbering is not sequential: {numbers}")

    if problems:
        return failed("xrefs", "XREF_MISSING", "; ".join(problems), problems=problems)
    return passed("xrefs", f"{listed} contents entries match pages; numbering sequential")
