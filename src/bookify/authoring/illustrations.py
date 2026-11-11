"""Illustration selection records: relevance-first, no quota, reuse on repeat."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bookify.errors import BookifyError
from bookify.publish import rights


def load(store: Path) -> list[dict[str, Any]]:
    if not store.is_file():
        return []
    return json.loads(store.read_text()).get("selections", [])


def save(store: Path, selections: list[dict[str, Any]]) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    temp = store.with_suffix(".tmp")
    temp.write_text(json.dumps({"schemaVersion": "1.0", "selections": selections}, indent=2, sort_keys=True) + "\n")
    temp.replace(store)


def select(store: Path, section_id: str, illustration_id: str, reason: str) -> dict[str, Any]:
    """Record a selection; repeating it returns the existing record unchanged."""
    selections = load(store)
    for record in selections:
        if record["sectionId"] == section_id and record["illustrationId"] == illustration_id:
            return {**record, "reused": True}
    if not reason.strip():
        raise BookifyError("INPUT_INVALID", "a selection needs a relevance reason", illustration_id)
    record = {
        "sectionId": section_id,
        "illustrationId": illustration_id,
        "reason": reason.strip(),
        "selectedBeforePagination": True,
    }
    selections.append(record)
    save(store, selections)
    return {**record, "reused": False}


def status(store: Path, root: Path, section: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in load(store):
        if section is not None and record["sectionId"] != section:
            continue
        try:
            image = rights.load(root, record["illustrationId"])
            rights_status = image.rights_status
            licence = image.licence
        except BookifyError:
            rights_status = "unconfirmed"
            licence = "unknown"
        rows.append({**record, "rightsStatus": rights_status, "licence": licence})
    return rows
