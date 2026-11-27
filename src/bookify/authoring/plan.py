"""Deterministic work list: only pages whose content changed since the last apply."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from bookify.authoring import cache
from bookify.errors import BookifyError
from bookify.intake import ocr as intake_ocr
from bookify.manuscript import model

PROMPT_VERSION = "v1"


@dataclass(frozen=True)
class WorkItem:
    sourceId: str
    page: int
    textSha256: str
    contentSha256: str
    reason: str
    blockIds: tuple[str, ...]
    figureIds: tuple[str, ...]
    promptVersion: str
    schemaVersion: str
    inputHash: str
    cached: bool


def page_content_sha256(page: dict[str, Any]) -> str:
    """Composite hash covering page text, embedded images and OCR evidence.

    When a page carries neither images nor OCR records this returns
    ``textSha256`` verbatim so legacy indexes stay valid.
    """
    text_sha = page["textSha256"]
    images = page.get("images") or []
    ocr_record = page.get("ocr")
    if not images and not ocr_record:
        return text_sha
    payload = {
        "textSha256": text_sha,
        "images": [item.get("sha256") for item in images if isinstance(item, dict)],
        "ocr": intake_ocr.page_ocr_hash(ocr_record) if ocr_record else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _is_current(recorded: Any, text_sha256: str, content_sha256: str, prompt_version: str) -> bool:
    if not isinstance(recorded, dict):
        return False
    recorded_content = recorded.get("contentSha256")
    if content_sha256 != text_sha256 or recorded_content is not None:
        if (recorded_content or recorded.get("textSha256")) != content_sha256:
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
        content_sha = page_content_sha256(page)
        if _is_current(recorded, page["textSha256"], content_sha, prompt_version):
            continue
        input_hash = cache.key(
            source_id, page["page"], page["textSha256"], prompt_version, content_sha256=content_sha
        )
        blocks = cited.get((source_id, page["page"]), [])
        work.append(
            WorkItem(
                sourceId=source_id,
                page=page["page"],
                textSha256=page["textSha256"],
                contentSha256=content_sha,
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
