"""The PDF's own identity: title, author, language and any declared standard.

WeasyPrint's ``pdf/metadata.py``, ``pdf/pdfa.py`` and ``pdf/pdfua.py`` are the
reference for which fields a conforming file must carry; this check verifies the
fields instead of writing them. It is read-only over the built PDF and compares
it with the manuscript that produced it, so a file that describes some other book
cannot pass.

Two deliberate limits, both recorded rather than guessed:

- the declared document language is evidence, not a gate. Typst sets it through
  ``text(lang:)``, which changes line breaking, so requiring it here would move
  every page baseline. The mismatch is visible in the report until that work
  lands.
- the structural obligations of a declared standard (output intent, tag tree)
  are checked only when the file claims the standard. Bookify does not pass
  ``--pdf-standard`` today, so a file that claims nothing is not penalised.
"""

from __future__ import annotations

import subprocess
import unicodedata
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from bookify.manuscript import model
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks.pages import pdf_info

NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "pdfaid": "http://www.aiim.org/pdfa/ns/id/",
    "pdfuaid": "http://www.aiim.org/pdfua/ns/id/",
}
CONFORMANCE = {"A", "B", "U", "E", "F"}


def _flat(value: str | None) -> str:
    """Compare metadata the way a reader sees it: one line, one normal form."""
    if value is None:
        return ""
    collapsed = " ".join(value.split())
    return unicodedata.normalize("NFC", collapsed).strip()


def _xmp(pdf: Path) -> ElementTree.Element | None:
    """The XMP packet, or None when the file carries none."""
    result = subprocess.run(
        ["pdfinfo", "-meta", str(pdf)], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return None
    text = result.stdout
    start = text.find("<x:xmpmeta")
    end = text.rfind("</x:xmpmeta>")
    if start < 0 or end < 0:
        return None
    try:
        return ElementTree.fromstring(text[start : end + len("</x:xmpmeta>")])
    except ElementTree.ParseError:
        return None


def _values(root: ElementTree.Element | None, path: str) -> list[str]:
    """Every text value under an RDF container (Alt, Seq or Bag)."""
    if root is None:
        return []
    items: list[ElementTree.Element] = []
    for container in ("rdf:Alt", "rdf:Seq", "rdf:Bag"):
        items.extend(root.findall(f"{path}/{container}/rdf:li", NS))
    if not items:
        node = root.find(path, NS)
        if node is None:
            return []
        text = _flat("".join(node.itertext()))
        return [text] if text else []
    return [text for text in (_flat("".join(item.itertext())) for item in items) if text]


def _text(root: ElementTree.Element | None, path: str) -> str | None:
    if root is None:
        return None
    node = root.find(path, NS)
    if node is None:
        return None
    return _flat("".join(node.itertext())) or None


def _primary(tag: str) -> str:
    return tag.replace("_", "-").split("-")[0].lower()


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    metadata = manuscript.data["metadata"]
    info = pdf_info(pdf)
    root = _xmp(pdf)

    expected_title = _flat(metadata["title"])
    expected_author = _flat(metadata.get("author"))
    expected_languages = [str(language) for language in metadata["languages"]]

    info_title = _flat(info.get("Title"))
    xmp_titles = _values(root, ".//dc:title")
    info_author = _flat(info.get("Author"))
    xmp_authors = _values(root, ".//dc:creator")

    titles = [value for value in (info.get("Title"), *xmp_titles) if value]
    authors = [value for value in (info.get("Author"), *xmp_authors) if value]
    languages = _values(root, ".//dc:language")

    declared_title = _flat(titles[0]) if titles else ""
    declared_author = _flat(authors[0]) if authors else ""

    claimed = {
        "part": _text(root, ".//pdfaid:part"),
        "conformance": _text(root, ".//pdfaid:conformance"),
        "ua": _text(root, ".//pdfuaid:part"),
    }
    tagged = info.get("Tagged", "no")

    evidence = {
        "title": declared_title,
        "author": declared_author,
        "languages": languages,
        "expectedLanguages": expected_languages,
        "languagesCovered": bool(languages)
        and set(map(_primary, expected_languages)) <= set(map(_primary, languages)),
        "standard": claimed,
        "tagged": tagged,
        "pdfVersion": info.get("PDF version"),
        "xmp": root is not None,
    }

    problems: list[str] = []
    if not declared_title:
        problems.append("the file declares no title")
    elif declared_title != expected_title:
        problems.append(f"title is {declared_title!r}, manuscript says {expected_title!r}")
    if info_title and xmp_titles and info_title != xmp_titles[0]:
        problems.append(f"Info title {info_title!r} disagrees with XMP dc:title {xmp_titles[0]!r}")

    if expected_author and not declared_author:
        problems.append(f"the file declares no author, manuscript says {expected_author!r}")
    elif not expected_author and declared_author:
        problems.append(f"the file invents an author {declared_author!r}")
    elif expected_author and declared_author != expected_author:
        problems.append(f"author is {declared_author!r}, manuscript says {expected_author!r}")
    if info_author and xmp_authors and info_author != xmp_authors[0]:
        problems.append(f"Info author {info_author!r} disagrees with XMP dc:creator {xmp_authors[0]!r}")

    if problems:
        return failed(
            "docmeta",
            "BUILD_FAILED",
            "the PDF does not describe this book: " + "; ".join(problems),
            **evidence,
        )

    if claimed["part"] and claimed["conformance"] not in CONFORMANCE:
        return failed(
            "docmeta",
            "BUILD_FAILED",
            f"PDF/A part {claimed['part']} is claimed without a valid conformance level",
            **evidence,
        )
    if claimed["part"] and b"/OutputIntent" not in pdf.read_bytes():
        return failed(
            "docmeta",
            "BUILD_FAILED",
            "PDF/A is claimed but the file carries no /OutputIntent",
            **evidence,
        )
    if claimed["ua"] and tagged != "yes":
        return failed(
            "docmeta",
            "BUILD_FAILED",
            "PDF/UA is claimed but the file is not tagged",
            **evidence,
        )

    identity = "title and author match the manuscript" if expected_author else "title matches the manuscript"
    standard = f"; PDF/A-{claimed['part']}{claimed['conformance'].lower()} claimed" if claimed["part"] else ""
    return passed("docmeta", identity + standard, **evidence)
