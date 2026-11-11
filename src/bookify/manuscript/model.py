"""Semantic validation for a manuscript and its illustration records.

Shape is checked by `schema.validate`; this module enforces the rules JSON
Schema cannot express: unique ids, reference targets, chart matrix integrity,
diagram edges, table geometry, unreadable values and rights records.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

from bookify.errors import BookifyError
from bookify.figures import checks as figure_checks
from bookify.manuscript import schema

REF = re.compile(r"\{ref:([a-z0-9][a-z0-9-]*)\}")
RECORD_FIELDS = (
    "id",
    "path",
    "originUrl",
    "creator",
    "licence",
    "credit",
    "caption",
    "alt",
    "kind",
    "rightsStatus",
)
RECORD_KINDS = {"contemporary_photograph", "later_depiction", "reconstruction", "conceptual_artwork"}
RIGHTS_STATUS = {"verified", "unconfirmed"}


@dataclass(frozen=True)
class Manuscript:
    path: Path
    root: Path
    id: str
    revision: int
    sections: tuple[dict[str, Any], ...]
    block_ids: frozenset[str]
    data: dict[str, Any]


def _project_root(path: Path) -> Path:
    for parent in path.resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return path.resolve().parent


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in {"id", "sourceId", "illustrationId", "from", "to"}:
                continue
            yield from _strings(item)


def _require(condition: bool, message: str, locator: str, code: str = "SCHEMA_INVALID") -> None:
    if not condition:
        raise BookifyError(code, message, locator)


def _check_ids(data: dict[str, Any]) -> tuple[frozenset[str], frozenset[str]]:
    section_ids: set[str] = set()
    block_ids: set[str] = set()
    for index, section in enumerate(data["sections"]):
        section_id = section["id"]
        _require(section_id not in section_ids, f"duplicate section id: {section_id}", f"sections[{index}].id")
        section_ids.add(section_id)
        for position, block in enumerate(section["blocks"]):
            block_id = block["id"]
            _require(block_id not in block_ids, f"duplicate block id: {block_id}", f"sections[{index}].blocks[{position}].id")
            block_ids.add(block_id)
    return frozenset(section_ids), frozenset(block_ids)


def _check_xrefs(data: dict[str, Any], targets: frozenset[str]) -> None:
    for index, section in enumerate(data["sections"]):
        for text in _strings(section):
            for match in REF.finditer(text):
                target = match.group(1)
                _require(target in targets, f"unknown reference target: {target}", f"sections[{index}]", "XREF_MISSING")


def _check_chart(block: dict[str, Any], locator: str) -> None:
    """One boundary: `figures.checks` owns every chart shape, range and cap rule."""
    figure_checks.validate_chart(block)
    chart = block["chart"]
    values = chart.get("values", [])
    if block.get("confidence") == "unreadable":
        numeric = [
            value for row in values for value in row if value is not None
        ] if isinstance(values, list) else []
        _require(not numeric, "unreadable values must be null, not guessed", f"{locator}.confidence")


def _check_equation(block: dict[str, Any], locator: str) -> None:
    """Only math source is allowed: no delimiter, code escape or markup escape."""
    source = block["typst"]
    for token, reason in (("$", "math delimiter"), ("#", "code escape"), ("\\", "markup escape")):
        _require(token not in source, f"equation contains a {reason}: {token}", f"{locator}.typst")



def _check_diagram(block: dict[str, Any], locator: str, root: Path) -> None:
    """One boundary: `figures.checks` owns preset caps, graph rules and provenance."""
    figure_checks.validate_diagram(block, root=root)


def _check_table(block: dict[str, Any], locator: str) -> None:
    width = len(block["header"])
    for index, row in enumerate(block["rows"]):
        _require(len(row) == width, "row width must match the header", f"{locator}.rows[{index}]")
    if "widths" in block:
        _require(len(block["widths"]) == width, "one width per column", f"{locator}.widths")
    if "align" in block:
        _require(len(block["align"]) == width, "one alignment per column", f"{locator}.align")


PAYLOAD_FIELDS = (
    "text",
    "term",
    "definition",
    "attribution",
    "title",
    "items",
    "header",
    "rows",
    "typst",
    "diagram",
    "illustrationId",
)


def _check_unreadable(block: dict[str, Any], locator: str) -> None:
    """An unreadable block may hold a note, never invented payload."""
    _require(bool(block.get("note")), "unreadable blocks need a note", f"{locator}.note")
    kind = block["type"]
    if kind == "unresolved":
        return
    if kind == "chart":
        # `_check_chart` rejects numeric values under unreadable confidence.
        return
    payload = [field for field in PAYLOAD_FIELDS if block.get(field) not in (None, "", [], {})]
    if block.get("caption"):
        payload.append("caption")
    _require(
        not payload,
        f"unreadable {kind} blocks must not carry rendered content: {', '.join(sorted(payload))}",
        f"{locator}.confidence",
    )



def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


COMPANION_TYPES = frozenset(
    {"paragraph", "lead", "definition", "example", "case", "assessment", "quote", "list"}
)
COMPANION_CAP = 520
COMPANION_LABEL = re.compile(r"^(?:Figure|Table|Photograph) \d+\.")


def _collapsed(text: str) -> str:
    return " ".join(text.split())


def _companion_strings(block: dict[str, Any]) -> list[str]:
    """Every printable string of the companion, for the 520-character cap."""
    strings: list[str] = []
    for field in ("title", "term", "definition", "text", "attribution"):
        value = block.get(field)
        if isinstance(value, str) and value.strip():
            strings.append(value)
    items = block.get("items")
    if isinstance(items, list):
        strings.extend(item for item in items if isinstance(item, str))
    note = block.get("note")
    if isinstance(note, str) and note.strip():
        strings.append(note)
    return strings


def _companion_leading_text(block: dict[str, Any]) -> str:
    """The string a reader sees first, so a caption look-alike is caught."""
    kind = block["type"]
    if kind == "definition":
        return str(block.get("term", ""))
    if kind in {"example", "case", "assessment"}:
        return str(block.get("title") or kind.capitalize())
    if kind == "list":
        items = block.get("items") or [""]
        return str(items[0])
    return str(block.get("text", ""))


def _check_compositions(data: dict[str, Any]) -> None:
    """Optional illustration composition: adjacency, prose type, one use, cap, label."""
    used: dict[str, str] = {}
    for section_index, section in enumerate(data["sections"]):
        blocks = section["blocks"]
        for block_index, block in enumerate(blocks):
            composition = block.get("composition")
            if block["type"] != "illustration" or not composition:
                continue
            preset = composition["preset"]
            if preset == "full":
                continue
            locator = f"sections[{section_index}].blocks[{block_index}].composition"
            companion_id = composition.get("companion")
            _require(
                isinstance(companion_id, str),
                f"side composition requires a companion: {preset}",
                f"{locator}.companion",
            )
            _require(
                companion_id not in used,
                f"companion already used by {used.get(companion_id)}: {companion_id}",
                f"{locator}.companion",
            )
            used[companion_id] = block["id"]
            if block_index + 1 >= len(blocks):
                raise BookifyError(
                    "SCHEMA_INVALID",
                    f"companion is not the immediately following block: {companion_id}",
                    f"{locator}.companion",
                )
            companion = blocks[block_index + 1]
            _require(
                companion["id"] == companion_id,
                f"companion is not the immediately following block: {companion_id}",
                f"{locator}.companion",
            )
            _require(
                companion["type"] in COMPANION_TYPES,
                f"companion must be a prose block, not {companion['type']}: {companion_id}",
                f"{locator}.companion",
            )
            printable = _collapsed(" ".join(_companion_strings(companion)))
            _require(
                len(printable) <= COMPANION_CAP,
                f"companion exceeds {COMPANION_CAP} characters: {len(printable)}",
                f"{locator}.companion",
            )
            leading = _collapsed(_companion_leading_text(companion))
            _require(
                COMPANION_LABEL.match(leading) is None,
                f"companion must not begin with a figure, table or photograph label: {companion_id}",
                f"{locator}.companion",
            )


def _check_illustration(block: dict[str, Any], root: Path, locator: str) -> None:
    illustration_id = block["illustrationId"]
    directory = root / "assets" / "illustrations" / illustration_id
    record_path = directory / "record.yaml"
    _require(record_path.is_file(), f"missing illustration record: {illustration_id}", f"{locator}.illustrationId", "RIGHTS_INCOMPLETE")
    record = yaml.safe_load(record_path.read_text())
    _require(isinstance(record, dict), "illustration record must be a mapping", str(record_path), "RIGHTS_INCOMPLETE")
    for field in RECORD_FIELDS:
        value = record.get(field)
        _require(
            isinstance(value, str) and value.strip() != "",
            f"illustration record is missing {field}",
            f"{str(record_path)}:{field}",
            "RIGHTS_INCOMPLETE",
        )
    _require(record["id"] == illustration_id, "record id must match its directory", str(record_path), "RIGHTS_INCOMPLETE")
    _require(record["kind"] in RECORD_KINDS, f"unsupported illustration kind: {record['kind']}", str(record_path), "RIGHTS_INCOMPLETE")
    _require(record["rightsStatus"] in RIGHTS_STATUS, f"unsupported rights status: {record['rightsStatus']}", str(record_path), "RIGHTS_INCOMPLETE")
    image = root / record["path"]
    _require(image.is_file(), f"illustration file missing: {record['path']}", str(image), "RIGHTS_INCOMPLETE")
    if "sha256" in record:
        _require(_sha256(image) == record["sha256"], "illustration file hash mismatch", str(image), "RIGHTS_INCOMPLETE")


def load(path: Path, root: Path | None = None) -> Manuscript:
    if not path.is_file():
        raise BookifyError("INPUT_INVALID", f"manuscript not found: {path}", str(path))
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as error:
        raise BookifyError("SCHEMA_INVALID", f"manuscript is not valid YAML: {error}", str(path)) from error
    if not isinstance(data, dict):
        raise BookifyError("SCHEMA_INVALID", "manuscript root must be a mapping", str(path))

    schema.validate(data)
    project_root = root.resolve() if root else _project_root(path)
    section_ids, block_ids = _check_ids(data)
    _check_xrefs(data, section_ids | block_ids)
    _check_compositions(data)

    for section_index, section in enumerate(data["sections"]):
        for block_index, block in enumerate(section["blocks"]):
            locator = f"sections[{section_index}].blocks[{block_index}]"
            if block.get("confidence") == "unreadable":
                _check_unreadable(block, locator)
            kind = block["type"]
            if kind == "chart":
                _check_chart(block, locator)
            elif kind == "diagram":
                _check_diagram(block, locator, project_root)
            elif kind == "table":
                _check_table(block, locator)
            elif kind == "equation":
                _check_equation(block, locator)
            elif kind == "illustration":
                _check_illustration(block, project_root, locator)

    return Manuscript(
        path=path,
        root=project_root,
        id=data["id"],
        revision=data["revision"],
        sections=tuple(data["sections"]),
        block_ids=block_ids,
        data=data,
    )
