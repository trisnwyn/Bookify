"""Finite catalogue inventory, proved from reviewed data and the built PDF.

The reviewed fixture is data, not a value derived from the manuscript it checks.
This module compares it with the manuscript's stored inventory and then with the
text actually extractable from the rendered catalogue. It runs only for the
catalogue manuscript; the runner decides whether to call it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from bookify.errors import BookifyError
from bookify.figures import checks as figure_checks
from bookify.manuscript import model
from bookify.publish import rights
from bookify.verify.checks import Check, failed, passed
from bookify.verify.checks import captions as captions_check
from bookify.verify.checks import pages as pages_check

CATALOGUE_ID = "visual-catalogue"
DEFAULT_EXPECTED = Path("fixtures/expected/catalogue.json")
COUNT_KEYS = (
    "chartFamilies",
    "charts",
    "diagramPresets",
    "diagrams",
    "illustrations",
    "figures",
    "photographs",
    "tables",
    "coverageRows",
)


def _normalise(text: str) -> str:
    return " ".join(text.split())


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


def _require(condition: bool, message: str, path: Path) -> None:
    if not condition:
        raise BookifyError("VERIFY_FAILED", f"catalogue fixture: {message}", str(path))


def _mapping(value: Any, label: str, path: Path) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{label} must be an object", path)
    return value


def _array(value: Any, label: str, path: Path) -> list[Any]:
    _require(isinstance(value, list), f"{label} must be an array", path)
    return value


def _text(value: Any, label: str, path: Path) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"{label} must be a non-empty string", path)
    return value


def _variants(family: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    variants = _array(family.get("variants"), "chart family variants", path)
    _require(bool(variants), "a chart family needs at least one variant", path)
    for variant in variants:
        _mapping(variant, "chart variant", path)
        _text(variant.get("variant"), "chart variant name", path)
        _text(variant.get("blockId"), "chart variant blockId", path)
        _text(variant.get("label"), "chart variant label", path)
    return variants


def _validate_expected(data: dict[str, Any], path: Path) -> dict[str, Any]:
    _require(data.get("schemaVersion") == "1.0", "schemaVersion must be 1.0", path)

    manuscript = _mapping(data.get("manuscript"), "manuscript", path)
    _require(manuscript.get("id") == CATALOGUE_ID, f"manuscript id must be {CATALOGUE_ID}", path)
    revision = manuscript.get("revision")
    _require(
        isinstance(revision, int) and not isinstance(revision, bool) and revision >= 1,
        "manuscript revision must be a positive integer",
        path,
    )
    _require(
        manuscript.get("languages") == ["en", "vi", "ja"],
        "manuscript languages must be en, vi, ja",
        path,
    )
    _require(manuscript.get("sections") == 12, "manuscript sections must be 12", path)

    counts = _mapping(data.get("counts"), "counts", path)
    for key in COUNT_KEYS:
        _require(isinstance(counts.get(key), int), f"count {key} must be an integer", path)

    chart_families = _array(data.get("chartFamilies"), "chartFamilies", path)
    _require(len(chart_families) == counts["chartFamilies"] == 15, "must list 15 chart families", path)
    chart_kinds: list[str] = []
    chart_variants: list[dict[str, Any]] = []
    chart_labels: list[str] = []
    for family in chart_families:
        _mapping(family, "chart family", path)
        _text(family.get("family"), "chart family id", path)
        _text(family.get("familyLabel"), "chart family label", path)
        kind = _text(family.get("kind"), "chart family kind", path)
        chart_kinds.append(kind)
        variants = _variants(family, path)
        if kind == "pie":
            _require(
                {variant["variant"] for variant in variants} == {"pie", "donut"},
                "the pie family must have one pie and one donut variant",
                path,
            )
            _require(len(variants) == 2, "the pie family must have exactly two variants", path)
        else:
            _require(
                len(variants) == 1 and variants[0]["variant"] == "default",
                f"chart family {kind} must have one default variant",
                path,
            )
        chart_variants.extend(variants)
        chart_labels.extend(variant["label"] for variant in variants)
    _require(len(chart_variants) == counts["charts"] == 16, "must list 16 chart figures", path)
    _require(len(set(chart_kinds)) == len(chart_kinds), "chart family kinds must be unique", path)
    _require(set(chart_kinds) == set(figure_checks.CHART_KINDS), "chart kinds must match the 15-kind registry", path)
    _require(
        chart_labels == [f"Figure {number}" for number in range(1, 17)],
        "chart figure labels must be Figures 1-16 in order",
        path,
    )

    diagram_presets = _array(data.get("diagramPresets"), "diagramPresets", path)
    _require(len(diagram_presets) == counts["diagramPresets"] == 10, "must list 10 diagram presets", path)
    preset_names: list[str] = []
    diagram_labels: list[str] = []
    for preset in diagram_presets:
        _mapping(preset, "diagram preset", path)
        name = _text(preset.get("preset"), "diagram preset id", path)
        _text(preset.get("familyLabel"), "diagram family label", path)
        _text(preset.get("blockId"), "diagram blockId", path)
        diagram_labels.append(_text(preset.get("label"), "diagram label", path))
        preset_names.append(name)
    _require(len(set(preset_names)) == len(preset_names), "diagram presets must be unique", path)
    _require(set(preset_names) == set(figure_checks.DIAGRAM_PRESETS), "diagram presets must match the 10-preset registry", path)
    _require(
        diagram_labels == [f"Figure {number}" for number in range(17, 27)],
        "diagram labels must be Figures 17-26 in order",
        path,
    )

    illustrations = _array(data.get("illustrationFamilies"), "illustrationFamilies", path)
    _require(len(illustrations) == counts["illustrations"] == 4, "must list four illustration families", path)
    illustration_labels: list[str] = []
    for entry in illustrations:
        _mapping(entry, "illustration family", path)
        _text(entry.get("family"), "illustration family id", path)
        _text(entry.get("familyLabel"), "illustration family label", path)
        _text(entry.get("illustrationId"), "illustration id", path)
        _require(entry.get("recordKind") in model.RECORD_KINDS, "illustration recordKind is unsupported", path)
        _require(entry.get("origin") in {"local", "external"}, "illustration origin must be local or external", path)
        _text(entry.get("licence"), "illustration licence", path)
        _text(entry.get("blockId"), "illustration blockId", path)
        illustration_labels.append(_text(entry.get("label"), "illustration label", path))
        composition = entry.get("composition")
        _require(
            composition in {"full", "side-left", "side-right"},
            "illustration composition must be full, side-left or side-right",
            path,
        )
        companion = entry.get("companion")
        if composition == "full":
            _require(companion is None, "full illustration must not declare a companion", path)
        else:
            _text(companion, "illustration companion", path)
        requires = _array(entry.get("captionRequires"), "illustration captionRequires", path)
        _require(all(isinstance(item, str) and item for item in requires), "captionRequires entries must be strings", path)
    _require(
        [entry["illustrationId"] for entry in illustrations] == ["photo-1", "hist-1", "art-1", "rec-1"],
        "illustration ids must be photo-1, hist-1, art-1 and rec-1 in order",
        path,
    )
    _require(
        {entry["composition"] for entry in illustrations} >= {"full", "side-left", "side-right"},
        "illustrations must demonstrate full, side-left and side-right compositions",
        path,
    )
    _require(illustration_labels == [f"Photograph {number}" for number in range(1, 5)], "illustration labels must be Photographs 1-4 in order", path)

    all_block_ids = (
        [variant["blockId"] for variant in chart_variants]
        + [entry["blockId"] for entry in diagram_presets]
        + [entry["blockId"] for entry in illustrations]
    )
    _require(len(set(all_block_ids)) == len(all_block_ids), "blockIds must be unique", path)

    coverage_table = _mapping(data.get("coverageTable"), "coverageTable", path)
    _text(coverage_table.get("blockId"), "coverage table blockId", path)
    header = _array(coverage_table.get("header"), "coverage table header", path)
    _require(header == ["Family", "Kind or preset", "Figure"], "coverage table header must be Family/Kind or preset/Figure", path)
    _require(coverage_table.get("rows") == counts["coverageRows"] == 29, "coverage table must have 29 rows", path)

    coverage_rows = _array(data.get("coverageRows"), "coverageRows", path)
    _require(len(coverage_rows) == 29, "must list 29 coverage rows", path)
    seen_labels: set[str] = set()
    coverage_labels: list[str] = []
    for row in coverage_rows:
        _mapping(row, "coverage row", path)
        label = _text(row.get("familyLabel"), "coverage familyLabel", path)
        _text(row.get("kindCell"), "coverage kindCell", path)
        _text(row.get("figureCell"), "coverage figureCell", path)
        _require(label not in seen_labels, f"duplicate coverage family label: {label}", path)
        seen_labels.add(label)
        coverage_labels.append(label)

    family_labels = (
        [family["familyLabel"] for family in chart_families]
        + [entry["familyLabel"] for entry in diagram_presets]
        + [entry["familyLabel"] for entry in illustrations]
    )
    _require(family_labels == coverage_labels, "family labels must match the coverage rows in order", path)

    xrefs = _array(data.get("xrefs"), "xrefs", path)
    _require(bool(xrefs), "must record at least one cross-reference", path)
    for xref in xrefs:
        _mapping(xref, "xref", path)
        _text(xref.get("blockId"), "xref blockId", path)
        _text(xref.get("label"), "xref label", path)
    _require(any(item["label"].startswith("Figure ") for item in xrefs), "xrefs must include a figure", path)
    _require(any(item["label"].startswith("Photograph ") for item in xrefs), "xrefs must include a photograph", path)

    return data


def load_expected(path: Path) -> dict[str, Any]:
    """Read and validate the reviewed inventory fixture."""
    if not path.is_file():
        raise BookifyError("VERIFY_FAILED", f"catalogue fixture not found: {path}", str(path))
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise BookifyError("VERIFY_FAILED", f"catalogue fixture is not valid JSON: {error}", str(path)) from error
    if not isinstance(data, dict):
        raise BookifyError("VERIFY_FAILED", "catalogue fixture root must be an object", str(path))
    return _validate_expected(data, path)


def _block_specs(manuscript: model.Manuscript) -> dict[str, captions_check.CaptionSpec]:
    try:
        return {spec.block_id: spec for spec in captions_check.expected_captions(manuscript)}
    except BookifyError as error:
        raise BookifyError("VERIFY_FAILED", f"cannot read printed captions: {error.message}", str(manuscript.path)) from error


def _blocks(manuscript: model.Manuscript) -> list[dict[str, Any]]:
    return [block for section in manuscript.sections for block in section["blocks"]]


def _chart_variant(block: dict[str, Any]) -> str:
    chart = block["chart"]
    if chart["kind"] != "pie":
        return "default"
    return "pie" if chart.get("hole", 0) == 0 else "donut"


def _set_problems(label: str, expected_ids: set[str], actual_ids: set[str]) -> list[str]:
    missing = sorted(expected_ids - actual_ids)
    extra = sorted(actual_ids - expected_ids)
    problems: list[str] = []
    if missing:
        problems.append(f"missing {label}(s): {', '.join(missing)}")
    if extra:
        problems.append(f"extra {label}(s): {', '.join(extra)}")
    return problems


def _illustration_problem(entry: dict[str, Any], record: rights.Illustration, caption: str) -> list[str]:
    problems: list[str] = []
    if record.kind != entry["recordKind"]:
        problems.append(f"{entry['illustrationId']}: record kind is {record.kind}, expected {entry['recordKind']}")
    if record.rights_status != "verified":
        problems.append(f"{entry['illustrationId']}: rights status is {record.rights_status}, expected verified")
    if entry["origin"] == "local":
        expected_origin = f"local:{record.path}"
        if record.origin_url != expected_origin:
            problems.append(f"{entry['illustrationId']}: originUrl is {record.origin_url}, expected {expected_origin}")
    elif not record.origin_url.startswith(("https://", "http://")):
        problems.append(f"{entry['illustrationId']}: external image has no http origin URL")
    if record.licence != entry["licence"]:
        problems.append(f"{entry['illustrationId']}: licence is {record.licence!r}, expected {entry['licence']!r}")
    lowered = caption.casefold()
    for required in entry["captionRequires"]:
        if required.casefold() not in lowered:
            problems.append(f"{entry['illustrationId']}: printed caption does not contain {required!r}")
    return problems


def _audit(
    manuscript: model.Manuscript,
    expected: dict[str, Any],
) -> tuple[list[str], dict[str, Any], dict[str, captions_check.CaptionSpec]]:
    if manuscript.id != CATALOGUE_ID:
        return [f"not a catalogue manuscript: {manuscript.id}"], {}, {}

    problems: list[str] = []
    specs = _block_specs(manuscript)
    blocks = _blocks(manuscript)
    metadata = manuscript.data.get("metadata", {})

    if len(manuscript.sections) != expected["manuscript"]["sections"]:
        problems.append(f"section count is {len(manuscript.sections)}, expected {expected['manuscript']['sections']}")
    if manuscript.revision != expected["manuscript"]["revision"]:
        problems.append(f"revision is {manuscript.revision}, expected {expected['manuscript']['revision']}")
    if metadata.get("languages") != expected["manuscript"]["languages"]:
        problems.append(f"languages are {metadata.get('languages')}, expected {expected['manuscript']['languages']}")

    expected_charts: dict[str, dict[str, Any]] = {}
    for family in expected["chartFamilies"]:
        for variant in family["variants"]:
            expected_charts[variant["blockId"]] = {
                "family": family["family"],
                "kind": family["kind"],
                "variant": variant["variant"],
                "label": variant["label"],
            }
    actual_charts = {
        block["id"]: {
            "kind": block["chart"]["kind"],
            "variant": _chart_variant(block),
            "label": specs[block["id"]].label if block["id"] in specs else "<unprinted>",
        }
        for block in blocks
        if block["type"] == "chart"
    }
    problems.extend(_set_problems("chart block", set(expected_charts), set(actual_charts)))
    for block_id in sorted(set(expected_charts) & set(actual_charts)):
        expected_value = expected_charts[block_id]
        actual_value = actual_charts[block_id]
        if expected_value["kind"] != actual_value["kind"]:
            problems.append(f"{block_id}: chart kind is {actual_value['kind']}, expected {expected_value['kind']}")
        if expected_value["variant"] != actual_value["variant"]:
            problems.append(f"{block_id}: chart variant is {actual_value['variant']}, expected {expected_value['variant']}")
        if expected_value["label"] != actual_value["label"]:
            problems.append(f"{block_id}: label is {actual_value['label']}, expected {expected_value['label']}")

    expected_presets: dict[str, dict[str, Any]] = {
        entry["blockId"]: entry for entry in expected["diagramPresets"]
    }
    actual_presets = {
        block["id"]: {
            "preset": block["diagram"]["preset"],
            "label": specs[block["id"]].label if block["id"] in specs else "<unprinted>",
        }
        for block in blocks
        if block["type"] == "diagram"
    }
    problems.extend(_set_problems("diagram block", set(expected_presets), set(actual_presets)))
    for block_id in sorted(set(expected_presets) & set(actual_presets)):
        expected_value = expected_presets[block_id]
        actual_value = actual_presets[block_id]
        if expected_value["preset"] != actual_value["preset"]:
            problems.append(f"{block_id}: diagram preset is {actual_value['preset']}, expected {expected_value['preset']}")
        if expected_value["label"] != actual_value["label"]:
            problems.append(f"{block_id}: label is {actual_value['label']}, expected {expected_value['label']}")

    expected_illustrations: dict[str, dict[str, Any]] = {
        entry["blockId"]: entry for entry in expected["illustrationFamilies"]
    }
    actual_illustrations = {
        block["id"]: block["illustrationId"]
        for block in blocks
        if block["type"] == "illustration"
    }
    actual_compositions = {
        block["id"]: (
            (block.get("composition") or {}).get("preset", "full"),
            (block.get("composition") or {}).get("companion"),
        )
        for block in blocks
        if block["type"] == "illustration"
    }
    problems.extend(_set_problems("illustration block", set(expected_illustrations), set(actual_illustrations)))
    for block_id in sorted(set(expected_illustrations) & set(actual_illustrations)):
        entry = expected_illustrations[block_id]
        actual_id = actual_illustrations[block_id]
        if actual_id != entry["illustrationId"]:
            problems.append(f"{block_id}: illustration is {actual_id}, expected {entry['illustrationId']}")
            continue
        actual_composition = actual_compositions.get(block_id)
        expected_composition = (entry["composition"], entry["companion"])
        if actual_composition != expected_composition:
            problems.append(
                f"{block_id}: composition is {actual_composition}, expected {expected_composition}"
            )
        try:
            record = rights.load(manuscript.root, actual_id)
        except BookifyError as error:
            problems.append(f"{actual_id}: {error.message}")
            continue
        caption = specs[block_id].text if block_id in specs else ""
        problems.extend(_illustration_problem(entry, record, caption))

    table_block_id = expected["coverageTable"]["blockId"]
    tables = [block for block in blocks if block["type"] == "table"]
    table = next((block for block in tables if block["id"] == table_block_id), None)

    actual_counts = {
        "chartFamilies": len({value["kind"] for value in actual_charts.values()}),
        "charts": len(actual_charts),
        "diagramPresets": len({value["preset"] for value in actual_presets.values()}),
        "diagrams": len(actual_presets),
        "illustrations": len(actual_illustrations),
        "figures": sum(1 for block in blocks if block["type"] in {"chart", "diagram"}),
        "photographs": sum(1 for block in blocks if block["type"] == "illustration"),
        "tables": len(tables),
        "coverageRows": len(table["rows"]) if table is not None else 0,
    }
    for key, value in expected["counts"].items():
        if actual_counts.get(key) != value:
            problems.append(f"{key} count is {actual_counts.get(key)}, expected {value}")

    figures = [
        specs[block["id"]].label
        for block in blocks
        if block["type"] in {"chart", "diagram"} and block["id"] in specs
    ]
    photographs = [
        specs[block["id"]].label
        for block in blocks
        if block["type"] == "illustration" and block["id"] in specs
    ]
    if figures != [f"Figure {number}" for number in range(1, 27)]:
        problems.append(f"figure numbering is not Figures 1-26 in document order: {figures}")
    if photographs != [f"Photograph {number}" for number in range(1, 5)]:
        problems.append(f"photograph numbering is not Photographs 1-4 in document order: {photographs}")

    if table is None:
        problems.append(f"coverage table block not found: {table_block_id}")
    else:
        header = [_normalise(cell) for cell in table["header"]]
        if header != expected["coverageTable"]["header"]:
            problems.append(f"coverage table header is {header}, expected {expected['coverageTable']['header']}")
        if len(table["rows"]) != expected["coverageTable"]["rows"]:
            problems.append(
                f"coverage table has {len(table['rows'])} rows, expected {expected['coverageTable']['rows']}"
            )
        for index, row in enumerate(expected["coverageRows"]):
            if index >= len(table["rows"]):
                break
            actual_cells = [_normalise(cell) for cell in table["rows"][index]]
            expected_cells = [
                _normalise(row["familyLabel"]),
                _normalise(row["kindCell"]),
                _normalise(row["figureCell"]),
            ]
            if actual_cells != expected_cells:
                problems.append(f"coverage row {index + 1} is {actual_cells}, expected {expected_cells}")

    manuscript_text = "\n".join(_strings(manuscript.data))
    for xref in expected["xrefs"]:
        token = f"{{ref:{xref['blockId']}}}"
        if token not in manuscript_text:
            problems.append(f"missing cross-reference token {token}")

    evidence: dict[str, Any] = {
        "manuscriptId": manuscript.id,
        "sections": len(manuscript.sections),
        "counts": actual_counts,
        "chartFamilies": [family["familyLabel"] for family in expected["chartFamilies"]],
        "diagramPresets": [entry["preset"] for entry in expected["diagramPresets"]],
        "illustrationFamilies": [
            {
                "family": entry["family"],
                "illustrationId": entry["illustrationId"],
                "label": entry["label"],
            }
            for entry in expected["illustrationFamilies"]
        ],
        "illustrationCompositions": [
            {
                "blockId": entry["blockId"],
                "preset": entry["composition"],
                "companionId": entry["companion"],
            }
            for entry in expected["illustrationFamilies"]
        ],
        "figureLabels": figures,
        "photographLabels": photographs,
        "coverageRows": len(expected["coverageRows"]),
    }
    return problems, evidence, specs


def inventory_problems(manuscript: model.Manuscript, expected: dict[str, Any]) -> list[str]:
    """Content-level comparison only; useful before renderers exist."""
    problems, _, _ = _audit(manuscript, expected)
    return problems


def _pdf_problems(
    pdf: Path,
    expected: dict[str, Any],
    specs: dict[str, captions_check.CaptionSpec],
) -> list[str]:
    texts = pages_check.page_texts(pdf)
    full_text = _normalise("\n".join(texts))
    labels = pages_check.numbered_labels(texts)
    problems: list[str] = []

    expected_figure_labels = [
        variant["label"]
        for family in expected["chartFamilies"]
        for variant in family["variants"]
    ] + [entry["label"] for entry in expected["diagramPresets"]]
    for label in expected_figure_labels:
        if label not in labels:
            problems.append(f"{label}: printed figure label not found")

    for entry in expected["illustrationFamilies"]:
        if entry["label"] not in labels:
            problems.append(f"{entry['label']}: printed photograph label not found")
        spec = specs.get(entry["blockId"])
        if spec is None:
            problems.append(f"{entry['blockId']}: printed caption not available")
            continue
        occurrences = full_text.count(_normalise(spec.text))
        if occurrences != 1:
            problems.append(
                f"{entry['label']}: printed caption occurs {occurrences} time(s), expected exactly once"
            )

    illustration_pages = pages_check.illustration_pages(texts)
    offending = {page: found for page, found in illustration_pages.items() if len(found) > 1}
    if offending:
        problems.append(f"pages hold more than one photograph: {sorted(offending)}")
    photograph_pages = [page for page, found in illustration_pages.items() if found]
    if len(photograph_pages) != len(expected["illustrationFamilies"]):
        problems.append(
            f"photographs occupy {len(photograph_pages)} page(s), expected {len(expected['illustrationFamilies'])} distinct pages"
        )

    for row in expected["coverageRows"]:
        for field in ("familyLabel", "figureCell"):
            value = _normalise(row[field])
            if value not in full_text:
                problems.append(f"coverage {field} not extractable: {row[field]!r}")

    for xref in expected["xrefs"]:
        if _normalise(xref["label"]) not in full_text:
            problems.append(f"resolved cross-reference not found in PDF text: {xref['label']!r}")

    return problems


def check(
    pdf: Path,
    manuscript: model.Manuscript,
    expected_path: Path | None = None,
) -> Check:
    """Prove the finite catalogue inventory from reviewed data and the PDF."""
    path = expected_path or manuscript.root / DEFAULT_EXPECTED
    try:
        expected = load_expected(path)
    except BookifyError as error:
        return failed("catalogue", "VERIFY_FAILED", error.message, fixture=str(path))

    try:
        problems, evidence, specs = _audit(manuscript, expected)
    except BookifyError as error:
        return failed("catalogue", "VERIFY_FAILED", error.message, fixture=str(path))
    if problems:
        return failed("catalogue", "VERIFY_FAILED", problems[0], fixture=str(path), problems=problems)

    try:
        pdf_problems = _pdf_problems(pdf, expected, specs)
    except BookifyError as error:
        return failed("catalogue", "VERIFY_FAILED", error.message, fixture=str(path))
    if pdf_problems:
        return failed(
            "catalogue",
            "VERIFY_FAILED",
            pdf_problems[0],
            fixture=str(path),
            problems=pdf_problems,
        )

    counts = evidence["counts"]
    return passed(
        "catalogue",
        (
            f"exact {counts['chartFamilies']}/{counts['diagramPresets']}/{counts['illustrations']} "
            f"inventory: {counts['charts']} charts, {counts['diagrams']} diagrams, "
            f"{counts['illustrations']} illustrations, {counts['coverageRows']} coverage rows"
        ),
        fixture=str(path),
        **evidence,
    )
