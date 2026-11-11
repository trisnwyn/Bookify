"""Append-only decisions log for authoring choices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append(path: Path, entries: list[dict[str, Any]]) -> None:
    if not entries:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
