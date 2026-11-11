"""Content-addressed cache for interpreted source pages.

The index records what was applied, not just which page was seen: each value
carries the text hash plus the prompt and schema versions that produced it, so
a prompt or schema change invalidates earlier work.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"


def key(source_id: str, page: int, text_sha256: str, prompt_version: str, schema_version: str | None = None) -> str:
    schema_version = schema_version or SCHEMA_VERSION
    payload = f"{schema_version}|{prompt_version}|{source_id}#{page}|{text_sha256}"
    return hashlib.sha256(payload.encode()).hexdigest()


def record(
    text_sha256: str,
    prompt_version: str,
    model: str,
    input_hash: str,
    schema_version: str | None = None,
) -> dict[str, str]:
    """One applied-page record: content hash, versions, model and cache key."""
    return {
        "textSha256": text_sha256,
        "promptVersion": prompt_version,
        "schemaVersion": schema_version or SCHEMA_VERSION,
        "model": model,
        "inputHash": input_hash,
    }


def index_path(cache_dir: Path) -> Path:
    return cache_dir / "index.json"


def load_index(cache_dir: Path) -> dict[str, Any]:
    path = index_path(cache_dir)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        # The cache is disposable; a corrupt index is treated as empty, never a crash.
        return {}
    return payload if isinstance(payload, dict) else {}


def save_index(cache_dir: Path, index: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = index_path(cache_dir)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def get(cache_dir: Path, cache_key: str) -> dict[str, Any] | None:
    path = cache_dir / "entries" / f"{cache_key}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def put(cache_dir: Path, cache_key: str, payload: dict[str, Any], model: str, prompt_version: str, input_hash: str) -> None:
    directory = cache_dir / "entries"
    directory.mkdir(parents=True, exist_ok=True)
    record_data = {
        "schemaVersion": SCHEMA_VERSION,
        "key": cache_key,
        "model": model,
        "promptVersion": prompt_version,
        "inputHash": input_hash,
        "output": payload,
    }
    target = directory / f"{cache_key}.json"
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(record_data, indent=2, sort_keys=True) + "\n")
    temp.replace(target)
