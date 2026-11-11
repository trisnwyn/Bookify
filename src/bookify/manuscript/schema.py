"""Load the normative JSON Schema and validate shape.

Shape violations are `SCHEMA_INVALID`. Cross-field rules live in `model.py`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from bookify.errors import BookifyError

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "schemas" / "manuscript.schema.json"


@lru_cache(maxsize=1)
def load_document() -> dict[str, Any]:
    if not SCHEMA_PATH.is_file():
        raise BookifyError("INPUT_INVALID", f"manuscript schema missing: {SCHEMA_PATH}", str(SCHEMA_PATH))
    return json.loads(SCHEMA_PATH.read_text())


def validate(data: Any) -> None:
    validator = Draft202012Validator(load_document())
    error = best_match(validator.iter_errors(data))
    if error is None:
        return
    locator = "/".join(str(part) for part in error.absolute_path) or "<root>"
    raise BookifyError("SCHEMA_INVALID", error.message, locator)
