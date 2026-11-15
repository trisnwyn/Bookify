"""Machine-read provenance: OCR text is evidence, never verified fact."""

from __future__ import annotations

import re

from bookify.manuscript import model
from bookify.verify.checks import Check, failed, passed, warned

DIGIT = re.compile(r"\d")
NOTE_PREFIX = "Reconstructed from an image by OCR"


def _blocks(manuscript: model.Manuscript) -> list[tuple[int, dict]]:
    return [
        (index, block)
        for index, block in enumerate(
            (block for section in manuscript.sections for block in section["blocks"]), start=1
        )
    ]


def _regions(manifest: dict | None) -> dict[tuple[int, int], dict]:
    regions: dict[tuple[int, int], dict] = {}
    if not isinstance(manifest, dict):
        return regions
    for page in manifest.get("pages", []):
        record = page.get("ocr")
        if not isinstance(record, dict):
            continue
        for region in record.get("regions", []):
            if isinstance(region, dict) and "index" in region:
                regions[(page["page"], region["index"])] = region
    return regions


def _machine_region(
    block: dict, machine: dict, regions: dict[tuple[int, int], dict]
) -> tuple[int, int] | None:
    for anchor in block.get("sourceAnchors", []):
        if anchor.get("region") == machine.get("region") and isinstance(anchor.get("page"), int):
            return (anchor["page"], machine["region"])
    return None


def check(manuscript: model.Manuscript, manifest: dict | None = None) -> Check:
    failures: list[dict[str, str]] = []
    digit_blocks: list[dict[str, object]] = []
    regions = _regions(manifest)
    for _index, block in _blocks(manuscript):
        machine = block.get("machineRead")
        if block["type"] == "chart" and any(
            isinstance(anchor, dict) and "region" in anchor
            for anchor in block.get("sourceAnchors", [])
        ):
            failures.append(
                {
                    "blockId": block["id"],
                    "reason": "OCR numbers cannot become chart values",
                }
            )
        if machine is None:
            continue
        if block.get("confidence") == "verified":
            failures.append({"blockId": block["id"], "reason": "machineRead with confidence verified"})
        for field in ("region", "method", "confidence"):
            if field not in machine:
                failures.append({"blockId": block["id"], "reason": f"machineRead.{field} missing"})
        if block["type"] == "table":
            if machine.get("method") != "ocr-table-v1":
                failures.append({"blockId": block["id"], "reason": "table method is not ocr-table-v1"})
            if not str(block.get("note", "")).startswith(NOTE_PREFIX):
                failures.append(
                    {"blockId": block["id"], "reason": "machine-read table lacks the reconstruction note"}
                )
        if block["type"] in {"chart", "diagram", "equation", "illustration", "unresolved"}:
            failures.append(
                {"blockId": block["id"], "reason": f"machineRead is not valid on a {block['type']} block"}
            )
        if regions:
            key = _machine_region(block, machine, regions)
            if key is None:
                failures.append(
                    {"blockId": block["id"], "reason": "machineRead.region has no page anchor"}
                )
            elif key not in regions:
                failures.append(
                    {
                        "blockId": block["id"],
                        "reason": f"machineRead region {key[1]} on page {key[0]} is absent from the manifest",
                    }
                )
            else:
                region = regions[key]
                if region.get("band") in {"below_threshold", "failed"} or region.get("eligibleLineCount") == 0:
                    failures.append(
                        {
                            "blockId": block["id"],
                            "reason": f"machineRead cites a {region.get('band')} region with no eligible line",
                        }
                    )
                claimed = machine.get("confidence")
                if machine.get("method") == "ocr-line":
                    measured = [
                        float(line["confidence"])
                        for line in region.get("lines", [])
                        if line.get("eligible") and isinstance(line.get("confidence"), (int, float))
                    ]
                else:
                    mean = (region.get("confidence") or {}).get("mean")
                    measured = [float(mean)] if isinstance(mean, (int, float)) else []
                if not measured or not isinstance(claimed, (int, float)) or not any(
                    abs(float(claimed) - value) <= 0.01 for value in measured
                ):
                    failures.append(
                        {
                            "blockId": block["id"],
                            "reason": (
                                f"machineRead.confidence {claimed} does not match the measured "
                                f"region confidence {sorted(set(round(v, 2) for v in measured))}"
                            ),
                        }
                    )
                normalised = re.sub(
                    r"[^0-9a-z]+", "", " ".join(model._strings(block)).casefold()
                )
                for line in region.get("lines", []):
                    if line.get("eligible") is not False and line.get("band") not in {
                        "below_threshold",
                        "failed",
                    }:
                        continue
                    text = re.sub(r"[^0-9a-z]+", "", str(line.get("text", "")).casefold())
                    if len(text) >= 8 and text in normalised:
                        failures.append(
                            {
                                "blockId": block["id"],
                                "reason": f"publishes an ineligible OCR line: {line.get('text')!r}",
                            }
                        )
        content = " ".join(model._strings(block))
        if DIGIT.search(content):
            if not machine.get("crossCheckedBy"):
                failures.append(
                    {"blockId": block["id"], "reason": "machine-read digits lack crossCheckedBy"}
                )
            page = next(
                (
                    anchor.get("page")
                    for anchor in block.get("sourceAnchors", [])
                    if anchor.get("region") == machine.get("region")
                ),
                None,
            )
            digit_blocks.append(
                {
                    "blockId": block["id"],
                    "page": page,
                    "region": machine.get("region"),
                    "detail": (
                        f"{block['id']} on page {page} carries only machine-read digits; "
                        "the value is inferred and must be cross-checked by a reader"
                    ),
                }
            )

    if failures:
        return failed(
            "machine_read",
            "SCHEMA_INVALID",
            f"machine-read provenance is invalid on {len(failures)} block(s)",
            failures=failures,
        )
    if digit_blocks:
        return warned(
            "machine_read",
            f"{len(digit_blocks)} machine-read block(s) carry digits only",
            warnings=[
                {
                    "id": f"MACHINE_READ_DIGITS:{item['blockId']}",
                    "check": "machine_read",
                    **item,
                }
                for item in digit_blocks
            ],
        )
    return passed("machine_read", "every machineRead block is inferred and well recorded")
