"""Durable authoring record: mode, provenance, coverage and decisions.

The record is a sidecar beside the manuscript (``authoring/record.json``). It is
durable evidence, not a cache, and it never changes the closed manuscript schema
(``schemaVersion: "1.0"``). Violations reuse ``INPUT_INVALID`` with a locator
into the record file; workspace escapes reuse ``BUILD_FAILED``.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bookify.authoring import workspace as workspace_mod
from bookify.errors import BookifyError
from bookify.manuscript import model

SCHEMA_VERSION = "1.0"
MODES: tuple[str, str] = ("source-faithful", "teachable")
COVERAGE_STATUSES: tuple[str, str, str] = ("covered", "merged", "excluded")
DERIVATION_KINDS = frozenset(
    {
        "heading",
        "caption",
        "merge",
        "split",
        "reorder",
        "condense",
        "explain",
        "example",
        "assessment",
        "glossary",
        "external",
        "ocr",
    }
)
OCR_STATUSES = ("applied", "uncertain", "below_threshold", "not_required", "skipped", "failed")
OCR_UNUSABLE = frozenset({"below_threshold", "failed"})
TEACHING_KINDS = frozenset({"explain", "example", "assessment", "glossary"})
DECISION_KINDS = frozenset(
    {
        "omit",
        "merge",
        "split",
        "reorder",
        "condense",
        "redraw",
        "explain",
        "example",
        "assessment",
        "glossary",
        "external",
        "unresolved",
        "rights",
        "other",
    }
)
# Manuscript teaching block -> the derivation kind that must retain it in strict mode.
TEACHING_BLOCKS = {"definition": "glossary", "example": "example", "assessment": "assessment", "case": "explain"}

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
HEX = re.compile(r"^[0-9a-f]{64}$")
SOURCE_FIELDS = {"id", "sha256", "pages", "intakeManifest"}
ENRICHMENT_FIELDS = {"requested", "permission", "sources"}
SOURCE_CITATION_FIELDS = {"citation", "locator", "localSha256", "creator", "accessed"}
DERIVATION_FIELDS = {
    "kind",
    "blockIds",
    "anchors",
    "citation",
    "decision",
    "retained",
    "method",
    "crossCheck",
}
COVERAGE_FIELDS = {
    "sourceId",
    "page",
    "status",
    "blockIds",
    "reason",
    "basis",
    "ocrRegions",
    "ocrStatus",
}
UNCERTAINTY_FIELDS = {"sourceId", "page", "blockId", "note"}
DECISION_FIELDS = {"id", "kind", "decision"}
RECORD_FIELDS = {
    "schemaVersion",
    "bookId",
    "mode",
    "source",
    "enrichment",
    "coverage",
    "derivations",
    "uncertainty",
    "decisions",
    "manuscriptSha256",
    "manuscriptRevision",
}
REQUIRED_FIELDS = RECORD_FIELDS - {"uncertainty", "decisions"}


@dataclass(frozen=True)
class Record:
    path: Path
    book_id: str
    mode: str
    source_id: str
    source_sha256: str
    pages: int
    enrichment: dict[str, Any]
    coverage: tuple[dict[str, Any], ...]
    derivations: tuple[dict[str, Any], ...]
    uncertainty: tuple[dict[str, Any], ...]
    decisions: tuple[dict[str, Any], ...]
    manuscript_sha256: str
    manuscript_revision: int
    data: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        counts = {status: 0 for status in COVERAGE_STATUSES}
        for entry in self.coverage:
            counts[entry["status"]] += 1
        kinds: dict[str, int] = {}
        for entry in self.derivations:
            kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
        return {
            "bookId": self.book_id,
            "mode": self.mode,
            "source": {
                "id": self.source_id,
                "sha256": self.source_sha256,
                "pages": self.pages,
                "intakeManifest": self.data["source"]["intakeManifest"],
            },
            "coverage": counts,
            "derivations": {"total": len(self.derivations), "kinds": kinds},
            "uncertainty": len(self.uncertainty),
            "enrichment": {
                "requested": self.enrichment["requested"],
                "permission": self.enrichment["permission"],
                "sources": len(self.enrichment["sources"]),
            },
            "manuscript": {"revision": self.manuscript_revision, "sha256": self.manuscript_sha256},
            "decisions": len(self.decisions),
            "record": str(self.path),
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fail(locator: str, field: str, message: str) -> None:
    raise BookifyError("INPUT_INVALID", message, f"{locator}:{field}")


def _mapping(value: Any, locator: str, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(locator, field, f"{field} must be an object")
    return value


def _closed(data: dict[str, Any], allowed: set[str], locator: str, field: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        _fail(locator, field, f"unknown {field} field: {', '.join(unknown)}")


def _text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _slug_value(value: Any) -> bool:
    return isinstance(value, str) and SLUG.match(value) is not None


def _hex_value(value: Any) -> bool:
    return isinstance(value, str) and HEX.match(value) is not None


def _count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _block_ids(value: Any, locator: str, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or not value:
        if allow_empty and isinstance(value, list):
            return []
        _fail(locator, field, f"{field} must be a non-empty list of block ids")
    for index, item in enumerate(value):
        if not _slug_value(item):
            _fail(locator, f"{field}[{index}]", f"block id must be a slug: {item!r}")
    return list(value)


def _anchors(value: Any, locator: str, field: str, source_id: str, pages: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        _fail(locator, field, f"{field} must be a list of source anchors")
    anchors: list[dict[str, Any]] = []
    for index, anchor in enumerate(value):
        item = _mapping(anchor, locator, f"{field}[{index}]")
        _closed(item, {"sourceId", "page", "region"}, locator, f"{field}[{index}]")
        if item.get("sourceId") != source_id:
            _fail(locator, f"{field}[{index}].sourceId", f"anchor must use the record source id: {source_id}")
        page = item.get("page")
        if not _count(page) or not 1 <= page <= pages:
            _fail(locator, f"{field}[{index}].page", f"anchor page must be within 1..{pages}: {page!r}")
        anchor = {"sourceId": source_id, "page": page}
        if "region" in item:
            region = item["region"]
            if not _count(region) or region < 1:
                _fail(locator, f"{field}[{index}].region", f"anchor region must be an integer >= 1: {region!r}")
            anchor["region"] = region
        anchors.append(anchor)
    return anchors


def _validate_source(data: Any, locator: str) -> dict[str, Any]:
    source = _mapping(data, locator, "source")
    _closed(source, SOURCE_FIELDS, locator, "source")
    for field in sorted(SOURCE_FIELDS):
        if field not in source:
            _fail(locator, f"source.{field}", f"source is missing {field}")
    if not _slug_value(source["id"]):
        _fail(locator, "source.id", "source.id must be a slug")
    if not _hex_value(source["sha256"]):
        _fail(locator, "source.sha256", "source.sha256 must be 64 lowercase hex characters")
    if not _count(source["pages"]) or source["pages"] < 1:
        _fail(locator, "source.pages", "source.pages must be an integer >= 1")
    if not _text(source["intakeManifest"]):
        _fail(locator, "source.intakeManifest", "source.intakeManifest must be a relative path")
    return source


def _validate_enrichment(data: Any, locator: str) -> dict[str, Any]:
    enrichment = _mapping(data, locator, "enrichment")
    _closed(enrichment, ENRICHMENT_FIELDS, locator, "enrichment")
    for field in sorted(ENRICHMENT_FIELDS):
        if field not in enrichment:
            _fail(locator, f"enrichment.{field}", f"enrichment is missing {field}")
    if not isinstance(enrichment["requested"], bool):
        _fail(locator, "enrichment.requested", "enrichment.requested must be a boolean")
    if enrichment["permission"] is not None and not _text(enrichment["permission"]):
        _fail(locator, "enrichment.permission", "enrichment.permission must be null or a non-empty string")
    sources = enrichment["sources"]
    if not isinstance(sources, list):
        _fail(locator, "enrichment.sources", "enrichment.sources must be a list")
    for index, entry in enumerate(sources):
        source = _mapping(entry, locator, f"enrichment.sources[{index}]")
        _closed(source, SOURCE_CITATION_FIELDS, locator, f"enrichment.sources[{index}]")
        if not _text(source.get("citation")):
            _fail(locator, f"enrichment.sources[{index}].citation", "an enrichment source needs a citation")
        locator_values = source.get("locator")
        if locator_values is not None and not _text(locator_values):
            _fail(locator, f"enrichment.sources[{index}].locator", "locator must be a non-empty string")
        digest = source.get("localSha256")
        if digest is not None and not _hex_value(digest):
            _fail(locator, f"enrichment.sources[{index}].localSha256", "localSha256 must be 64 lowercase hex characters")
        if locator_values is None and digest is None:
            _fail(
                locator,
                f"enrichment.sources[{index}].locator",
                "an enrichment source needs a stable locator or a local hash",
            )
        for optional in ("creator", "accessed"):
            if source.get(optional) is not None and not _text(source[optional]):
                _fail(locator, f"enrichment.sources[{index}].{optional}", f"{optional} must be a non-empty string")
    if sources and not enrichment["requested"]:
        _fail(locator, "enrichment.requested", "enrichment sources require an explicit request")
    if enrichment["requested"] and not _text(enrichment["permission"]):
        _fail(locator, "enrichment.permission", "requested enrichment needs a recorded permission")
    return enrichment


def _validate_coverage(data: Any, locator: str, source: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    coverage = data
    if not isinstance(coverage, list) or not coverage:
        _fail(locator, "coverage", "coverage must be a non-empty list")
    entries: list[dict[str, Any]] = []
    for index, raw in enumerate(coverage):
        field = f"coverage[{index}]"
        entry = _mapping(raw, locator, field)
        _closed(entry, COVERAGE_FIELDS, locator, field)
        if entry.get("sourceId") != source["id"]:
            _fail(locator, f"{field}.sourceId", f"coverage must use the record source id: {source['id']}")
        page = entry.get("page")
        if not _count(page) or not 1 <= page <= source["pages"]:
            _fail(locator, f"{field}.page", f"coverage page must be within 1..{source['pages']}: {page!r}")
        status = entry.get("status")
        if status not in COVERAGE_STATUSES:
            _fail(locator, f"{field}.status", f"coverage status must be one of {', '.join(COVERAGE_STATUSES)}")
        allow_empty = status == "excluded"
        block_ids = _block_ids(entry.get("blockIds"), locator, f"{field}.blockIds", allow_empty=allow_empty)
        reason = entry.get("reason")
        if status == "covered":
            if reason is not None and not isinstance(reason, str):
                _fail(locator, f"{field}.reason", "covered reason must be null or a string")
        elif not _text(reason):
            _fail(locator, f"{field}.reason", f"{status} coverage needs a reason")

        basis = entry.get("basis", "text")
        if basis not in {"text", "ocr"}:
            _fail(locator, f"{field}.basis", "coverage basis must be text or ocr")
        raw_regions = entry.get("ocrRegions", [])
        if not isinstance(raw_regions, list):
            _fail(locator, f"{field}.ocrRegions", "ocrRegions must be a list of region indexes")
        regions: list[int] = []
        for region_index, region in enumerate(raw_regions):
            if not _count(region) or region < 1:
                _fail(
                    locator,
                    f"{field}.ocrRegions[{region_index}]",
                    "ocrRegions must contain integers >= 1",
                )
            regions.append(region)
        ocr_status = entry.get("ocrStatus")
        if ocr_status is not None and ocr_status not in OCR_STATUSES:
            _fail(locator, f"{field}.ocrStatus", f"unsupported OCR status: {ocr_status!r}")
        if basis == "text" and regions:
            _fail(locator, f"{field}.basis", "a page with OCR regions must use basis ocr")
        if basis == "ocr" and not regions:
            _fail(locator, f"{field}.basis", "basis ocr needs at least one ocrRegions entry")
        if basis == "ocr" and ocr_status is None:
            _fail(locator, f"{field}.ocrStatus", "basis ocr needs the page OCR status")
        if status == "covered" and ocr_status in OCR_UNUSABLE:
            _fail(locator, f"{field}.status", f"a {ocr_status} page cannot be presented as covered")
        entries.append(
            {
                "sourceId": source["id"],
                "page": page,
                "status": status,
                "blockIds": block_ids,
                "reason": reason if _text(reason) else None,
                "basis": basis,
                "ocrRegions": regions,
                "ocrStatus": ocr_status,
            }
        )
    pages = [entry["page"] for entry in entries]
    if pages != list(range(1, source["pages"] + 1)):
        _fail(
            locator,
            "coverage",
            f"coverage must name every source page once, in ascending order: {pages}",
        )
    return tuple(entries)


def _validate_derivations(data: Any, locator: str, source: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    if not isinstance(data, list):
        _fail(locator, "derivations", "derivations must be a list")
    entries: list[dict[str, Any]] = []
    for index, raw in enumerate(data):
        field = f"derivations[{index}]"
        entry = _mapping(raw, locator, field)
        _closed(entry, DERIVATION_FIELDS, locator, field)
        kind = entry.get("kind")
        if kind not in DERIVATION_KINDS:
            _fail(locator, f"{field}.kind", f"unsupported derivation kind: {kind!r}")
        block_ids = _block_ids(entry.get("blockIds"), locator, f"{field}.blockIds")
        anchors = _anchors(entry.get("anchors", []), locator, f"{field}.anchors", source["id"], source["pages"])
        citation = entry.get("citation")
        if kind == "external":
            if not _text(citation):
                _fail(locator, f"{field}.citation", "an external derivation needs a citation")
        else:
            if citation is not None and citation != "":
                _fail(locator, f"{field}.citation", "only an external derivation carries a citation")
            if not anchors:
                _fail(locator, f"{field}.anchors", "a derivation must anchor to a source page")
        method = entry.get("method")
        cross_check = entry.get("crossCheck")
        if kind == "ocr":
            if method not in {"ocr-line", "ocr-table-v1"}:
                _fail(locator, f"{field}.method", "an OCR derivation needs method ocr-line or ocr-table-v1")
            if not any("region" in anchor for anchor in anchors):
                _fail(locator, f"{field}.anchors", "an OCR derivation needs a region anchor")
        else:
            if method is not None:
                _fail(locator, f"{field}.method", "only an OCR derivation records a method")
            if cross_check is not None:
                _fail(locator, f"{field}.crossCheck", "only an OCR derivation records a cross-check")
        if cross_check is not None and not _text(cross_check):
            _fail(locator, f"{field}.crossCheck", "crossCheck must be a non-empty string")
        if not _text(entry.get("decision")):
            _fail(locator, f"{field}.decision", "every derivation needs a recorded decision")
        retained = entry.get("retained", False)
        if not isinstance(retained, bool):
            _fail(locator, f"{field}.retained", "retained must be a boolean")
        entries.append(
            {
                "kind": kind,
                "blockIds": block_ids,
                "anchors": anchors,
                "citation": citation if _text(citation) else None,
                "decision": entry["decision"],
                "retained": retained,
                "method": method,
                "crossCheck": cross_check,
            }
        )
    return tuple(entries)


def _validate_uncertainty(data: Any, locator: str, source: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        _fail(locator, "uncertainty", "uncertainty must be a list")
    entries: list[dict[str, Any]] = []
    for index, raw in enumerate(data):
        field = f"uncertainty[{index}]"
        entry = _mapping(raw, locator, field)
        _closed(entry, UNCERTAINTY_FIELDS, locator, field)
        if not _text(entry.get("note")):
            _fail(locator, f"{field}.note", "an uncertainty entry needs a note")
        page = entry.get("page")
        if entry.get("sourceId") is not None and entry.get("sourceId") != source["id"]:
            _fail(locator, f"{field}.sourceId", f"uncertainty must use the record source id: {source['id']}")
        if page is not None:
            if not _count(page) or not 1 <= page <= source["pages"]:
                _fail(locator, f"{field}.page", f"uncertainty page must be within 1..{source['pages']}: {page!r}")
        block_id = entry.get("blockId")
        if block_id is not None and not _slug_value(block_id):
            _fail(locator, f"{field}.blockId", "uncertainty blockId must be a slug")
        if page is None and block_id is None:
            _fail(locator, f"{field}.note", "an uncertainty entry needs a page or a block id")
        entries.append(
            {
                "sourceId": source["id"],
                "page": page,
                "blockId": block_id,
                "note": entry["note"],
            }
        )
    return tuple(entries)


def _validate_decisions(data: Any, locator: str) -> tuple[dict[str, Any], ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        _fail(locator, "decisions", "decisions must be a list")
    entries: list[dict[str, Any]] = []
    for index, raw in enumerate(data):
        field = f"decisions[{index}]"
        entry = _mapping(raw, locator, field)
        _closed(entry, DECISION_FIELDS, locator, field)
        if not _text(entry.get("decision")):
            _fail(locator, f"{field}.decision", "a decision needs a recorded reason")
        kind = entry.get("kind")
        if kind is not None and kind not in DECISION_KINDS:
            _fail(locator, f"{field}.kind", f"unsupported decision kind: {kind!r}")
        identifier = entry.get("id")
        if identifier is not None and not _slug_value(identifier):
            _fail(locator, f"{field}.id", "decision id must be a slug")
        entries.append({"id": identifier, "kind": kind, "decision": entry["decision"]})
    return tuple(entries)


def _mode_guards(
    mode: str,
    enrichment: dict[str, Any],
    derivations: tuple[dict[str, Any], ...],
    locator: str,
) -> None:
    if mode == "source-faithful":
        if enrichment["requested"] or enrichment["permission"] is not None or enrichment["sources"]:
            _fail(
                locator,
                "enrichment",
                "source-faithful forbids external enrichment; permission belongs to teachable mode",
            )
        for index, entry in enumerate(derivations):
            field = f"derivations[{index}]"
            if entry["kind"] == "external":
                _fail(locator, f"{field}.kind", "source-faithful rejects external derivations")
            if entry["kind"] == "reorder":
                _fail(locator, f"{field}.kind", "source-faithful keeps the source order; reorder is teachable only")
            if entry["kind"] in TEACHING_KINDS and not entry["retained"]:
                _fail(
                    locator,
                    f"{field}.kind",
                    f"{entry['kind']} must be retained source content in source-faithful mode",
                )
        return

    citations = {source["citation"]: source for source in enrichment["sources"]}
    used: set[str] = set()
    for index, entry in enumerate(derivations):
        field = f"derivations[{index}]"
        if entry["kind"] == "external":
            if not enrichment["requested"]:
                _fail(locator, f"{field}.citation", "external enrichment was not requested for this book")
            if not _text(enrichment["permission"]):
                _fail(locator, f"{field}.citation", "external enrichment needs a recorded permission")
            citation = entry["citation"]
            if citation not in citations:
                _fail(locator, f"{field}.citation", f"citation is not a declared enrichment source: {citation}")
            used.add(citation)
        if entry["kind"] in TEACHING_KINDS and not entry["anchors"]:
            _fail(
                locator,
                f"{field}.anchors",
                "a teaching block must derive from recorded source pages, not from invention",
            )
    for index, source in enumerate(enrichment["sources"]):
        if source["citation"] not in used:
            _fail(
                locator,
                f"enrichment.sources[{index}].citation",
                f"enrichment source is never cited by an external derivation: {source['citation']}",
            )


def _manuscript_blocks(manuscript: model.Manuscript) -> list[dict[str, Any]]:
    return [block for section in manuscript.sections for block in section["blocks"]]


def _manuscript_guards(
    mode: str,
    manuscript: model.Manuscript,
    book_id: str,
    manuscript_sha256: str,
    manuscript_revision: int,
    coverage: tuple[dict[str, Any], ...],
    derivations: tuple[dict[str, Any], ...],
    uncertainty: tuple[dict[str, Any], ...],
    locator: str,
    manifest_data: dict[str, Any] | None = None,
) -> None:
    if book_id != manuscript.id:
        _fail(locator, "bookId", f"bookId must match the manuscript id: {manuscript.id}")
    if manuscript_revision != manuscript.revision:
        _fail(locator, "manuscriptRevision", f"manuscriptRevision must match the manuscript revision: {manuscript.revision}")
    digest = sha256_file(manuscript.path)
    if manuscript_sha256 != digest:
        _fail(locator, "manuscriptSha256", "manuscriptSha256 does not match the stored manuscript")

    blocks = _manuscript_blocks(manuscript)
    known = {block["id"] for block in blocks}
    for index, entry in enumerate(coverage):
        for block_id in entry["blockIds"]:
            if block_id not in known:
                _fail(locator, f"coverage[{index}].blockIds", f"unknown manuscript block: {block_id}")
    recorded: set[str] = set()
    for index, entry in enumerate(derivations):
        for block_id in entry["blockIds"]:
            if block_id not in known:
                _fail(locator, f"derivations[{index}].blockIds", f"unknown manuscript block: {block_id}")
            recorded.add(block_id)
    uncertain_blocks: set[str] = set()
    for index, entry in enumerate(uncertainty):
        block_id = entry["blockId"]
        if block_id is None:
            continue
        if block_id not in known:
            _fail(locator, f"uncertainty[{index}].blockId", f"unknown manuscript block: {block_id}")
        uncertain_blocks.add(block_id)

    by_page = {entry["page"]: entry for entry in coverage}
    for block in blocks:
        for anchor in block.get("sourceAnchors", []):
            page = anchor["page"]
            entry = by_page.get(page)
            if entry is None:
                _fail(locator, "coverage", f"block {block['id']} anchors page {page}, which is not covered")
            if entry["status"] == "excluded":
                _fail(locator, "coverage", f"block {block['id']} is anchored to excluded page {page}")

    for block in blocks:
        block_id = block["id"]
        unreadable = block.get("confidence") == "unreadable" or block["type"] == "unresolved"
        if unreadable and block_id not in uncertain_blocks:
            _fail(
                locator,
                "uncertainty",
                f"block {block_id} is unreadable/unresolved but has no recorded uncertainty",
            )
        if not unreadable and block_id in uncertain_blocks:
            _fail(
                locator,
                "uncertainty",
                f"block {block_id} is readable; it must not be recorded as unreadable evidence",
            )
        anchored = bool(block.get("sourceAnchors"))
        if anchored or block_id in recorded or (unreadable and block_id in uncertain_blocks):
            continue
        _fail(
            locator,
            "derivations",
            f"block {block_id} has no source anchor; record its provenance in a derivation",
        )

    _ocr_guards(blocks, coverage, derivations, locator, manifest_data)

    if mode == "source-faithful":
        # A block may carry its provenance in a derivation instead of a
        # manuscript source anchor. Include those anchors in the order
        # sequence so an unanchored block cannot sit out of order unnoticed.
        derivation_pages: dict[str, list[int]] = {}
        for entry in derivations:
            for block_id in entry["blockIds"]:
                derivation_pages.setdefault(block_id, []).extend(
                    anchor["page"] for anchor in entry.get("anchors", [])
                )
        pages = []
        for block in blocks:
            anchor_pages = [anchor["page"] for anchor in block.get("sourceAnchors", [])]
            pages.extend(anchor_pages or derivation_pages.get(block["id"], []))
        if pages != sorted(pages):
            _fail(
                locator,
                "coverage",
                "source-faithful keeps the source order: page anchors must not decrease, record reorder in teachable",
            )
        retained = {
            (entry["kind"], block_id)
            for entry in derivations
            if entry["retained"]
            for block_id in entry["blockIds"]
        }
        for block in blocks:
            kind = TEACHING_BLOCKS.get(block["type"])
            if kind is None:
                continue
            if (kind, block["id"]) not in retained:
                _fail(
                    locator,
                    "derivations",
                    f"teaching block {block['id']} is absent from the recorded source content; "
                    f"retain it with a retained {kind} derivation or remove it",
                )



def _normalise_ocr_text(text: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", text.casefold())


def _check_machine_confidence(
    block: dict[str, Any],
    machine: dict[str, Any],
    region: dict[str, Any],
    locator: str,
) -> None:
    """The claimed confidence must be the manifest's measured value, not a guess."""
    claimed = machine.get("confidence")
    if not isinstance(claimed, (int, float)) or isinstance(claimed, bool):
        _fail(locator, "machineRead.confidence", f"block {block['id']} needs a numeric confidence")
    if machine.get("method") == "ocr-line":
        measured = [
            float(line["confidence"])
            for line in region.get("lines", [])
            if line.get("eligible")
            and isinstance(line.get("confidence"), (int, float))
        ]
    else:
        mean = (region.get("confidence") or {}).get("mean")
        measured = [float(mean)] if isinstance(mean, (int, float)) else []
    if not measured:
        _fail(
            locator,
            "machineRead.region",
            f"block {block['id']} cites a region with no measured confidence",
        )
    if not any(abs(float(claimed) - value) <= 0.01 for value in measured):
        _fail(
            locator,
            "machineRead.confidence",
            f"block {block['id']} claims confidence {claimed}, but the manifest "
            f"measured {sorted(set(round(value, 2) for value in measured))}",
        )


def _check_ineligible_lines(
    block: dict[str, Any], region: dict[str, Any], locator: str
) -> None:
    """A block may not publish the text of a below-threshold line."""
    content = _normalise_ocr_text(" ".join(model._strings(block)))
    if not content:
        return
    for line in region.get("lines", []):
        if line.get("eligible") is not False and line.get("band") not in OCR_UNUSABLE:
            continue
        text = _normalise_ocr_text(str(line.get("text", "")))
        if len(text) >= 8 and text in content:
            _fail(
                locator,
                "machineRead.line",
                f"block {block['id']} publishes an ineligible OCR line: {line.get('text')!r} "
                f"(band {line.get('band')}, confidence {line.get('confidence')})",
            )


def _ocr_guards(
    blocks: list[dict[str, Any]],
    coverage: tuple[dict[str, Any], ...],
    derivations: tuple[dict[str, Any], ...],
    locator: str,
    manifest_data: dict[str, Any] | None,
) -> None:
    """OCR provenance must resolve to measured regions and corroborated digits."""
    # Eligibility is per region and per line, never only the page status
    # (SPEC-bookify-v2 §3.5). The manifest already measures both bands.
    region_status: dict[tuple[int, int], dict[str, Any]] = {}
    page_status: dict[int, str] = {}
    if manifest_data is not None:
        for page in manifest_data.get("pages", []):
            record = page.get("ocr")
            if not isinstance(record, dict):
                continue
            page_status[page["page"]] = record.get("status")
            for region in record.get("regions", []):
                region_status[(page["page"], region["index"])] = region

    by_page = {entry["page"]: entry for entry in coverage}
    if manifest_data is not None:
        for page, status in page_status.items():
            if status not in {"applied", "uncertain", "below_threshold"}:
                continue
            entry = by_page.get(page)
            if entry is None or entry.get("basis") != "ocr":
                _fail(
                    locator,
                    "coverage",
                    f"page {page} was OCR'd ({status}) but its coverage entry is not basis ocr",
                )
            if entry.get("ocrStatus") != status:
                _fail(
                    locator,
                    f"coverage[{page - 1}].ocrStatus",
                    f"coverage ocrStatus {entry.get('ocrStatus')!r} != manifest {status!r}",
                )
            for region in entry.get("ocrRegions", []):
                if (page, region) not in region_status:
                    _fail(
                        locator,
                        f"coverage[{page - 1}].ocrRegions",
                        f"page {page} has no OCR region {region} in the manifest",
                    )
                measured = region_status[(page, region)]
                if entry.get("status") in {"covered", "merged"} and (
                    measured.get("band") in OCR_UNUSABLE
                    or measured.get("eligibleLineCount") == 0
                ):
                    _fail(
                        locator,
                        f"coverage[{page - 1}].ocrRegions",
                        f"page {page} region {region} is "
                        f"{measured.get('band')} and cannot be presented as covered",
                    )

    ocr_derivations: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(derivations):
        if entry["kind"] != "ocr":
            continue
        for block_id in entry["blockIds"]:
            ocr_derivations[block_id] = entry
        if manifest_data is not None:
            for anchor in entry["anchors"]:
                if "region" not in anchor:
                    continue
                key = (anchor["page"], anchor["region"])
                if key not in region_status:
                    _fail(
                        locator,
                        f"derivations[{index}].anchors",
                        f"OCR derivation names a region absent from the manifest: page {anchor['page']} region {anchor['region']}",
                    )
                measured = region_status[key]
                if measured.get("band") in OCR_UNUSABLE or measured.get("eligibleLineCount") == 0:
                    _fail(
                        locator,
                        f"derivations[{index}].anchors",
                        f"OCR derivation cites a {measured.get('band')} region "
                        f"(page {anchor['page']} region {anchor['region']})",
                    )

    for block in blocks:
        machine = block.get("machineRead")
        if machine is None:
            continue
        match = next(
            (
                anchor
                for anchor in block.get("sourceAnchors", [])
                if anchor.get("region") == machine["region"]
            ),
            None,
        )
        if manifest_data is not None:
            if match is None:
                _fail(locator, "machineRead.region", f"block {block['id']} has no matching region anchor")
            key = (match["page"], machine["region"])
            if key not in region_status:
                _fail(
                    locator,
                    "machineRead.region",
                    f"block {block['id']} cites region {machine['region']} on page {match['page']}, "
                    "which the manifest does not contain",
                )
            measured = region_status[key]
            if measured.get("band") in OCR_UNUSABLE or measured.get("eligibleLineCount") == 0:
                _fail(
                    locator,
                    "machineRead.region",
                    f"block {block['id']} cites a {measured.get('band')} OCR region "
                    "with no eligible line",
                )
            _check_machine_confidence(block, machine, measured, locator)
            _check_ineligible_lines(block, measured, locator)
            for page_anchor in block.get("sourceAnchors", []):
                page = page_anchor["page"]
                if page_status.get(page) in OCR_UNUSABLE and page_anchor.get("region") is None:
                    _fail(
                        locator,
                        "sourceAnchors",
                        f"block {block['id']} anchors a below-threshold OCR page {page} without a region",
                    )
        content = " ".join(model._strings(block))
        if model.DIGIT.search(content):
            cross_checked = machine.get("crossCheckedBy")
            if not cross_checked:
                _fail(
                    locator,
                    "machineRead.crossCheckedBy",
                    f"machine-read block {block['id']} renders digits without a recorded cross-check",
                )
            evidence = ocr_derivations.get(block["id"])
            if evidence is None:
                _fail(
                    locator,
                    "derivations",
                    f"block {block['id']} needs an OCR derivation recording its digit cross-check",
                )
            if evidence.get("crossCheck") != cross_checked:
                _fail(
                    locator,
                    "derivations",
                    f"block {block['id']} crossCheckedBy does not match its recorded OCR derivation",
                )


def _manifest_guards(source: dict[str, Any], workspace: Path, locator: str) -> dict[str, Any]:
    path = workspace_mod.inside(workspace, Path(source["intakeManifest"]), code="INPUT_INVALID", label="intake manifest")
    if not path.is_file():
        _fail(locator, "source.intakeManifest", f"intake manifest not found: {source['intakeManifest']}")
    try:
        manifest = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise BookifyError(
            "INPUT_INVALID",
            f"intake manifest is not valid JSON: {error}",
            f"{locator}:source.intakeManifest",
        ) from error
    if not isinstance(manifest, dict):
        _fail(locator, "source.intakeManifest", "intake manifest must be an object")
    expected = {"sourceId": source["id"], "sourceSha256": source["sha256"], "pageCount": source["pages"]}
    for field, value in expected.items():
        if manifest.get(field) != value:
            _fail(
                locator,
                "source.intakeManifest",
                f"intake manifest {field} does not match the record: {manifest.get(field)!r} != {value!r}",
            )
    return manifest


def validate(
    data: Any,
    *,
    locator: str = "authoring/record.json",
    manuscript: model.Manuscript | None = None,
    workspace: Path | None = None,
    source_sha256: str | None = None,
) -> Record:
    record_data = _mapping(data, locator, "record")
    _closed(record_data, RECORD_FIELDS, locator, "record")
    for field in sorted(REQUIRED_FIELDS):
        if field not in record_data:
            _fail(locator, field, f"record is missing {field}")

    if record_data["schemaVersion"] != SCHEMA_VERSION:
        _fail(locator, "schemaVersion", f"record schemaVersion must be {SCHEMA_VERSION}")
    book_id = record_data["bookId"]
    if not _slug_value(book_id):
        _fail(locator, "bookId", "bookId must be a slug")
    mode = record_data["mode"]
    if mode not in MODES:
        _fail(locator, "mode", f"mode must be one of {', '.join(MODES)}; there is no third mode")

    source = _validate_source(record_data["source"], locator)
    enrichment = _validate_enrichment(record_data["enrichment"], locator)
    coverage = _validate_coverage(record_data["coverage"], locator, source)
    derivations = _validate_derivations(record_data["derivations"], locator, source)
    uncertainty = _validate_uncertainty(record_data.get("uncertainty"), locator, source)
    decisions = _validate_decisions(record_data.get("decisions"), locator)

    manuscript_sha256 = record_data["manuscriptSha256"]
    if not _hex_value(manuscript_sha256):
        _fail(locator, "manuscriptSha256", "manuscriptSha256 must be 64 lowercase hex characters")
    manuscript_revision = record_data["manuscriptRevision"]
    if not _count(manuscript_revision) or manuscript_revision < 1:
        _fail(locator, "manuscriptRevision", "manuscriptRevision must be an integer >= 1")

    _mode_guards(mode, enrichment, derivations, locator)

    if source_sha256 is not None and source_sha256 != source["sha256"]:
        _fail(locator, "source.sha256", "source.sha256 does not match the supplied source file")

    manifest_data = _manifest_guards(source, workspace, locator) if workspace is not None else None

    if manuscript is not None:
        _manuscript_guards(
            mode,
            manuscript,
            book_id,
            manuscript_sha256,
            manuscript_revision,
            coverage,
            derivations,
            uncertainty,
            locator,
            manifest_data,
        )

    return Record(
        path=Path(locator),
        book_id=book_id,
        mode=mode,
        source_id=source["id"],
        source_sha256=source["sha256"],
        pages=source["pages"],
        enrichment=enrichment,
        coverage=coverage,
        derivations=derivations,
        uncertainty=uncertainty,
        decisions=decisions,
        manuscript_sha256=manuscript_sha256,
        manuscript_revision=manuscript_revision,
        data=record_data,
    )


def load(
    path: Path,
    *,
    manuscript: model.Manuscript | None = None,
    workspace: Path | None = None,
    source_sha256: str | None = None,
) -> Record:
    if not path.is_file():
        raise BookifyError("INPUT_INVALID", f"authoring record not found: {path}", str(path))
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise BookifyError("INPUT_INVALID", f"authoring record is not valid JSON: {error}", f"{path}:json") from error
    return validate(
        data,
        locator=str(path),
        manuscript=manuscript,
        workspace=workspace,
        source_sha256=source_sha256,
    )


def check(
    record_path: Path,
    *,
    manuscript_path: Path | None = None,
    workspace: Path | None = None,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Validate one durable record and return the CLI summary payload."""
    resolved_workspace = workspace_mod.resolve(workspace)
    if resolved_workspace is not None:
        record_path = workspace_mod.inside(
            resolved_workspace, record_path, code="INPUT_INVALID", label="authoring record"
        )
    if manuscript_path is None and resolved_workspace is not None:
        manuscript_path = resolved_workspace / "book.yaml"
    if manuscript_path is not None and resolved_workspace is not None:
        manuscript_path = workspace_mod.inside(
            resolved_workspace, manuscript_path, code="INPUT_INVALID", label="manuscript"
        )
    manuscript = (
        model.load(manuscript_path, workspace=resolved_workspace)
        if manuscript_path is not None
        else None
    )
    source_sha256 = None
    if source_path is not None:
        if not source_path.is_file():
            raise BookifyError("INPUT_INVALID", f"source not found: {source_path}", str(source_path))
        source_sha256 = sha256_file(source_path)
    loaded = load(record_path, manuscript=manuscript, workspace=resolved_workspace, source_sha256=source_sha256)
    payload = loaded.summary()
    payload["ok"] = True
    payload["workspace"] = str(resolved_workspace) if resolved_workspace is not None else None
    return payload
