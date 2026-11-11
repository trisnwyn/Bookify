"""Apply an agent-produced draft to a manuscript, with uncertainty preserved."""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml

from bookify.authoring import cache, decisions as decisions_log, plan
from bookify.errors import BookifyError
from bookify.manuscript import model

SLUG = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    return SLUG.sub("-", value.lower()).strip("-")[:48] or "block"


def _block_id(source_id: str, page: int, index: int) -> str:
    return f"src-{_slug(source_id)}-p{page}-{index}"


def _with_anchor(block: dict[str, Any], source_id: str, page: int) -> dict[str, Any]:
    entry = copy.deepcopy(block)
    anchors = entry.setdefault("sourceAnchors", [])
    if not any(a.get("sourceId") == source_id and a.get("page") == page for a in anchors):
        anchors.append({"sourceId": source_id, "page": page})
    return entry


def _write_atomic(data: dict[str, Any], manuscript_path: Path, root: Path) -> None:
    """Validate the serialized document, then replace the manuscript atomically."""
    payload = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    manuscript_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{manuscript_path.name}.", suffix=".tmp", dir=manuscript_path.parent
    )
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        model.load(temp, root=root)
        os.replace(temp, manuscript_path)
    finally:
        temp.unlink(missing_ok=True)


def _section(data: dict[str, Any], section_id: str) -> dict[str, Any]:
    for section in data["sections"]:
        if section["id"] == section_id:
            return section
    raise BookifyError("INPUT_INVALID", f"draft names an unknown section: {section_id}", section_id)


def _recorded_current(recorded: Any, work_item: dict[str, Any]) -> bool:
    return (
        isinstance(recorded, dict)
        and recorded.get("textSha256") == work_item["textSha256"]
        and recorded.get("promptVersion") == work_item.get("promptVersion", plan.PROMPT_VERSION)
        and recorded.get("schemaVersion") == work_item.get("schemaVersion", cache.SCHEMA_VERSION)
    )


def _model_name(draft: dict[str, Any]) -> str:
    model_name = draft.get("model")
    if isinstance(model_name, str) and model_name.strip():
        return model_name
    for call in draft.get("modelCalls", []):
        name = call.get("model") if isinstance(call, dict) else None
        if isinstance(name, str) and name.strip():
            return name
    return "agent"


def _normalise_work_item(item: dict[str, Any], plan_data: dict[str, Any], source_id: str) -> dict[str, Any]:
    """Accept older plan files that predate the versioned cache record."""
    text_sha256 = item["textSha256"]
    prompt_version = item.get("promptVersion", plan_data.get("promptVersion", plan.PROMPT_VERSION))
    schema_version = item.get("schemaVersion", cache.SCHEMA_VERSION)
    input_hash = item.get("inputHash") or cache.key(
        source_id, int(item["page"]), text_sha256, prompt_version, schema_version
    )
    return {
        **item,
        "promptVersion": prompt_version,
        "schemaVersion": schema_version,
        "inputHash": input_hash,
    }


def apply(
    plan_path: Path,
    draft_path: Path,
    manuscript_path: Path,
    cache_dir: Path,
    decisions_path: Path,
) -> dict[str, Any]:
    manuscript = model.load(manuscript_path)
    plan_data = json.loads(plan_path.read_text())
    draft = json.loads(draft_path.read_text())

    work_pages = {
        (item["sourceId"], item["page"]): _normalise_work_item(item, plan_data, item["sourceId"])
        for item in plan_data.get("work", [])
    }
    source_id = draft.get("sourceId") or plan_data.get("sourceId")
    if source_id is None:
        raise BookifyError("INPUT_INVALID", "draft has no sourceId", str(draft_path))

    data = copy.deepcopy(manuscript.data)
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    applied_index = cache.load_index(cache_dir)
    model_name = _model_name(draft)
    prompt_version = plan_data.get("promptVersion", plan.PROMPT_VERSION)

    for entry in draft.get("pages", []):
        page = int(entry["page"])
        key = f"{source_id}#{page}"
        work_item = work_pages.get((source_id, page))
        if work_item is None:
            raise BookifyError(
                "INPUT_INVALID",
                f"page {page} is not in the plan; replan before applying",
                key,
            )
        if _recorded_current(applied_index.get(key), work_item):
            skipped.append({"sourceId": source_id, "page": page, "reason": "already applied"})
            continue
        if entry.get("textSha256") != work_item["textSha256"] or entry.get("inputHash") != work_item["inputHash"]:
            raise BookifyError(
                "INPUT_INVALID",
                f"draft for page {page} was authored from different content; replan and re-author it",
                key,
            )
        section = _section(data, entry["sectionId"])
        unreadable = bool(entry.get("unreadable"))

        new_blocks: list[dict[str, Any]] = []
        if unreadable:
            if entry.get("blocks"):
                raise BookifyError(
                    "SCHEMA_INVALID",
                    "an unreadable page must not carry invented blocks",
                    key,
                )
            note = entry.get("note")
            if not isinstance(note, str) or not note.strip():
                raise BookifyError("SCHEMA_INVALID", "unreadable pages need a note", key)
            new_blocks.append(
                {
                    "id": _block_id(source_id, page, 1),
                    "type": "unresolved",
                    "note": note.strip(),
                    "confidence": "unreadable",
                    "sourceAnchors": [{"sourceId": source_id, "page": page}],
                }
            )
        else:
            for position, block in enumerate(entry.get("blocks", []), start=1):
                candidate = _with_anchor(block, source_id, page)
                candidate.setdefault("id", _block_id(source_id, page, position))
                new_blocks.append(candidate)

        retained = [
            block
            for block in section["blocks"]
            if not any(a.get("sourceId") == source_id and a.get("page") == page for a in block.get("sourceAnchors", []))
        ]
        insert_at = next(
            (
                position
                for position, block in enumerate(section["blocks"])
                if any(a.get("sourceId") == source_id and a.get("page") == page for a in block.get("sourceAnchors", []))
            ),
            len(retained),
        )
        section["blocks"] = retained[:insert_at] + new_blocks + retained[insert_at:]
        applied.append({"sourceId": source_id, "page": page, "sectionId": section["id"], "blocks": len(new_blocks)})

        for decision in entry.get("decisions", []):
            decisions.append({"sourceId": source_id, "page": page, "decision": decision})

    if not applied:
        return {
            "ok": True, "revision": manuscript.revision,
            "applied": [], "skipped": skipped, "modelCalls": [],
        }

    data["revision"] = int(data["revision"]) + 1
    _write_atomic(data, manuscript_path, manuscript.root)

    for item in applied:
        work_item = work_pages[(source_id, item["page"])]
        page_prompt = work_item.get("promptVersion", prompt_version)
        applied_index[f"{source_id}#{item['page']}"] = cache.record(
            text_sha256=work_item["textSha256"],
            prompt_version=page_prompt,
            model=model_name,
            input_hash=work_item["inputHash"],
            schema_version=work_item.get("schemaVersion", cache.SCHEMA_VERSION),
        )
        cache.put(
            cache_dir,
            work_item["inputHash"],
            next(
                entry
                for entry in draft["pages"]
                if int(entry["page"]) == item["page"] and entry.get("sectionId") == item["sectionId"]
            ),
            model_name,
            page_prompt,
            work_item["textSha256"],
        )
    cache.save_index(cache_dir, applied_index)

    decisions_log.append(decisions_path, decisions)

    return {
        "ok": True,
        "revision": data["revision"],
        "applied": applied,
        "skipped": skipped,
        "modelCalls": draft.get("modelCalls", []) if applied else [],
    }
