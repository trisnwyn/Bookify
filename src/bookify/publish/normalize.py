"""Normalize a validated manuscript into the document model Typst consumes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bookify.manuscript import model
from bookify.publish import rights

REF = re.compile(r"\{ref:([a-z0-9][a-z0-9-]*)\}")


@dataclass(frozen=True)
class Document:
    data: dict[str, Any]
    labels: dict[str, str]


def appendix_letter(index: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA. Mirrors the Typst numbering function."""
    letters = ""
    value = index
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def section_numbers(manuscript: model.Manuscript) -> list[dict[str, Any]]:
    """The printed number of every section, in document order.

    The hierarchy is the one the page shows, level by level: `Chapter 1: Title`
    → `1.1 Heading` → `1.1.1 Subheading` → terminal `1.1.1 a)` → continuing
    `1.1.1.1`, `1.1.1.1.1`. The chapter stem is the printed chapter number
    (`1`, `2`) or the appendix letter (`A`), so a body heading never repeats the
    chapter word and an appendix child prints `A.1`.

    Every level carries the path to itself, which is why no number ends with a
    period: an earlier scheme printed the level-2 marker as `1.` and gave a
    second sibling `1.2.`, so `§1.` could be a chapter reference followed by a
    sentence full stop and `§1.2.` could be either the second section or a
    subsection plus punctuation. A reader could not resolve the token. The
    hierarchical path removes both collisions by construction.

    `number` is the cross-reference form and equals `printed` for body levels;
    it is the printed chapter number for a chapter and the bare appendix letter
    for an appendix chapter (`§A`, not `§Appendix A`). Two sections never share
    a `number`, and `§1.1.` always means section `1.1` followed by punctuation
    because no section is numbered `1.1.`.
    """
    numbers: list[dict[str, Any]] = []
    stem = ""
    role = "chapter"
    counters = [0, 0, 0, 0]  # level 2, 3, 4, 5
    for section in manuscript.sections:
        level = section.get("level", 1)
        if level == 1:
            role = section.get("role", "chapter")
            if role == "appendix":
                count = sum(
                    1 for item in numbers if item["level"] == 1 and item["role"] == "appendix"
                ) + 1
                printed = f"Appendix {appendix_letter(count)}"
                stem = appendix_letter(count)
            else:
                count = sum(1 for item in numbers if item["level"] == 1 and item["role"] == "chapter") + 1
                printed = str(count)
                stem = str(count)
            counters = [0, 0, 0, 0]
            number = stem if role == "appendix" else printed
        else:
            depth = min(level - 2, len(counters) - 1)
            counters[depth] += 1
            for deeper in range(depth + 1, len(counters)):
                counters[deeper] = 0
            # Every level carries its own path: `1.1`, `1.1.2`, `1.1.2.1`.
            path = ".".join(str(value) for value in counters[: depth + 1])
            printed = f"{stem}.{path}"
            number = printed
        numbers.append({"level": level, "role": role, "number": number, "printed": printed})
    return numbers



def section_heading(number: dict[str, Any], title: str) -> str:
    """The full printed heading line for one section.

    A chapter prints `Chapter 1: Title` and an appendix `Appendix A: Title`; the
    numbered body headings keep the bare path (`1.1 Title`). The string is data,
    so the report and the verifier can look for the line the page really shows.
    """
    if number["level"] == 1:
        prefix = f"Chapter {number['printed']}" if number["role"] == "chapter" else number["printed"]
        return f"{prefix}: {title}"
    return f"{number['printed']} {title}"


def _number_map(
    manuscript: model.Manuscript, numbers: list[dict[str, Any]]
) -> tuple[dict[str, str], dict[str, int]]:
    """Assign section, figure, table and photograph labels in document order."""
    labels: dict[str, str] = {}
    kinds: dict[str, int] = {"figure": 0, "table": 0, "photograph": 0}
    for index, section in enumerate(manuscript.sections):
        labels[section["id"]] = f"§{numbers[index]['number']}"
        for block in section["blocks"]:
            block_type = block["type"]
            if block_type in {"chart", "diagram"}:
                kinds["figure"] += 1
                labels[block["id"]] = f"Figure {kinds['figure']}"
            elif block_type == "table":
                kinds["table"] += 1
                labels[block["id"]] = f"Table {kinds['table']}"
            elif block_type == "illustration":
                kinds["photograph"] += 1
                labels[block["id"]] = f"Photograph {kinds['photograph']}"
            else:
                labels[block["id"]] = labels[section["id"]]
    return labels, kinds


def _resolve(text: str, labels: dict[str, str]) -> str:
    return REF.sub(lambda match: labels.get(match.group(1), match.group(0)), text)


def _companion_entry(block: dict[str, Any], labels: dict[str, str]) -> dict[str, Any]:
    """The companion as a normal prose entry, emitted once inside the illustration."""
    kind = block["type"]
    entry: dict[str, Any] = {"id": block["id"], "type": kind}
    if kind in {"paragraph", "lead", "quote", "example", "case", "assessment"}:
        entry["text"] = _resolve(block["text"], labels)
        if block.get("title"):
            entry["title"] = _resolve(block["title"], labels)
        if block.get("attribution"):
            entry["attribution"] = _resolve(block["attribution"], labels)
    elif kind == "definition":
        entry["term"] = _resolve(block["term"], labels)
        entry["definition"] = _resolve(block["definition"], labels)
    elif kind == "list":
        entry["items"] = [_resolve(item, labels) for item in block["items"]]
        entry["ordered"] = bool(block.get("ordered", False))
    if block.get("note"):
        entry["note"] = _resolve(block["note"], labels)
    return entry


def _cover_entry(
    manuscript: model.Manuscript, draft: bool
) -> dict[str, Any]:
    """The cover the renderer will draw, recorded as data, not as a claim.

    An absent `metadata.cover` is the engine's documented typographic fallback,
    never a user selection. An art-bearing composition with no artwork record
    reserves its field and records `artwork: absent`; nothing is synthesized.
    """
    selection = manuscript.data["metadata"].get("cover")
    if selection is None:
        return {
            "composition": model.COVER_DEFAULT,
            "selection": "engine-fallback",
            "artwork": "not-applicable",
            "indexPrinted": False,
        }
    composition = selection["composition"]
    entry: dict[str, Any] = {
        "composition": composition,
        "selection": "author",
        "indexPrinted": False,
    }
    if composition == model.COVER_TYPOGRAPHIC:
        entry["artwork"] = "not-applicable"
        return entry
    artwork = selection.get("artwork")
    if not artwork:
        entry["artwork"] = "absent"
        return entry
    record = rights.load(manuscript.root, artwork)
    rights.require_publishable(record, draft)
    entry["artwork"] = "present"
    entry["artworkId"] = record.id
    entry["artworkPath"] = "/" + record.path.lstrip("/")
    entry["artworkCredit"] = record.credit
    return entry


def build(
    manuscript: model.Manuscript,
    figure_paths: dict[str, str],
    draft: bool = False,
) -> Document:
    numbers = section_numbers(manuscript)
    labels, _ = _number_map(manuscript, numbers)
    data: dict[str, Any] = {
        "schemaVersion": "1.0",
        "revision": manuscript.revision,
        "metadata": manuscript.data["metadata"],
        "sections": [],
        "illustrations": [],
        "numbering": {
            "chapters": sum(1 for item in numbers if item["level"] == 1 and item["role"] == "chapter"),
            "appendices": sum(1 for item in numbers if item["level"] == 1 and item["role"] == "appendix"),
            "levels": 5,
        },
        "cover": _cover_entry(manuscript, draft),
    }

    for index, section in enumerate(manuscript.sections, start=1):
        level = section.get("level", 1)
        if index == 1:
            # The contents page already ends with a break; a redundant or
            # explicit first-section break must never create a blank page.
            break_before = "auto"
        else:
            break_before = section.get("breakBefore")
            if break_before is None:
                break_before = "page" if level == 1 else "auto"
        kinds = {block["type"] for block in section["blocks"]}
        illustrations = [block for block in section["blocks"] if block["type"] == "illustration"]
        keep_together = (
            len(illustrations) == 1
            and kinds <= {"illustration", "unresolved"}
        )
        out_section: dict[str, Any] = {
            "number": index,
            "label": labels[section["id"]],
            "level": level,
            "role": numbers[index - 1]["role"],
            "printed": numbers[index - 1]["printed"],
            "heading": section_heading(numbers[index - 1], _resolve(section["title"], labels)),
            "breakBefore": break_before,
            "title": _resolve(section["title"], labels),
            "kicker": _resolve(section["kicker"], labels) if section.get("kicker") else None,
            "standfirst": _resolve(section["standfirst"], labels) if section.get("standfirst") else None,
            "blocks": [],
        }
        if section.get("layout"):
            out_section["layout"] = {"columns": section["layout"]["columns"]}
        if keep_together:
            out_section["keepTogether"] = True
        if section.get("noPlate"):
            out_section["noPlate"] = section["noPlate"]
        consumed: set[str] = set()
        branches = 0
        for position, block in enumerate(section["blocks"]):
            if block["id"] in consumed:
                continue
            kind = block["type"]
            label = labels[block["id"]]
            entry: dict[str, Any] = {"id": block["id"], "type": kind, "label": label}
            if kind in {"paragraph", "lead", "quote", "example", "case", "assessment"}:
                entry["text"] = _resolve(block["text"], labels)
                if block.get("title"):
                    entry["title"] = _resolve(block["title"], labels)
                if block.get("attribution"):
                    entry["attribution"] = _resolve(block["attribution"], labels)
            elif kind == "definition":
                entry["term"] = _resolve(block["term"], labels)
                entry["definition"] = _resolve(block["definition"], labels)
            elif kind == "list":
                entry["items"] = [_resolve(item, labels) for item in block["items"]]
                entry["ordered"] = bool(block.get("ordered", False))
            elif kind == "table":
                entry["caption"] = f"{label}. {_resolve(block['caption'], labels)}" if block.get("caption") else label
                entry["header"] = [_resolve(cell, labels) for cell in block["header"]]
                entry["rows"] = [[_resolve(cell, labels) for cell in row] for row in block["rows"]]
                entry["widths"] = block.get("widths")
                entry["align"] = block.get("align")
            elif kind == "equation":
                entry["typst"] = block["typst"]
                entry["caption"] = _resolve(block["caption"], labels) if block.get("caption") else label
            elif kind == "chart":
                entry["path"] = figure_paths[block["id"]]
                verification = block["chart"]["verification"]
                caption = f"{label}. {_resolve(block['caption'], labels)}"
                approximate = verification == "inferred"
                synthetic = verification == "synthetic"
                if approximate and "approximat" not in caption.lower():
                    caption = f"{caption.rstrip()} Approximate values."
                if synthetic and "synthetic data" not in caption.lower():
                    caption = f"{caption.rstrip()} Synthetic data."
                entry["caption"] = caption
                entry["approximate"] = approximate or synthetic
                entry["synthetic"] = synthetic
                entry["note"] = block["chart"].get("notes")
            elif kind == "diagram":
                entry["spec"] = block["diagram"]
                caption = f"{label}. {_resolve(block['caption'], labels)}"
                synthetic = bool(block["diagram"].get("synthetic"))
                approximate = block.get("confidence") == "inferred"
                if synthetic:
                    if "illustrative diagram" not in caption.lower():
                        caption = f"{caption.rstrip()} Illustrative diagram."
                elif approximate and "reconstruction" not in caption.lower():
                    caption = f"{caption.rstrip()} Reconstruction."
                entry["caption"] = caption
                entry["approximate"] = approximate or synthetic
                entry["synthetic"] = synthetic
            elif kind == "unresolved":
                entry["note"] = _resolve(block["note"], labels)
            elif kind == "branch":
                branches += 1
                marker = f"{numbers[index - 1]['printed']} {chr(ord('a') + branches - 1)})"
                entry["marker"] = marker
                entry["text"] = _resolve(block["text"], labels)
            elif kind == "illustration":
                record = rights.load(manuscript.root, block["illustrationId"])
                rights.require_publishable(record, draft)
                entry["path"] = "/" + record.path.lstrip("/")
                entry["caption"] = f"{label}. {_resolve(rights.caption(record, block.get('caption')), labels)}"
                entry["credit"] = record.credit
                entry["alt"] = record.alt
                entry["rightsStatus"] = record.rights_status
                entry["kind"] = record.kind
                entry["illustrationId"] = record.id
                composition = block.get("composition")
                if composition:
                    entry["composition"] = composition["preset"]
                    if composition["preset"] in {"side-left", "side-right"}:
                        single = "companions" not in composition
                        ids = [composition["companion"]] if single else composition["companions"]
                        companions = []
                        for offset, companion_id in enumerate(ids):
                            companion = section["blocks"][position + 1 + offset]
                            companions.append(_companion_entry(companion, labels))
                            consumed.add(companion_id)
                        if single:
                            entry["companion"] = companions[0]
                        else:
                            entry["companions"] = companions
                data["illustrations"].append(
                    {
                        "id": record.id,
                        "label": label,
                        "caption": entry["caption"],
                        "credit": record.credit,
                        "alt": record.alt,
                        "kind": record.kind,
                        "licence": record.licence,
                        "originUrl": record.origin_url,
                        "pagebreak": False,
                    }
                )
            if kind != "unresolved":
                notes = [block.get("note")]
                if kind == "chart":
                    notes.append(block["chart"].get("notes"))
                notes = [note for note in dict.fromkeys(notes) if isinstance(note, str) and note.strip()]
                if notes:
                    entry["note"] = _resolve(" ".join(notes), labels)
            if "machineRead" in block:
                entry["machineRead"] = dict(block["machineRead"])
            out_section["blocks"].append(entry)
        data["sections"].append(out_section)

    return Document(data=data, labels=labels)
