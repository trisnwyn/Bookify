"""Per-page change detection between two manifests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bookify.intake import manifest as manifest_module

SCHEMA_VERSION = "1.0"


def _image_keys(manifest: dict[str, Any]) -> dict[str, str]:
    keys: dict[str, str] = {}
    for page in manifest.get("pages", []):
        for image in page["images"]:
            keys[f"{page['page']}:{image['index']}"] = image["sha256"]
    return keys


def empty(source_id: str) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "sourceId": source_id,
        "addedPages": [],
        "removedPages": [],
        "changedPages": [],
        "addedImages": [],
        "removedImages": [],
    }


def diff(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if previous is None:
        return empty(current["sourceId"])

    old_pages = {page["page"]: page for page in previous.get("pages", [])}
    new_pages = {page["page"]: page for page in current.get("pages", [])}
    old_images = _image_keys(previous)
    new_images = _image_keys(current)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "sourceId": current["sourceId"],
        "addedPages": sorted(set(new_pages) - set(old_pages)),
        "removedPages": sorted(set(old_pages) - set(new_pages)),
        "changedPages": sorted(
            page
            for page in set(old_pages) & set(new_pages)
            if old_pages[page]["textSha256"] != new_pages[page]["textSha256"]
            or [image["sha256"] for image in old_pages[page]["images"]]
            != [image["sha256"] for image in new_pages[page]["images"]]
        ),
        "addedImages": sorted(set(new_images) - set(old_images)),
        "removedImages": sorted(set(old_images) - set(new_images)),
    }


def write(path: Path, changes: dict[str, Any]) -> None:
    manifest_module.write_json(path / "changes.json", changes)
