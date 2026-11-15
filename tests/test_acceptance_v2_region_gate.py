"""Acceptance: an applied page does not make a degraded region usable (C1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bookify.authoring import record as author_record
from bookify.errors import BookifyError

from test_ocr_provenance import _derivation, _manifest, _manuscript, _workspace


def _add_degraded_region(manifest: dict[str, Any]) -> None:
    record = manifest["pages"][0]["ocr"]
    record["regions"].append(
        {
            "index": 2,
            "bbox": [56.72, 520.0, 539.22, 700.0],
            "band": "below_threshold",
            "confidence": {"mean": 43.25, "minLine": 31.0, "lowConfidenceShare": 0.76},
            "agreement": 0.6667,
            "eligibleLineCount": 0,
            "lineCount": 1,
            "wordCount": 3,
            "machineRead": True,
            "lines": [
                {
                    "index": 1,
                    # Deliberately unlike the table text: only the region band,
                    # not a quoted line, can reject this block.
                    "text": "Smudged memo of receipts",
                    "confidence": 43.25,
                    "agreement": 0.6667,
                    "band": "below_threshold",
                    "eligible": False,
                }
            ],
        }
    )


def test_an_applied_page_cannot_present_a_degraded_region_as_covered(
    tmp_path: Path,
) -> None:
    def mutate_manifest(manifest: dict[str, Any]) -> None:
        _add_degraded_region(manifest)

    def mutate_manuscript(manuscript: dict[str, Any]) -> None:
        block = manuscript["sections"][0]["blocks"][0]
        block["machineRead"]["region"] = 2
        block["sourceAnchors"][0]["region"] = 2
        block["machineRead"]["confidence"] = 43.25

    def mutate_record(record: dict[str, Any]) -> None:
        record["coverage"][0]["ocrRegions"] = [1, 2]
        record["derivations"] = [_derivation()]
        record["derivations"][0]["anchors"] = [
            {"sourceId": "ocr-source", "page": 1, "region": 2}
        ]

    workspace, book, record = _workspace(
        tmp_path,
        mutate_manifest=mutate_manifest,
        mutate_manuscript=mutate_manuscript,
        mutate_record=mutate_record,
    )

    with pytest.raises(BookifyError) as error:
        author_record.check(record, manuscript_path=book, workspace=workspace)

    assert error.value.code == "INPUT_INVALID"
    assert "below_threshold" in error.value.message
    assert "cannot be presented as covered" in error.value.message


def test_the_same_page_still_accepts_its_adequate_region(tmp_path: Path) -> None:
    def mutate_manifest(manifest: dict[str, Any]) -> None:
        _add_degraded_region(manifest)

    workspace, book, record = _workspace(tmp_path, mutate_manifest=mutate_manifest)

    payload = author_record.check(record, manuscript_path=book, workspace=workspace)
    assert payload["ok"] is True
    assert _manifest()["pages"][0]["ocr"]["regions"][0]["band"] == "adequate"
    assert _manuscript()["sections"][0]["blocks"][0]["machineRead"]["region"] == 1
