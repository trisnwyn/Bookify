"""Deterministic work list: only pages whose content changed since the last apply."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from bookify.authoring import cache
from bookify.errors import BookifyError
from bookify.manuscript import model

PROMPT_VERSION = "v1"


@dataclass(frozen=True)
class WorkItem:
    sourceId: str
    page: int
    textSha256: str
    reason: str
    blockIds: tuple[str, ...]
    figureIds: tuple[str, ...]
    promptVersion: str
    schemaVersion: str
    inputHash: str
    cached: bool


def _cited(manuscript: model.Manuscript) -> dict[tuple[str, int], list[dict[str, Any]]]:
    cited: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for section in manuscript.sections:
        for block in section["blocks"]:
            for anchor in block.get("sourceAnchors", []):
                cited.setdefault((anchor["sourceId"], anchor["page"]), []).append(block)
    return cited


def _recorded_hash(recorded: Any) -> str | None:
    if isinstance(recorded, dict):
        value = recorded.get("textSha256")
        return value if isinstance(value, str) else None
    # Legacy index values were a bare text hash with no version information.
    return recorded if isinstance(recorded, str) else None


def _is_current(recorded: Any, text_sha256: str, prompt_version: str) -> bool:
    if not isinstance(recorded, dict):
        return False
    return (
        _recorded_hash(recorded) == text_sha256
        and recorded.get("promptVersion") == prompt_version
        and recorded.get("schemaVersion") == cache.SCHEMA_VERSION
    )


def build(
    intake_dir: Path,
    manuscript: model.Manuscript,
    cache_dir: Path,
    prompt_version: str | None = None,
) -> dict[str, Any]:
    prompt_version = prompt_version or PROMPT_VERSION
    manifest_path = intake_dir / "manifest.json"
    if not manifest_path.is_file():
        raise BookifyError("INPUT_INVALID", f"intake manifest missing: {manifest_path}", str(manifest_path))
    manifest = json.loads(manifest_path.read_text())
    source_id = manifest["sourceId"]
    index = cache.load_index(cache_dir)
    cited = _cited(manuscript)

    work: list[WorkItem] = []
    for page in manifest["pages"]:
        key = f"{source_id}#{page['page']}"
        recorded = index.get(key)
        if _is_current(recorded, page["textSha256"], prompt_version):
            continue
        input_hash = cache.key(source_id, page["page"], page["textSha256"], prompt_version)
        blocks = cited.get((source_id, page["page"]), [])
        work.append(
            WorkItem(
                sourceId=source_id,
                page=page["page"],
                textSha256=page["textSha256"],
                reason="new" if recorded is None else "changed",
                blockIds=tuple(sorted(block["id"] for block in blocks)),
                figureIds=tuple(sorted(block["id"] for block in blocks if block["type"] in {"chart", "diagram"})),
                promptVersion=prompt_version,
                schemaVersion=cache.SCHEMA_VERSION,
                inputHash=input_hash,
                cached=cache.get(cache_dir, input_hash) is not None,
            )
        )

    return {
        "schemaVersion": "1.0",
        "sourceId": source_id,
        "promptVersion": prompt_version,
        "cacheSchemaVersion": cache.SCHEMA_VERSION,
        "work": [asdict(item) for item in work],
    }
