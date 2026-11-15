"""Extraction probes: the expected text must survive the PDF."""

from __future__ import annotations

import re
from pathlib import Path

from bookify.manuscript import model
from bookify.publish import rights
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks.pages import page_texts

VIETNAMESE = re.compile(r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", re.I)
JAPANESE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def _blocks(manuscript: model.Manuscript) -> list[dict]:
    return [block for section in manuscript.sections for block in section["blocks"]]


def _normalise(text: str) -> str:
    text = text.replace("\u200b", "")
    text = re.sub(r"\u00ad\s*", "", text)
    return re.sub(r"\s+", " ", text)


def expected_probes(manuscript: model.Manuscript) -> list[str]:
    probes: list[str] = [manuscript.data["metadata"]["title"]]

    for block in _blocks(manuscript):
        text = block.get("text") or ""
        if not any(probe.startswith(text[:12]) for probe in probes if text):
            if VIETNAMESE.search(text) and len(text) >= 20:
                probes.append(text[:20])
            elif JAPANESE.search(text) and len(text) >= 12:
                probes.append(text[:12])
        if block["type"] == "equation" and "sum" in block["typst"]:
            probes.append("∑")
        if block.get("note"):
            probes.append(block["note"])
        if block["type"] == "chart" and block["chart"].get("notes"):
            probes.append(block["chart"]["notes"])

    figures = tables = photographs = 0
    for block in _blocks(manuscript):
        kind = block["type"]
        if kind in {"chart", "diagram"}:
            figures += 1
            probes.append(f"Figure {figures}.")
        elif kind == "table":
            tables += 1
            probes.append(f"Table {tables}.")
        elif kind == "illustration":
            photographs += 1
            probes.append(f"Photograph {photographs}.")
            record = rights.load(manuscript.root, block["illustrationId"])
            probes.append(record.credit)
            marker = rights.printed_class_wording(record, None)
            if marker:
                probes.append(marker)

    if any("{ref:" in str(value) for section in manuscript.sections for value in section.values() if isinstance(value, str)):
        probes.append("§1")
    return [probe for probe in probes if probe]


def machine_read_probes(manuscript: model.Manuscript) -> list[str]:
    """Probes drawn only from OCR-derived blocks, reported as rendering probes.

    A missing machine-read probe fails exactly like a text probe; it is never
    reported as factual verification of the OCR value.
    """
    probes: list[str] = []
    for block in _blocks(manuscript):
        if not isinstance(block.get("machineRead"), dict):
            continue
        if block["type"] == "table":
            header = [cell for cell in block.get("header", []) if cell]
            rows = [cell for row in block.get("rows", []) for cell in row if cell]
            if header:
                probes.append(header[0])
            if rows:
                probes.append(rows[0])
        else:
            for field in ("text", "definition", "term", "title"):
                value = block.get(field)
                if isinstance(value, str) and value.strip():
                    probes.append(value[:24])
                    break
    return probes


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    text = _normalise("\n".join(page_texts(pdf)))
    probes = list(dict.fromkeys(expected_probes(manuscript)))
    derived = list(dict.fromkeys(machine_read_probes(manuscript)))
    all_probes = list(dict.fromkeys([*probes, *derived]))
    missing = [probe for probe in all_probes if _normalise(probe) not in text]
    if missing:
        return failed(
            "text",
            "BUILD_FAILED",
            f"missing from extraction: {missing[:6]}",
            missing=missing,
            machineReadProbes=len(derived),
        )
    return passed(
        "text",
        f"{len(all_probes)} probes extracted intact ({len(derived)} machine-read)",
        machineReadProbes=len(derived),
    )
