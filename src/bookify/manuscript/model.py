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

from bookify.authoring import workspace as workspace_mod
from bookify.errors import BookifyError
from bookify.figures import checks as figure_checks
from bookify.manuscript import schema

REF = re.compile(r"\{ref:([a-z0-9][a-z0-9-]*)\}")
DIGIT = re.compile(r"\d")
MACHINE_READ_NOTE = "Reconstructed from an image by OCR"
MACHINE_READ_TYPES = frozenset(
    {"paragraph", "lead", "quote", "definition", "example", "case", "assessment", "list", "table"}
)
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
    engine: Path
    workspace: Path | None = None


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
            if key in {"id", "sourceId", "illustrationId", "from", "to", "machineRead"}:
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


def _check_section_hierarchy(data: dict[str, Any]) -> None:
    """Levels are additive: first section level 1, no skipped/orphan depth.

    `breakBefore` itself is enum-checked by JSON Schema. A break on the first
    body section is not an error; `normalize` resolves it to `auto` and the
    template also guards `section-index > 0`, so it can never create a blank page.
    """
    titles: set[str] = set()
    current = 0
    for index, section in enumerate(data["sections"]):
        title = section["title"]
        _require(title not in titles, f"duplicate section title: {title}", f"sections[{index}].title")
        titles.add(title)
        level = section.get("level", 1)
        if index == 0:
            _require(level == 1, f"the first section must be level 1, not {level}", f"sections[{index}].level")
        else:
            _require(
                level <= current + 1,
                f"section level skips a parent: {current} -> {level}",
                f"sections[{index}].level",
            )
        current = level


def _check_no_plate(data: dict[str, Any]) -> None:
    """A no-plate decision is authored, non-empty and level-1 only (D4)."""
    for index, section in enumerate(data["sections"]):
        if "noPlate" not in section:
            continue
        _require(
            section.get("level", 1) == 1,
            "noPlate is a chapter-level decision",
            f"sections[{index}].noPlate",
        )
        _require(
            isinstance(section["noPlate"], str) and bool(section["noPlate"].strip()),
            "noPlate needs a real reason",
            f"sections[{index}].noPlate",
        )


COVER_COMPOSITIONS = ("cover-1", "cover-2", "cover-3", "cover-4", "cover-5", "cover-6", "cover-7")
# The typographic composition has no illustration field, so artwork is refused
# rather than silently ignored.
COVER_TYPOGRAPHIC = "cover-3"
COVER_DEFAULT = COVER_TYPOGRAPHIC


def _check_cover_selection(data: dict[str, Any]) -> None:
    """The cover is an authored selection; artwork is an illustration record.

    No composition is a user default: an absent `metadata.cover` is recorded as
    the engine fallback by `normalize`, never printed as if it were a choice.
    """
    selection = data["metadata"].get("cover")
    if selection is None:
        return
    if selection["composition"] == COVER_TYPOGRAPHIC:
        _require(
            "artwork" not in selection,
            "the typographic cover has no artwork field",
            "metadata.cover.artwork",
        )


def _check_section_layout(data: dict[str, Any]) -> None:
    """A column count is a chapter-level property and never a runtime choice."""
    for index, section in enumerate(data["sections"]):
        if "layout" not in section:
            continue
        _require(
            section.get("level", 1) == 1,
            "layout is a chapter-level property",
            f"sections[{index}].layout",
        )


def _check_section_roles(data: dict[str, Any]) -> None:
    """D3: back matter is authored, never inferred; mixed order is refused.

    A level-1 section is a chapter unless it says `role: appendix`. Appendices
    follow every chapter; a chapter after an appendix is refused rather than
    silently renumbered. Role is a level-1 property: a level-2/3 section inherits
    its chapter's role and may not declare one.
    """
    appendix = False
    for index, section in enumerate(data["sections"]):
        role = section.get("role", "chapter")
        level = section.get("level", 1)
        if level != 1:
            _require(
                role == "chapter",
                f"role is a level-1 property; {role} on a level-{level} section",
                f"sections[{index}].role",
            )
            continue
        if role == "appendix":
            _require(index > 0, "the first body section cannot be an appendix", f"sections[{index}].role")
            appendix = True
        elif appendix:
            raise BookifyError(
                "SCHEMA_INVALID",
                "a chapter cannot follow an appendix; back matter stays last",
                f"sections[{index}].role",
            )


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



def _check_machine_read(block: dict[str, Any], locator: str) -> None:
    """OCR provenance is a mark, never a licence to render unverified fact.

    The no-invention rule is unchanged: machine-read text is `inferred` at
    best, a table is a reconstruction with its mandatory note, and digits need
    a recorded cross-check.
    """
    machine = block.get("machineRead")
    anchors = block.get("sourceAnchors", [])
    for index, anchor in enumerate(anchors):
        _require(
            "region" not in anchor or machine is not None,
            "sourceAnchors[].region is only valid with machineRead provenance",
            f"{locator}.sourceAnchors[{index}].region",
        )
    if machine is None:
        return
    kind = block["type"]
    _require(
        kind in MACHINE_READ_TYPES,
        f"machineRead is not valid on a {kind} block; OCR text is prose or a reconstructed table",
        f"{locator}.machineRead",
    )
    _require(
        block.get("confidence") != "verified",
        "machine-read text can never be verified",
        f"{locator}.confidence",
    )
    region = machine["region"]
    _require(isinstance(region, int) and region >= 1, "machineRead.region must be >= 1", f"{locator}.machineRead.region")
    _require(
        any(anchor.get("region") == region for anchor in anchors),
        "a machineRead block needs a source anchor with the same region",
        f"{locator}.sourceAnchors",
    )
    for index, anchor in enumerate(anchors):
        if "region" in anchor:
            _require(
                anchor["region"] == region,
                "every region anchor must name the machineRead region",
                f"{locator}.sourceAnchors[{index}].region",
            )
    method = machine["method"]
    if kind == "table":
        _require(
            method == "ocr-table-v1",
            "a machine-read table uses method ocr-table-v1",
            f"{locator}.machineRead.method",
        )
        note = block.get("note") or ""
        _require(
            note.startswith(MACHINE_READ_NOTE),
            f"machine-read tables need a note beginning {MACHINE_READ_NOTE!r}",
            f"{locator}.note",
        )
    else:
        _require(
            method == "ocr-line",
            "machine-read prose uses method ocr-line",
            f"{locator}.machineRead.method",
        )
    content = " ".join(_strings(block))
    if DIGIT.search(content):
        _require(
            bool(machine.get("crossCheckedBy")),
            "machine-read text containing digits needs crossCheckedBy evidence",
            f"{locator}.machineRead.crossCheckedBy",
        )


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
COMPANION_MAX = 3
# A side column is ~218.63 pt wide, about 33 body characters a line. 900
# collapsed characters is ~27 lines, ~414 pt at the 15.30 pt pitch: the height
# the accepted A1 side composition measured. The per-block 520 cap still holds.
COMPANION_GROUP_CAP = 900
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


def _check_companion(
    companion: dict[str, Any],
    companion_id: str,
    block_id: str,
    used: dict[str, str],
    locator: str,
) -> None:
    _require(
        companion_id not in used,
        f"companion already used by {used.get(companion_id)}: {companion_id}",
        f"{locator}.companion",
    )
    used[companion_id] = block_id
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


def effective_columns(sections: Any) -> list[int]:
    """The column count in force for each section (a child inherits its chapter)."""
    columns = 1
    resolved: list[int] = []
    for section in sections:
        if section.get("level", 1) == 1:
            columns = (section.get("layout") or {}).get("columns", 1)
        resolved.append(columns)
    return resolved


def _check_compositions(data: dict[str, Any]) -> None:
    """Optional illustration composition: adjacency, prose type, one use, caps.

    A side composition takes either the legacy single `companion` or an ordered
    `companions` group of up to three prose blocks. Both require the blocks to be
    the immediately following blocks, in order, and every block is consumed once.
    """
    used: dict[str, str] = {}
    columns_by_section = effective_columns(data["sections"])
    for section_index, section in enumerate(data["sections"]):
        blocks = section["blocks"]
        for block_index, block in enumerate(blocks):
            composition = block.get("composition")
            if block["type"] != "illustration" or not composition:
                continue
            preset = composition["preset"]
            if preset in {"full", "centred"}:
                continue
            locator = f"sections[{section_index}].blocks[{block_index}].composition"
            _require(
                columns_by_section[section_index] != 2,
                "a side composition is not available inside a two-column chapter "
                "(including its descendant sections); a column visual takes the "
                "column measure",
                locator,
            )
            ids = composition["companions"] if "companions" in composition else [composition["companion"]]
            _require(
                len(ids) <= COMPANION_MAX,
                f"a side composition takes at most {COMPANION_MAX} companions",
                f"{locator}.companions",
            )
            companions: list[dict[str, Any]] = []
            for offset, companion_id in enumerate(ids):
                position = block_index + 1 + offset
                if position >= len(blocks):
                    raise BookifyError(
                        "SCHEMA_INVALID",
                        f"companion is not the immediately following block: {companion_id}",
                        f"{locator}.companion",
                    )
                companion = blocks[position]
                _require(
                    companion["id"] == companion_id,
                    f"companion is not the immediately following block: {companion_id}",
                    f"{locator}.companion",
                )
                _check_companion(companion, companion_id, block["id"], used, locator)
                companions.append(companion)
            printable = _collapsed(
                " ".join(" ".join(_companion_strings(companion)) for companion in companions)
            )
            _require(
                len(printable) <= COMPANION_GROUP_CAP,
                f"companion group exceeds {COMPANION_GROUP_CAP} characters: {len(printable)}",
                f"{locator}.companions",
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


def engine_root() -> Path:
    """The read-only engine tree: fonts, templates, vendored packages and pins."""
    return workspace_mod.engine_root()


def load(
    path: Path,
    root: Path | None = None,
    *,
    workspace: Path | None = None,
    engine: Path | None = None,
) -> Manuscript:
    if root is not None and workspace is not None:
        raise BookifyError("INPUT_INVALID", "use either root or workspace, not both", str(path))
    selected: Path | None = None
    if workspace is not None:
        selected = workspace_mod.resolve(workspace, engine=engine)
        if selected is None:
            raise BookifyError("INPUT_INVALID", f"workspace not found: {workspace}", str(workspace))
        path = workspace_mod.inside(selected, path, code="INPUT_INVALID", label="manuscript")
    if not path.is_file():
        raise BookifyError("INPUT_INVALID", f"manuscript not found: {path}", str(path))
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as error:
        raise BookifyError("SCHEMA_INVALID", f"manuscript is not valid YAML: {error}", str(path)) from error
    if not isinstance(data, dict):
        raise BookifyError("SCHEMA_INVALID", "manuscript root must be a mapping", str(path))

    schema.validate(data)
    if selected is not None:
        project_root = selected
        engine_root_path = (engine or engine_root()).resolve()
    else:
        project_root = root.resolve() if root else _project_root(path)
        engine_root_path = (engine or project_root).resolve()
    section_ids, block_ids = _check_ids(data)
    _check_section_hierarchy(data)
    _check_section_roles(data)
    _check_no_plate(data)
    _check_section_layout(data)
    _check_cover_selection(data)
    _check_xrefs(data, section_ids | block_ids)
    _check_compositions(data)

    for section_index, section in enumerate(data["sections"]):
        for block_index, block in enumerate(section["blocks"]):
            locator = f"sections[{section_index}].blocks[{block_index}]"
            if block.get("confidence") == "unreadable":
                _check_unreadable(block, locator)
            _check_machine_read(block, locator)
            kind = block["type"]
            if kind == "chart":
                _check_chart(block, locator)
            elif kind == "diagram":
                _check_diagram(block, locator, engine_root_path)
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
        engine=engine_root_path,
        workspace=selected,
    )
