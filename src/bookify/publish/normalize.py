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


def _number_map(manuscript: model.Manuscript) -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    """Assign section, figure, table and photograph labels in document order."""
    labels: dict[str, str] = {}
    kinds: dict[str, int] = {"figure": 0, "table": 0, "photograph": 0}
    for index, section in enumerate(manuscript.sections, start=1):
        labels[section["id"]] = f"§{index}"
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
    return labels, {}, kinds


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


def build(
    manuscript: model.Manuscript,
    figure_paths: dict[str, str],
    draft: bool = False,
) -> Document:
    labels, _, _ = _number_map(manuscript)
    data: dict[str, Any] = {
        "schemaVersion": "1.0",
        "revision": manuscript.revision,
        "metadata": manuscript.data["metadata"],
        "sections": [],
        "illustrations": [],
    }

    for index, section in enumerate(manuscript.sections, start=1):
        out_section: dict[str, Any] = {
            "number": index,
            "label": labels[section["id"]],
            "title": _resolve(section["title"], labels),
            "kicker": _resolve(section["kicker"], labels) if section.get("kicker") else None,
            "standfirst": _resolve(section["standfirst"], labels) if section.get("standfirst") else None,
            "blocks": [],
        }
        consumed: set[str] = set()
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
                    if composition["preset"] != "full":
                        companion = section["blocks"][position + 1]
                        entry["companion"] = _companion_entry(companion, labels)
                        consumed.add(companion["id"])
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
            out_section["blocks"].append(entry)
        data["sections"].append(out_section)

    return Document(data=data, labels=labels)
