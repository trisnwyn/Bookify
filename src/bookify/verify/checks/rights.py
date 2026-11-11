"""Rights completeness, kind wording and credit rendering."""

from __future__ import annotations

import re
from pathlib import Path

from bookify.manuscript import model
from bookify.publish import rights
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks.pages import page_texts


def _normalise(text: str) -> str:
    """Collapse whitespace and rejoin words split by a soft hyphen at a line break."""
    text = text.replace("\u200b", "")
    text = re.sub(r"\u00ad\s*", "", text)
    return re.sub(r"\s+", " ", text)


def check(pdf: Path, manuscript: model.Manuscript, draft: bool) -> Check:
    text = _normalise("\n".join(page_texts(pdf)))
    problems: list[str] = []
    checked: list[str] = []
    for section in manuscript.sections:
        for block in section["blocks"]:
            if block["type"] != "illustration":
                continue
            try:
                record = rights.load(manuscript.root, block["illustrationId"])
            except Exception as error:  # noqa: BLE001 - report the contract code
                problems.append(str(error))
                continue
            if record.rights_status != "verified" and not draft:
                problems.append(f"{record.id}: unconfirmed rights")
            if _normalise(record.credit) not in text:
                problems.append(f"{record.id}: credit missing from the PDF")
            marker = rights.kind_wording(record.kind)
            if marker and _normalise(marker).lower().rstrip(".") not in text.lower():
                problems.append(f"{record.id}: {record.kind} not named in the caption")
            if not record.alt.strip():
                problems.append(f"{record.id}: alt text missing")
            checked.append(record.id)

    if problems:
        return failed("rights", "RIGHTS_INCOMPLETE", "; ".join(problems), problems=problems)
    return passed("rights", f"{len(checked)} illustration record(s) complete and credited", ids=checked)
